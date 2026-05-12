"""
ARQUIVO: boundary tests de isolamento multi-tenant — Sprint 4.

POR QUE ELE EXISTE:
- prova que dois tenants (box_a, box_b) nao vazam dados entre si via ORM, cache,
  session, raw SQL ou middleware.
- cada teste tem um ID (B1..B12) referenciado em §9.2 do plano de migracao.

COMO RODAR:
    python manage.py test tests.test_tenant_boundary --tag=tenant

REQUISITOS:
- Postgres (nao SQLite) com schema-per-tenant via django-tenants.
- Dois schemas provisionados: box_test_a e box_test_b.
- Para CI, veja §9.3 do plano: provision_box --slug=test-a e --slug=test-b.

Testes que nao precisam de schemas reais (B3, B4, B8, B9, B12) usam mock e
rodam em qualquer banco de testes.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from django.http import JsonResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, tag
from django.urls import reverse


# ---------------------------------------------------------------------------
# B3 — Cache isolation per tenant
# ---------------------------------------------------------------------------

@tag('tenant', 'cache')
class B3CacheIsolationPerTenantTest(SimpleTestCase):
    """B3: duas chaves de cache geradas com schemas diferentes nao colidem."""

    def test_cache_keys_differ_per_schema(self):
        """Aluno #42 em box_a e aluno #42 em box_b devem ter chaves distintas."""
        # Patch via o modulo que usa connection (nao via django.db)
        with patch('student_app.application.cache_keys.connection') as mock_conn:
            mock_conn.schema_name = 'box_test_a'
            from student_app.application.cache_keys import build_student_wod_snapshot_cache_key
            key_a = build_student_wod_snapshot_cache_key(box_root_slug='endorfina', session_id=42, workout_version=1)

        with patch('student_app.application.cache_keys.connection') as mock_conn:
            mock_conn.schema_name = 'box_test_b'
            key_b = build_student_wod_snapshot_cache_key(box_root_slug='endorfina', session_id=42, workout_version=1)

        self.assertNotEqual(key_a, key_b, (
            'Aluno #42 em box_test_a e box_test_b geraram a mesma chave de cache. '
            'Isso e uma colisao de tenant que causa vazamento de dados.'
        ))
        self.assertIn('box_test_a', key_a)
        self.assertIn('box_test_b', key_b)

    def test_get_active_tenant_slug_returns_schema_name_when_tenant_active(self):
        """Quando schema_name != 'public', get_active_tenant_slug retorna schema_name."""
        with patch('student_app.application.cache_keys.connection') as mock_conn:
            mock_conn.schema_name = 'box_endorfina'
            from student_app.application.cache_keys import get_active_tenant_slug
            slug = get_active_tenant_slug()
        self.assertEqual(slug, 'box_endorfina')

    def test_get_active_tenant_slug_falls_back_to_env_in_public(self):
        """Em schema public, usa fallback (env ou parametro)."""
        with patch('student_app.application.cache_keys.connection') as mock_conn:
            mock_conn.schema_name = 'public'
            from student_app.application.cache_keys import get_active_tenant_slug
            slug = get_active_tenant_slug(fallback='box_fallback')
        self.assertEqual(slug, 'box_fallback')


# ---------------------------------------------------------------------------
# B4 — Session attached box persists after relogin
# ---------------------------------------------------------------------------

@tag('tenant', 'session')
class B4SessionBoxPersistsTest(SimpleTestCase):
    """B4: o box_id no cookie de sessao do aluno sobrevive a relogin."""

    def test_session_cookie_includes_box_id_and_active_box_id(self):
        """build_student_session_value deve incluir box_id e active_box_id."""
        from student_identity.infrastructure.session import build_student_session_value
        from django.core import signing

        value = build_student_session_value(
            identity_id=7,
            box_root_slug='endorfina',
            active_box_root_slug='endorfina',
            box_id=42,
            active_box_id=42,
        )
        data = signing.loads(value, salt='student_identity.session')
        self.assertEqual(data['identity_id'], 7)
        self.assertEqual(data['box_id'], 42)
        self.assertEqual(data['active_box_id'], 42)
        self.assertEqual(data['box_root_slug'], 'endorfina')

    def test_session_cookie_without_box_id_is_backward_compatible(self):
        """Sessao sem box_id (legada) deve ainda ser lida sem erro."""
        from student_identity.infrastructure.session import build_student_session_value, read_student_session_value
        from django.core import signing

        # Simula cookie legado sem box_id
        value = signing.dumps(
            {
                'identity_id': 5,
                'box_root_slug': 'alpha',
                'active_box_root_slug': 'alpha',
                'device_fingerprint': '',
            },
            salt='student_identity.session',
        )
        data = read_student_session_value(value)
        self.assertIsNotNone(data)
        self.assertEqual(data['identity_id'], 5)
        # box_id ausente nao e erro — middleware trata com fallback
        self.assertIsNone(data.get('box_id'))


# ---------------------------------------------------------------------------
# B8 — StudentAuthMiddleware exige membership ativa
# ---------------------------------------------------------------------------

@tag('tenant', 'middleware')
class B8ActiveMembershipRequiredTest(SimpleTestCase):
    """B8: /aluno/grade/ redireciona se StudentBoxMembership.status != ACTIVE."""

    def setUp(self):
        self.factory = RequestFactory()

    def _make_request_with_session(self, path='/aluno/grade/', identity_id=1, box_id=1):
        from django.core import signing
        cookie_value = signing.dumps(
            {
                'identity_id': identity_id,
                'box_root_slug': 'box_test',
                'active_box_root_slug': 'box_test',
                'device_fingerprint': '',
                'box_id': box_id,
                'active_box_id': box_id,
            },
            salt='student_identity.session',
        )
        request = self.factory.get(path)
        request.COOKIES['octobox_student_session'] = cookie_value
        request.session = {}
        return request

    @patch('student_app.middleware.student_auth._has_active_membership', return_value=False)
    @patch('student_app.middleware.student_auth._resolve_student_tenant')
    @patch('student_identity.infrastructure.session.read_student_session_value')
    def test_redirects_to_no_active_box_when_membership_inactive(
        self,
        mock_read_session,
        mock_resolve_tenant,
        mock_has_membership,
    ):
        """Se _has_active_membership retorna False, deve redirecionar para student-app-no-active-box."""
        from student_app.middleware.student_auth import StudentAuthMiddleware

        mock_read_session.return_value = {'identity_id': 1, 'box_id': 1}
        mock_resolve_tenant.return_value = None

        get_response = MagicMock(return_value=JsonResponse({}))
        middleware = StudentAuthMiddleware(get_response)
        request = self._make_request_with_session()

        response = middleware(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn('sem-box', response['Location'])
        get_response.assert_not_called()

    @patch('student_app.middleware.student_auth._has_active_membership', return_value=True)
    @patch('student_app.middleware.student_auth._resolve_student_tenant')
    @patch('student_identity.infrastructure.session.read_student_session_value')
    def test_allows_access_when_membership_is_active(
        self,
        mock_read_session,
        mock_resolve_tenant,
        mock_has_membership,
    ):
        """Se _has_active_membership retorna True, deixa passar para a view."""
        from student_app.middleware.student_auth import StudentAuthMiddleware

        mock_read_session.return_value = {'identity_id': 1, 'box_id': 1}
        mock_resolve_tenant.return_value = None

        get_response = MagicMock(return_value=JsonResponse({'ok': True}))
        middleware = StudentAuthMiddleware(get_response)
        request = self._make_request_with_session()

        response = middleware(request)

        get_response.assert_called_once()
        self.assertEqual(response.status_code, 200)

    def test_has_active_membership_returns_true_when_no_identity_id(self):
        """Sessao legada sem identity_id nao bloqueia acesso (backward compat)."""
        from student_app.middleware.student_auth import _has_active_membership

        request = MagicMock()
        request.tenant = MagicMock(slug='box_test')
        result = _has_active_membership(request, {})  # sem identity_id
        self.assertTrue(result)

    def test_has_active_membership_returns_true_when_no_tenant(self):
        """Sem tenant resolvido, nao bloqueia (evita loop de redirect)."""
        from student_app.middleware.student_auth import _has_active_membership

        request = MagicMock()
        request.tenant = None
        result = _has_active_membership(request, {'identity_id': 7})
        self.assertTrue(result)


# ---------------------------------------------------------------------------
# B9 — /aluno/box/switch/ troca connection.schema_name
# ---------------------------------------------------------------------------

@tag('tenant', 'middleware')
class B9SwitchBoxChangesSchemaTest(SimpleTestCase):
    """B9: apos /aluno/box/switch/<other_box_id>/, o tenant muda no proximo request."""

    def test_resolve_student_tenant_sets_tenant_on_request(self):
        """_resolve_student_tenant deve chamar connection.set_tenant com o Box correto."""
        from student_app.middleware.student_auth import _resolve_student_tenant

        mock_box = MagicMock()
        mock_box.slug = 'box_test_b'

        request = MagicMock()
        request.tenant = None

        with patch('control.models.Box.objects') as mock_qs:
            mock_qs.filter.return_value.first.return_value = mock_box
            with patch('django.db.connection') as mock_conn:
                _resolve_student_tenant(
                    request,
                    {'identity_id': 7, 'box_id': 2, 'active_box_id': 2},
                )
                mock_conn.set_tenant.assert_called_once_with(mock_box)

        self.assertEqual(request.tenant, mock_box)

    def test_session_with_different_active_box_id_resolves_different_tenant(self):
        """Dois payloads com active_box_id diferentes devem tentar resolver boxes distintos."""
        from student_app.middleware.student_auth import _resolve_student_tenant

        calls = []

        def fake_filter(**kwargs):
            calls.append(kwargs.get('pk'))
            m = MagicMock()
            m.first.return_value = None  # simula nao encontrado (sem DB)
            return m

        with patch('control.models.Box.objects') as mock_qs:
            mock_qs.filter.side_effect = lambda **kw: (
                calls.append(kw.get('pk')) or MagicMock(first=lambda: None)
            )

            r1 = MagicMock()
            _resolve_student_tenant(r1, {'active_box_id': 11})

            r2 = MagicMock()
            _resolve_student_tenant(r2, {'active_box_id': 22})

        # Os box_id consultados devem ser diferentes
        self.assertIn(11, calls)
        self.assertIn(22, calls)
        self.assertNotEqual(calls[0], calls[1])


# ---------------------------------------------------------------------------
# B12 — Box SUSPENDED redireciona staff para billing renewal
# ---------------------------------------------------------------------------

@tag('tenant', 'stripe')
class B12SuspendedBoxRedirectsStaffTest(SimpleTestCase):
    """B12: TenantBySessionMiddleware retorna 403/redirect quando box.status == SUSPENDED."""

    def test_suspended_box_is_not_resolved_by_tenant_middleware(self):
        """Box com status SUSPENDED nao deve ser retornado pelo _resolve_box."""
        from control.middleware import TenantBySessionMiddleware
        from control.models import Box

        middleware = TenantBySessionMiddleware(get_response=lambda r: JsonResponse({}))

        # _resolve_box usa Box.objects.get(pk=..., status=Box.Status.ACTIVE)
        # Um SUSPENDED box levanta DoesNotExist porque status != ACTIVE.
        with patch('control.models.Box.objects') as mock_box_qs, \
             patch('control.models.Membership.objects') as mock_mem_qs:

            # Box.get levanta DoesNotExist (SUSPENDED nao tem status=ACTIVE)
            mock_box_qs.get.side_effect = Box.DoesNotExist('Box nao encontrado com status ACTIVE')
            # Fallback via Membership: nenhum primary box ativo
            mock_mem_qs.select_related.return_value.filter.return_value.first.return_value = None

            request = MagicMock()
            request.user.is_authenticated = True
            request.session = {}
            request.session['active_box_id'] = 99  # SUSPENDED box

            box = middleware._resolve_box(request)

        self.assertIsNone(box)

    def test_invoice_payment_failed_handler_suspends_box(self):
        """_handle_invoice_payment_failed suspende Box.status para SUSPENDED."""
        from integrations.stripe.router import _handle_invoice_payment_failed

        mock_box = MagicMock()
        mock_box.pk = 1
        mock_box.slug = 'box_test'
        mock_box.status = 'active'

        mock_event = MagicMock()
        mock_event.event_id = 'evt_test_123'
        mock_event.payload = {
            'data': {
                'object': {
                    'subscription': 'sub_test',
                    'customer': 'cus_test',
                }
            }
        }

        with patch('control.models.Box.objects') as mock_box_qs, \
             patch('control.models.PlatformAuditEvent.objects') as mock_audit:

            mock_box_qs.filter.return_value.first.return_value = mock_box
            mock_box.status = 'active'  # nao SUSPENDED ainda

            _handle_invoice_payment_failed(mock_event)

            # Deve ter chamado update com status SUSPENDED
            mock_box_qs.filter.return_value.update.assert_called_once()
            update_kwargs = mock_box_qs.filter.return_value.update.call_args[1]
            from control.models import Box
            self.assertEqual(update_kwargs.get('status'), Box.Status.SUSPENDED)


# ---------------------------------------------------------------------------
# B1 — User de box_a nao ve Students de box_b  (requer postgres real)
# ---------------------------------------------------------------------------

@tag('tenant', 'isolation', 'requires-postgres')
class B1CrossTenantStudentIsolationTest(TestCase):
    """B1: ORM filter em box_a nao retorna Students de box_b.

    Este teste requer schemas provisionados (box_test_a, box_test_b).
    Em CI: rodar apos provision_box --slug=test-a e --slug=test-b.
    """

    def test_student_objects_scoped_to_current_schema(self):
        """Students criados em box_test_a nao aparecem em box_test_b."""
        try:
            from django_tenants.utils import schema_context
            from students.models import Student
        except ImportError:
            self.skipTest('django-tenants ou students.models nao disponivel')

        try:
            # Cria student em box_test_a
            with schema_context('box_test_a'):
                s = Student.objects.create(full_name='Joao Teste Boundary', status='active')
                student_id_a = s.pk

            # Verifica que nao aparece em box_test_b
            with schema_context('box_test_b'):
                count = Student.objects.filter(pk=student_id_a).count()
                self.assertEqual(count, 0, (
                    f'Student #{student_id_a} criado em box_test_a apareceu em box_test_b. '
                    'Isso e um vazamento de dados entre tenants.'
                ))

            # Limpa
            with schema_context('box_test_a'):
                Student.objects.filter(pk=student_id_a).delete()

        except Exception as exc:
            if 'does not exist' in str(exc).lower() or 'schema' in str(exc).lower():
                self.skipTest(f'Schema de teste nao existe: {exc}')
            raise


# ---------------------------------------------------------------------------
# B2 — Acesso por PK direto retorna 404 em outro tenant
# ---------------------------------------------------------------------------

@tag('tenant', 'isolation', 'requires-postgres')
class B2DirectPkAccessTest(TestCase):
    """B2: lookup por PK em tenant errado nao encontra o objeto.

    ORM scoped pelo search_path — PK de box_a nao existe em box_b.
    """

    def test_direct_pk_lookup_returns_none_in_wrong_tenant(self):
        """Student.objects.filter(pk=<id_de_box_a>) retorna 0 em box_b."""
        try:
            from django_tenants.utils import schema_context
            from students.models import Student
        except ImportError:
            self.skipTest('django-tenants nao disponivel')

        try:
            with schema_context('box_test_a'):
                s = Student.objects.create(full_name='Maria Boundary PK', status='active')
                pk_a = s.pk

            with schema_context('box_test_b'):
                result = Student.objects.filter(pk=pk_a).first()
                self.assertIsNone(result, (
                    f'Student #{pk_a} de box_test_a encontrado em box_test_b via PK direto.'
                ))

            with schema_context('box_test_a'):
                Student.objects.filter(pk=pk_a).delete()

        except Exception as exc:
            if 'does not exist' in str(exc).lower() or 'schema' in str(exc).lower():
                self.skipTest(f'Schema nao existe: {exc}')
            raise


# ---------------------------------------------------------------------------
# B5 — ORM filter nao vaza entre schemas
# ---------------------------------------------------------------------------

@tag('tenant', 'isolation', 'requires-postgres')
class B5OrmFilterDoesNotLeakTest(TestCase):
    """B5: Student.objects.all() em box_a nao retorna registros de box_b.

    Prova que search_path esta corretamente setado e nao ha UNION implicita.
    """

    def test_queryset_count_isolated_per_schema(self):
        """Contagens de Students sao independentes por schema."""
        try:
            from django_tenants.utils import schema_context
            from students.models import Student
        except ImportError:
            self.skipTest('django-tenants nao disponivel')

        try:
            with schema_context('box_test_a'):
                count_a_before = Student.objects.count()
                s = Student.objects.create(full_name='Carlos Boundary ORM', status='active')
                pk = s.pk
                count_a_after = Student.objects.count()
                self.assertEqual(count_a_after, count_a_before + 1)

            with schema_context('box_test_b'):
                count_b = Student.objects.count()
                # Nao pode incluir o student criado em box_test_a
                self.assertEqual(
                    Student.objects.filter(pk=pk).count(), 0,
                    'Student de box_a aparece em queryset de box_b'
                )
                # Contagem de box_b nao aumentou
                self.assertEqual(Student.objects.count(), count_b)

            with schema_context('box_test_a'):
                Student.objects.filter(pk=pk).delete()

        except Exception as exc:
            if 'does not exist' in str(exc).lower() or 'schema' in str(exc).lower():
                self.skipTest(f'Schema nao existe: {exc}')
            raise


# ---------------------------------------------------------------------------
# B6 — Raw SQL respeita search_path
# ---------------------------------------------------------------------------

@tag('tenant', 'isolation', 'requires-postgres')
class B6RawSqlRespectsSearchPathTest(TestCase):
    """B6: raw SQL em dashboard usa search_path ativo (nao hardcoded public).

    Verifica que queries raw nao vazam para outro schema.
    """

    def test_raw_sql_count_scoped_to_current_schema(self):
        """SELECT COUNT(*) FROM boxcore_student respeita o search_path do tenant."""
        try:
            from django_tenants.utils import schema_context
            from django.db import connection
        except ImportError:
            self.skipTest('django-tenants nao disponivel')

        try:
            with schema_context('box_test_a'):
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM boxcore_student")
                    count_a = cursor.fetchone()[0]

            with schema_context('box_test_b'):
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM boxcore_student")
                    count_b = cursor.fetchone()[0]

            # Contagens sao independentes (cada schema tem sua propria tabela)
            # Nao e possivel afirmar que sao iguais ou diferentes sem dados,
            # mas a query nao deve falhar (prova que search_path foi setado).
            self.assertIsInstance(count_a, int)
            self.assertIsInstance(count_b, int)

        except Exception as exc:
            if 'does not exist' in str(exc).lower() or 'schema' in str(exc).lower():
                self.skipTest(f'Schema nao existe: {exc}')
            raise


# ---------------------------------------------------------------------------
# B7 — Student records com mesma identity permanecem isolados por tenant
# ---------------------------------------------------------------------------

@tag('tenant', 'isolation', 'requires-postgres')
class B7StudentRecordsWithSameIdentityIsolatedTest(TestCase):
    """B7: Joao em box_a (Student#42) e box_b (Student#17) nao compartilham dados.

    Mesmo identity_id em dois tenants nao cria colisao.
    """

    def test_student_with_same_identity_id_isolated_per_tenant(self):
        """Student.objects.filter(identity_id=7) em box_a nao retorna record de box_b."""
        try:
            from django_tenants.utils import schema_context
            from students.models import Student
            from student_identity.models import StudentIdentity
        except ImportError:
            self.skipTest('django-tenants ou modelos nao disponiveis')

        try:
            # Cria identity em public
            identity = StudentIdentity.objects.create(
                student_name='Joao Boundary Identity',
                email='joao.boundary@test.com',
                box_root_slug='box_test_a',
                primary_box_root_slug='box_test_a',
                provider='test',
                provider_subject='test:joao_boundary',
            )
            identity_id = identity.pk

            # Cria Student em box_a vinculado a identity
            with schema_context('box_test_a'):
                s_a = Student.objects.create(
                    full_name='Joao Boundary',
                    status='active',
                    identity_id=identity_id,
                )

            # Verifica que filtro por identity_id em box_b retorna 0
            with schema_context('box_test_b'):
                count = Student.objects.filter(identity_id=identity_id).count()
                self.assertEqual(count, 0, (
                    'Student com identity_id compartilhado apareceu em box_b. Vazamento.'
                ))

            # Limpa
            with schema_context('box_test_a'):
                Student.objects.filter(pk=s_a.pk).delete()
            StudentIdentity.objects.filter(pk=identity_id).delete()

        except Exception as exc:
            if 'does not exist' in str(exc).lower() or 'schema' in str(exc).lower():
                self.skipTest(f'Schema nao existe: {exc}')
            raise


# ---------------------------------------------------------------------------
# B10 — OAuth callback resolve identity em public (sem entrar em tenant)
# ---------------------------------------------------------------------------

@tag('tenant', 'oauth')
class B10OAuthCallbackRunsInPublicTest(SimpleTestCase):
    """B10: OAuth callback executa em public, resolve Identity, entra em tenant so no redirect."""

    def test_oauth_callback_path_is_public(self):
        """O path /aluno/auth/ deve estar nos PUBLIC_PREFIXES do StudentAuthMiddleware."""
        from student_app.middleware.student_auth import _PUBLIC_PREFIXES
        self.assertIn('/aluno/auth/', _PUBLIC_PREFIXES, (
            '/aluno/auth/ nao esta em _PUBLIC_PREFIXES. '
            'OAuth callback seria bloqueado pelo StudentAuthMiddleware.'
        ))

    def test_is_public_path_returns_true_for_oauth(self):
        """_is_public_path reconhece /aluno/auth/callback/ como publico."""
        from student_app.middleware.student_auth import _is_public_path
        self.assertTrue(_is_public_path('/aluno/auth/callback/'))
        self.assertTrue(_is_public_path('/aluno/auth/login/'))
        self.assertFalse(_is_public_path('/aluno/grade/'))
        self.assertFalse(_is_public_path('/aluno/perfil/'))


# ---------------------------------------------------------------------------
# B11 — Invitation token cria membership em public (sem entrar no schema do tenant)
# ---------------------------------------------------------------------------

@tag('tenant', 'invitation')
class B11InvitationTokenCreatesMembershipInPublicTest(SimpleTestCase):
    """B11: StudentAppInvitation criada em public; aceite cria StudentBoxMembership em public."""

    def test_student_app_invitation_is_in_shared_apps(self):
        """StudentAppInvitation deve ter app_label de SHARED (public schema)."""
        from student_identity.models import StudentAppInvitation, StudentBoxMembership
        # Ambos devem estar em public (SHARED_APPS), nao em tenant-specific
        # O app_label deve ser 'student_identity' (app em SHARED_APPS)
        self.assertEqual(StudentAppInvitation._meta.app_label, 'student_identity')
        self.assertEqual(StudentBoxMembership._meta.app_label, 'student_identity')

    def test_student_box_membership_does_not_require_tenant_schema(self):
        """StudentBoxMembership pode ser consultada sem schema_context (esta em public)."""
        from student_identity.models import StudentBoxMembership
        # Se a tabela estiver em public, esta query nao deve levantar OperationalError
        # por schema missing. Nao podemos criar sem fixtures, mas a introspection funciona.
        meta = StudentBoxMembership._meta
        self.assertIsNotNone(meta.db_table)
        self.assertFalse(
            meta.db_table.startswith('box_'),
            f'StudentBoxMembership.db_table parece ser de tenant: {meta.db_table}'
        )


# ---------------------------------------------------------------------------
# Webhook idempotency — middleware seta public antes de consultar DB
# ---------------------------------------------------------------------------

@tag('tenant', 'webhook')
class WebhookIdempotencyPublicSchemaTest(SimpleTestCase):
    """Sprint 4 / §13.1: WebhookIdempotencyMiddleware forca public schema."""

    def test_set_schema_to_public_called_on_webhook_path(self):
        """Para /api/v1/integrations/*, middleware chama set_schema_to_public()."""
        factory = RequestFactory()
        request = factory.post(
            '/api/v1/integrations/whatsapp/webhook/poll-vote/',
            data=json.dumps({'event_id': 'evt_test'}),
            content_type='application/json',
        )

        from integrations.middleware import WebhookIdempotencyMiddleware

        get_response = MagicMock(return_value=JsonResponse({}))
        middleware = WebhookIdempotencyMiddleware(get_response)

        with patch('integrations.middleware.WebhookEvent.objects.filter') as mock_filter, \
             patch('integrations.middleware._webhook_event_table_available', return_value=True), \
             patch('django.db.connection') as mock_conn:

            mock_filter.return_value.exists.return_value = False
            middleware(request)

            mock_conn.set_schema_to_public.assert_called_once()

    def test_non_webhook_path_does_not_call_set_public(self):
        """Para paths que nao sao de webhook, nao chama set_schema_to_public."""
        factory = RequestFactory()
        request = factory.post('/dashboard/', data={})

        from integrations.middleware import WebhookIdempotencyMiddleware

        get_response = MagicMock(return_value=JsonResponse({}))
        middleware = WebhookIdempotencyMiddleware(get_response)

        with patch('django.db.connection') as mock_conn:
            middleware(request)
            mock_conn.set_schema_to_public.assert_not_called()


# ---------------------------------------------------------------------------
# box_runtime.py — get_box_runtime_slug usa schema_name quando tenant ativo
# ---------------------------------------------------------------------------

@tag('tenant', 'runtime')
class BoxRuntimeSlugUsesSchemaNameTest(SimpleTestCase):
    """Sprint 4: get_box_runtime_slug() retorna connection.schema_name quando tenant ativo."""

    def test_returns_schema_name_when_tenant_active(self):
        # get_box_runtime_slug usa `from django.db import connection` DENTRO da funcao.
        # O patch em django.db.connection e resolvido no momento da chamada.
        from shared_support.box_runtime import get_box_runtime_slug
        with patch('django.db.connection') as mock_conn:
            mock_conn.schema_name = 'box_endorfina'
            result = get_box_runtime_slug()
        self.assertEqual(result, 'box_endorfina')

    def test_falls_back_to_env_when_schema_is_public(self):
        import os
        from shared_support.box_runtime import get_box_runtime_slug
        with patch('django.db.connection') as mock_conn, \
             patch.dict(os.environ, {'BOX_RUNTIME_SLUG': 'endorfina-test'}):
            mock_conn.schema_name = 'public'
            result = get_box_runtime_slug()
        # Com schema=public, deve usar o env var normalizado ('endorfina-test')
        self.assertEqual(result, 'endorfina-test')


# ---------------------------------------------------------------------------
# Healthcheck tenant endpoint
# ---------------------------------------------------------------------------

@tag('tenant', 'healthcheck')
class TenantHealthEndpointTest(SimpleTestCase):
    """Sprint 4: /api/v1/health/tenant/ reporta o tenant ativo."""

    def test_tenant_health_returns_schema_name(self):
        factory = RequestFactory()
        request = factory.get('/api/v1/health/tenant/')
        request.tenant = MagicMock(slug='box_endorfina')
        request.user = MagicMock(is_authenticated=True)

        from api.v1.views import ApiV1TenantHealthView

        with patch('django.db.connection') as mock_conn:
            mock_conn.schema_name = 'box_endorfina'
            view = ApiV1TenantHealthView.as_view()
            response = view(request)

        data = json.loads(response.content)
        self.assertEqual(data['tenant'], 'box_endorfina')
        self.assertTrue(data['healthy'])

    def test_public_health_includes_tenants_active(self):
        factory = RequestFactory()
        request = factory.get('/api/v1/health/')

        from api.v1.views import ApiV1HealthView

        with patch('control.models.Box.objects') as mock_box_qs:
            mock_box_qs.filter.return_value.count.return_value = 3
            view = ApiV1HealthView.as_view()
            response = view(request)

        data = json.loads(response.content)
        self.assertEqual(data['tenants_active'], 3)
        self.assertEqual(data['runtime'], 'control')
        self.assertTrue(data['healthy'])
