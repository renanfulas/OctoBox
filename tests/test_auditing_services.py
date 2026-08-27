"""
ARQUIVO: testes de auditing.services e signals (trilha de auditoria regulatória).

POR QUE EXISTE:
- AuditEvent vive em TENANT_APPS — INSERT em schema=public estoura
  ProgrammingError. _ensure_tenant_for_audit_write é a salvaguarda que
  resolve tenant antes da escrita.
- Antes deste arquivo: 0 testes para esse path. Auditoria perdida em
  fluxos pre-auth (login, logout, webhook) era silenciosa.
- Cobre Sprint 6 do plano de hardening.

CAMADA: L2 (services com banco) + L1 (signals).

SOURCE-UNDER-TEST:
- auditing/services.py:29 (_ensure_tenant_for_audit_write — 7 branches)
- auditing/services.py:76 (_write_audit_event em PUBLIC_SCHEMA)
- auditing/signals.py:23,36 (handlers de user_logged_in/out)

CONTRATO DE MOCK (Sprint 9 — corrigido para django-tenants):
- A função faz `from django.db import connection` (import local) e usa
  connection.schema_name + connection.set_tenant. Em django-tenants esses
  são gerenciados pelo wrapper; patch.object(connection, ..., create=True)
  conflitava no teardown. Solução: patch('django.db.connection') com
  MagicMock — controla schema_name/set_tenant SEM tocar o wrapper real.
  O ORM (Box/Membership.objects) usa connections['default'], não o proxy,
  então continua funcionando sob o patch.
- @pytest.mark.public_schema: a classe cria Box (modelo tenant) → precisa
  rodar no schema public (opt-out do schema_context autouse do conftest).
- Box de fundo: o fixture `test_tenant` cria um Box 'test' ACTIVE em
  PostgreSQL. setUp neutraliza todos os boxes (status -> INACTIVE, revertido
  pelo rollback do TestCase) para os testes controlarem a contagem absoluta.
- Usernames únicos (uuid) para evitar colisão sob paralelização.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.test import RequestFactory, TestCase

User = get_user_model()


def _uniq(prefix: str) -> str:
    return f'{prefix}_{uuid.uuid4().hex[:8]}'


# ===========================================================================
# _ensure_tenant_for_audit_write — 7 branches
# ===========================================================================

@pytest.mark.public_schema
class EnsureTenantForAuditWriteTest(TestCase):
    """L2: _ensure_tenant_for_audit_write — auditing/services.py:29.

    Branches:
    1. schema != 'public' → retorna None (já em tenant)
    2. actor com Membership primary_box ativa → set_tenant + retorna box
    3. Strategy 2 levanta exceção → cai para Strategy 3
    4. 1 Box ATIVO (pilot) → set_tenant + retorna box
    5. 0 ou ≥2 boxes ATIVOS → retorna None
    6. Strategy 3 levanta exceção → retorna None
    """

    def setUp(self):
        from control.models import Box
        # Neutraliza o(s) box(es) de fundo criados pela fixture test_tenant,
        # para que os testes controlem a contagem absoluta de boxes ATIVOS.
        # Revertido pelo rollback do TestCase ao fim de cada teste.
        Box.objects.update(status=Box.Status.SUSPENDED)
        self.user = User.objects.create_user(username=_uniq('audit_actor'), email='actor@x.com')

    def _mock_conn(self, schema_name='public'):
        """patch('django.db.connection') com schema_name e set_tenant controlados."""
        cm = patch('django.db.connection')
        mock_conn = cm.start()
        self.addCleanup(cm.stop)
        mock_conn.schema_name = schema_name
        return mock_conn

    # Branch 1: já em tenant
    def test_returns_none_when_already_in_tenant_schema(self):
        """Quando schema_name != 'public', função é no-op."""
        from auditing.services import _ensure_tenant_for_audit_write

        self._mock_conn(schema_name='box_some_tenant')
        result = _ensure_tenant_for_audit_write(self.user)
        self.assertIsNone(result)

    # Branch 2: actor com Membership primary
    def test_activates_box_via_actor_primary_membership(self):
        from control.models import Box, Membership
        from auditing.services import _ensure_tenant_for_audit_write

        box = Box.objects.create(
            slug='audit-primary', schema_name='box_audit_primary',
            display_name='Audit Primary Box', status=Box.Status.ACTIVE,
            owner_user=self.user,
        )
        Membership.objects.create(
            user=self.user, box=box, role=Membership.Role.OWNER, is_primary_box=True,
        )

        mock_conn = self._mock_conn(schema_name='public')
        result = _ensure_tenant_for_audit_write(self.user)

        self.assertEqual(result, box)
        mock_conn.set_tenant.assert_called_once_with(box)

    # Branch 3: Strategy 2 levanta, cai para Strategy 3
    def test_strategy2_exception_falls_through_to_strategy3(self):
        """Erro na consulta de Membership não impede pilot fallback."""
        from control.models import Box
        from auditing.services import _ensure_tenant_for_audit_write

        pilot_box = Box.objects.create(
            slug='audit-pilot', schema_name='box_audit_pilot',
            display_name='Pilot Box', status=Box.Status.ACTIVE, owner_user=self.user,
        )

        mock_conn = self._mock_conn(schema_name='public')
        with patch('control.models.Membership.objects') as mock_mgr:
            mock_mgr.select_related.side_effect = RuntimeError('membership lookup falhou')
            result = _ensure_tenant_for_audit_write(self.user)

        self.assertEqual(result, pilot_box)
        mock_conn.set_tenant.assert_called_once_with(pilot_box)

    # Branch 4: pilot fallback (1 box ativo) com actor=None
    def test_activates_single_active_box_when_actor_is_none(self):
        """Sem actor: pula Strategy 2, vai direto para Strategy 3."""
        from control.models import Box
        from auditing.services import _ensure_tenant_for_audit_write

        single_box = Box.objects.create(
            slug='audit-single', schema_name='box_audit_single',
            display_name='Single Active Box', status=Box.Status.ACTIVE, owner_user=self.user,
        )

        mock_conn = self._mock_conn(schema_name='public')
        result = _ensure_tenant_for_audit_write(actor=None)

        self.assertEqual(result, single_box)
        mock_conn.set_tenant.assert_called_once_with(single_box)

    # Branch 5a: 0 boxes ativos → None
    def test_returns_none_when_zero_active_boxes(self):
        from auditing.services import _ensure_tenant_for_audit_write

        self._mock_conn(schema_name='public')
        result = _ensure_tenant_for_audit_write(actor=None)
        self.assertIsNone(result)

    # Branch 5b: 2+ boxes ativos → None (pilot só ativa quando há exatamente 1)
    def test_returns_none_when_multiple_active_boxes(self):
        from control.models import Box
        from auditing.services import _ensure_tenant_for_audit_write

        Box.objects.create(slug='b1', schema_name='box_b1', display_name='B1',
                           status=Box.Status.ACTIVE, owner_user=self.user)
        Box.objects.create(slug='b2', schema_name='box_b2', display_name='B2',
                           status=Box.Status.ACTIVE, owner_user=self.user)

        self._mock_conn(schema_name='public')
        result = _ensure_tenant_for_audit_write(actor=None)
        self.assertIsNone(result)

    # Branch 6: Strategy 3 levanta → retorna None
    def test_strategy3_exception_returns_none(self):
        from auditing.services import _ensure_tenant_for_audit_write

        self._mock_conn(schema_name='public')
        with patch('control.models.Box.objects') as mock_box_mgr:
            mock_box_mgr.filter.side_effect = RuntimeError('box lookup falhou')
            result = _ensure_tenant_for_audit_write(actor=None)
        self.assertIsNone(result)


# ===========================================================================
# _write_audit_event — não pode explodir em PUBLIC_SCHEMA sem actor
# ===========================================================================

@pytest.mark.public_schema
class AsyncLogAuditEventTest(TestCase):
    """L2: _write_audit_event — auditing/services.py:76.

    Contrato: NUNCA propaga exceção, mesmo em schema=public sem tenant.
    """

    def setUp(self):
        from control.models import Box
        Box.objects.update(status=Box.Status.SUSPENDED)

    def test_does_not_raise_when_in_public_schema_without_actor(self):
        """webhook chega sem actor, schema=public, sem boxes ativos → não propaga."""
        from auditing.services import _write_audit_event

        with patch('django.db.connection') as mock_conn:
            mock_conn.schema_name = 'public'
            _write_audit_event(
                actor_id=None, action='webhook.received', target_model='',
                target_id='', target_label='', description='Stripe webhook received',
                metadata={'source': 'stripe'},
            )
        # Sem assert de exceção: o teste passa se chegou aqui sem levantar.

    def test_calls_audit_event_create_when_tenant_resolved(self):
        """Quando _ensure_tenant_for_audit_write resolve, AuditEvent.create é chamado."""
        from auditing.services import _write_audit_event

        with patch('auditing.models.AuditEvent.objects.create') as mock_create, \
             patch('auditing.services._ensure_tenant_for_audit_write', return_value=MagicMock()):
            _write_audit_event(
                actor_id=None, action='test.action', target_model='',
                target_id='', target_label='', description='test', metadata={'key': 'value'},
            )

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        self.assertEqual(call_kwargs['action'], 'test.action')
        self.assertEqual(call_kwargs['description'], 'test')

    def test_does_not_raise_when_audit_event_create_raises(self):
        """Best-effort: erro do AuditEvent.create é engolido (except Exception: pass)."""
        from auditing.services import _write_audit_event

        with patch('auditing.models.AuditEvent.objects.create') as mock_create, \
             patch('auditing.services._ensure_tenant_for_audit_write', return_value=None):
            mock_create.side_effect = RuntimeError('tabela boxcore_auditevent não existe em public')
            _write_audit_event(
                actor_id=None, action='x', target_model='',
                target_id='', target_label='', description='', metadata={},
            )

    def test_resolves_role_slug_when_actor_id_present(self):
        """Quando actor_id é dado, busca user e resolve role_slug."""
        from auditing.services import _write_audit_event

        actor = User.objects.create_user(username=_uniq('actor_with_role'), email='r@x.com')

        with patch('auditing.models.AuditEvent.objects.create') as mock_create, \
             patch('auditing.services._ensure_tenant_for_audit_write', return_value=MagicMock()), \
             patch('access.roles.get_user_role') as mock_role:
            mock_role.return_value = MagicMock(slug='owner')
            _write_audit_event(
                actor_id=actor.pk, action='x', target_model='',
                target_id='', target_label='', description='', metadata={},
            )

        mock_create.assert_called_once()
        self.assertEqual(mock_create.call_args.kwargs['actor_role'], 'owner')


# ===========================================================================
# Signal handlers — auditing/signals.py
#
# Onda 5b (2026-08-26): login/logout migraram de log_audit_event
# (AuditEvent, TENANT_APP) para log_platform_audit_event (PlatformAuditEvent,
# SHARED_APP) — ver docstring de auditing/signals.py e de
# auditing/services.py::log_platform_audit_event.
# ===========================================================================

class AuditingSignalsTest(TestCase):
    """L1: signals user_logged_in/out — auditing/signals.py:23,36.

    log_platform_audit_event é mockado, então os signals não tocam
    schema/tenant — não precisa de public_schema aqui (PlatformAuditEvent
    é SHARED_APP mesmo, mas o mock nem chega a tocar o banco).
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username=_uniq('signal_user'), email='s@x.com')

    def test_user_logged_in_signal_invokes_log_platform_audit_event_with_correct_kind(self):
        """Login deve registrar kind='auth.login' via log_platform_audit_event."""
        request = self.factory.get('/admin/login/')

        with patch('auditing.signals.log_platform_audit_event') as mock_log:
            user_logged_in.send(sender=User, request=request, user=self.user)

        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args.kwargs
        self.assertEqual(call_kwargs['actor'], self.user)
        self.assertEqual(call_kwargs['kind'], 'auth.login')
        self.assertEqual(call_kwargs['metadata']['path'], '/admin/login/')
        self.assertEqual(call_kwargs['metadata']['method'], 'GET')

    def test_user_logged_out_signal_invokes_log_platform_audit_event_with_correct_kind(self):
        """Logout deve registrar kind='auth.logout'."""
        request = self.factory.post('/admin/logout/')

        with patch('auditing.signals.log_platform_audit_event') as mock_log:
            user_logged_out.send(sender=User, request=request, user=self.user)

        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args.kwargs
        self.assertEqual(call_kwargs['actor'], self.user)
        self.assertEqual(call_kwargs['kind'], 'auth.logout')
        self.assertEqual(call_kwargs['metadata']['path'], '/admin/logout/')
        self.assertEqual(call_kwargs['metadata']['method'], 'POST')

    def test_login_signal_handles_missing_request_attributes_gracefully(self):
        """request=None não deve quebrar (getattr com default '')."""
        with patch('auditing.signals.log_platform_audit_event') as mock_log:
            user_logged_in.send(sender=User, request=None, user=self.user)

        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args.kwargs
        self.assertEqual(call_kwargs['metadata']['path'], '')
        self.assertEqual(call_kwargs['metadata']['method'], '')


# ===========================================================================
# Onda 5a (2026-08-26) — gate: schema restaurado + savepoint real
#
# SEM mock de connection nem de _ensure_tenant_for_audit_write — os testes
# acima provam a mecânica isolada; estes provam o comportamento fim-a-fim
# contra Postgres real, que é o que efetivamente muda com esta onda.
# ===========================================================================

@pytest.mark.public_schema
class LogAuditEventRestoresSchemaTest(TestCase):
    """Gate (1): connection.schema_name volta ao que era, mesmo quando
    _ensure_tenant_for_audit_write ativa um tenant de verdade para escrever.

    Antes da Onda 5a: log_audit_event ativava o tenant do actor e nunca
    devolvia — a conexão ficava presa em box_test até algo mais (ex.: o
    próximo TenantBySessionMiddleware) resetar. Este teste teria FALHADO
    contra o código anterior — não é um teste que passaria de qualquer jeito.
    """

    def setUp(self):
        from django.db import connection
        from django_tenants.utils import get_public_schema_name

        connection.set_schema_to_public()
        self.public_schema_name = get_public_schema_name()

    def test_schema_returns_to_public_after_activating_tenant_for_write(self):
        from django.db import connection
        from control.models import Membership
        from auditing.services import log_audit_event

        # conftest._auto_membership_for_test_users já dá Membership(role=OWNER,
        # is_primary_box=True) no box de teste a todo User criado aqui — é
        # exatamente o que _ensure_tenant_for_audit_write.Strategy 2 precisa
        # para resolver e ativar o tenant. Não recriar (duplicaria a unique
        # constraint user+box).
        actor = User.objects.create_user(username=_uniq('restore_actor'), email='a@x.com')
        self.assertTrue(
            Membership.objects.filter(user=actor, is_primary_box=True).exists(),
            'setup inválido: fixture do conftest não deu Membership ao actor',
        )

        self.assertEqual(connection.schema_name, self.public_schema_name)

        log_audit_event(actor=actor, action='test.onda5a.restore', description='prova de restore')

        self.assertEqual(
            connection.schema_name, self.public_schema_name,
            'log_audit_event deixou a conexão presa no schema do tenant após escrever o evento — '
            'o restore da Onda 5a não está funcionando.',
        )

    def test_public_path_without_resolvable_tenant_stays_on_public(self):
        """Sem actor e sem box único ativo: _ensure_tenant_for_audit_write
        não resolve nada — a conexão nunca devia ter saído de public."""
        from django.db import connection
        from control.models import Box
        from auditing.services import log_audit_event

        Box.objects.update(status=Box.Status.SUSPENDED)

        log_audit_event(actor=None, action='test.onda5a.no_tenant', description='')

        self.assertEqual(connection.schema_name, self.public_schema_name)


@pytest.mark.public_schema
class LogAuditEventSavepointTest(TestCase):
    """Gate (2): falha na escrita do AuditEvent não corrompe uma transação
    externa em andamento.

    Antes da Onda 5a: auditing/services.py não tinha nenhum transaction.atomic
    — o ADR-008 prescreve o trio "facade + savepoint + try/except" e lista
    este arquivo como implementação, mas o savepoint nunca existiu. Descoberto
    ao tentar rodar a verificação da Onda 1 dentro de um transaction.atomic:
    o INSERT falhou em public, foi engolido pelo except, e a query seguinte
    (uma simples asserção) morreu com TransactionManagementError. Este teste
    reproduz exatamente essa sequência.
    """

    def test_failed_audit_write_does_not_poison_external_transaction(self):
        """
        NÃO mocka AuditEvent.objects.create — de propósito. Mockar a chamada
        inteira substitui a exceção por uma levantada em Python puro, sem
        NENHUM SQL real chegando ao Postgres — a transação no banco nunca
        entra em estado abortado de verdade, e o teste passaria em QUALQUER
        versão do código (falso-negativo, não prova nada). A falha real
        precisa vir do banco: mantém schema=public (via
        _ensure_tenant_for_audit_write mockado pra None, simulando o caso
        real de webhook sem actor e sem box único ativo) e deixa o INSERT
        rodar de verdade contra public, onde boxcore_auditevent não existe —
        um ProgrammingError genuíno do Postgres, que é o que aborta a
        transação de verdade.
        """
        from django.db import transaction
        from control.models import Box
        from auditing.services import log_audit_event

        actor = User.objects.create_user(username=_uniq('savepoint_actor'), email='s@x.com')

        with patch('auditing.services._ensure_tenant_for_audit_write', return_value=None):
            with transaction.atomic():
                log_audit_event(actor=actor, action='test.onda5a.savepoint', description='')

                # Sem savepoint, esta query trivial levantaria
                # TransactionManagementError — era assim que o bug foi
                # descoberto. Se chegou aqui e o exists() funciona, a
                # transação externa sobreviveu à falha real do audit.
                self.assertTrue(Box.objects.filter(slug='test').exists())

        # A transação externa (sem exceção não tratada) commitou normalmente
        # — nenhuma escrita legítima foi perdida por causa do audit falho.


# ===========================================================================
# Onda 5b (2026-08-26) — log_platform_audit_event
#
# Gate: escreve de QUALQUER schema sem fallback frágil (diferente de
# log_audit_event/_write_audit_event, que dependem de
# _ensure_tenant_for_audit_write achar algum tenant); PIIScrubber aplicado
# ao payload (nenhum dos 3 call sites que já criavam PlatformAuditEvent
# direto fazia isso); painel dev mescla as duas fontes corretamente.
# ===========================================================================

@pytest.mark.public_schema
class LogPlatformAuditEventTest(TestCase):
    def setUp(self):
        from django.db import connection
        from control.models import Box

        connection.set_schema_to_public()
        Box.objects.update(status=Box.Status.SUSPENDED)  # sem nenhum box ATIVO — pilot fallback nunca ajudaria aqui

    def test_writes_successfully_from_public_with_zero_active_boxes(self):
        """O ganho central da Onda 5b: sem box ATIVO nenhum (cenário em que
        log_audit_event/_ensure_tenant_for_audit_write teria retornado None
        e a escrita seria descartada), a escrita ainda funciona — porque
        PlatformAuditEvent é SHARED_APP, não precisa de tenant nenhum."""
        from control.models import PlatformAuditEvent
        from auditing.services import log_platform_audit_event

        actor = User.objects.create_user(username=_uniq('platform_actor'), email='p@x.com')

        event = log_platform_audit_event(actor=actor, kind='test.onda5b.no_box', description='sem box ativo')

        self.assertIsNotNone(event, 'log_platform_audit_event não deveria retornar None aqui — é exatamente o caso que ela resolve')
        self.assertTrue(PlatformAuditEvent.objects.filter(pk=event.pk, kind='test.onda5b.no_box').exists())

    def test_target_box_defaults_to_none_never_guessed(self):
        """target_box não é adivinhado via primary Membership — mesmo com
        o actor tendo uma, login/logout não deve atribuir a um box."""
        from control.models import Box, Membership
        from auditing.services import log_platform_audit_event

        actor = User.objects.create_user(username=_uniq('has_primary'), email='hp@x.com')
        box = Box.objects.create(
            slug='onda5b-box', schema_name='box_onda5b', display_name='Onda5b Box',
            status=Box.Status.ACTIVE, owner_user=actor,
        )
        Membership.objects.create(user=actor, box=box, role=Membership.Role.OWNER, is_primary_box=True)

        event = log_platform_audit_event(actor=actor, kind='test.onda5b.has_primary')

        self.assertIsNone(event.target_box)

    def test_payload_is_scrubbed_for_pii(self):
        """PIIScrubber aplicado ao payload — nenhum dos 3 call sites que já
        criavam PlatformAuditEvent direto (control/services.py,
        integrations/stripe/router.py) fazia isso; o caminho novo não repete
        a lacuna."""
        from auditing.services import log_platform_audit_event

        actor = User.objects.create_user(username=_uniq('scrub_actor'), email='sc@x.com')

        event = log_platform_audit_event(
            actor=actor, kind='test.onda5b.scrub',
            metadata={'password': 'hunter2', 'cpf': '111.222.333-44', 'path': '/login/'},
        )

        self.assertEqual(event.payload['password'], '[REDACTED]')
        self.assertEqual(event.payload['cpf'], '[REDACTED]')
        self.assertEqual(event.payload['path'], '/login/')

    def test_description_and_actor_role_fold_into_payload(self):
        """PlatformAuditEvent não tem campo description/actor_role dedicado
        — ambos vão para payload (ver docstring de log_platform_audit_event).

        get_user_role só lê Membership.role quando o middleware anexou
        _octobox_membership ao request.user (não é o caso aqui, sem
        request) — cai no fallback de Group, que é como staff real resolve
        role fora de um request (a mesma situação em que
        log_platform_audit_event roda, dentro do signal de login). Group
        sincronizado com Membership.role via bootstrap_roles + groups.add,
        igual ao setup de access/tests/test_access_boundary.py.
        """
        from django.contrib.auth.models import Group
        from django.core.management import call_command
        from access.roles import ROLE_OWNER
        from control.models import Box, Membership
        from auditing.services import log_platform_audit_event

        call_command('bootstrap_roles')
        actor = User.objects.create_user(username=_uniq('role_actor'), email='ra@x.com')
        actor.groups.add(Group.objects.get(name=ROLE_OWNER))
        box = Box.objects.create(
            slug='onda5b-role-box', schema_name='box_onda5b_role', display_name='Onda5b Role Box',
            status=Box.Status.ACTIVE, owner_user=actor,
        )
        Membership.objects.create(user=actor, box=box, role=Membership.Role.OWNER, is_primary_box=True)

        event = log_platform_audit_event(actor=actor, kind='test.onda5b.role', description='login de teste')

        self.assertEqual(event.payload['description'], 'login de teste')
        self.assertEqual(event.payload['actor_role'], ROLE_OWNER)

    def test_does_not_raise_when_database_write_fails(self):
        """Best-effort — mesma filosofia do ADR-008."""
        from auditing.services import log_platform_audit_event

        with patch('control.models.PlatformAuditEvent.objects.create') as mock_create:
            mock_create.side_effect = RuntimeError('banco fora do ar')
            result = log_platform_audit_event(actor=None, kind='test.onda5b.db_down')

        self.assertIsNone(result)


@pytest.mark.public_schema
class DevWorkspaceAuditPanelMergeTest(TestCase):
    """Onda 5b: build_dev_workspace_snapshot mescla AuditEvent (per-tenant)
    com PlatformAuditEvent (SHARED_APP) — sem isso, login/logout somem do
    painel (eram AuditEvent, agora são PlatformAuditEvent)."""

    def test_recent_audit_events_includes_both_sources_sorted_by_recency(self):
        from django_tenants.utils import schema_context
        from control.models import Box, PlatformAuditEvent
        from auditing.models import AuditEvent
        from operations.queries import build_dev_workspace_snapshot

        test_box = Box.objects.get(slug='test')
        actor = User.objects.create_user(username=_uniq('panel_actor'), email='pa@x.com')

        PlatformAuditEvent.objects.create(actor_user=actor, kind='auth.login', payload={'actor_role': 'owner'})
        with schema_context(test_box.schema_name):
            AuditEvent.objects.create(
                actor=actor, actor_role='owner', action='admin_change_payment',
                target_model='payment', target_id='1', target_label='Pagamento #1',
                description='', metadata={},
            )

            snapshot = build_dev_workspace_snapshot()

        actions = [row.action for row in snapshot['recent_audit_events']]
        self.assertIn('auth.login', actions)
        self.assertIn('admin_change_payment', actions)
        # ordenado por created_at desc — não assume ordem de criação, só que
        # a lista inteira está em ordem não-crescente de created_at.
        created_ats = [row.created_at for row in snapshot['recent_audit_events']]
        self.assertEqual(created_ats, sorted(created_ats, reverse=True))

    def test_eventos_auditados_counts_both_sources(self):
        from django_tenants.utils import schema_context
        from control.models import Box, PlatformAuditEvent
        from auditing.models import AuditEvent
        from operations.queries import build_dev_workspace_snapshot

        test_box = Box.objects.get(slug='test')
        with schema_context(test_box.schema_name):
            baseline = build_dev_workspace_snapshot()['technical_metrics']['eventos_auditados']

            PlatformAuditEvent.objects.create(kind='test.onda5b.count')
            AuditEvent.objects.create(
                action='test.onda5b.count', target_model='', target_id='',
                target_label='', description='', metadata={},
            )

            after = build_dev_workspace_snapshot()['technical_metrics']['eventos_auditados']

        self.assertEqual(after, baseline + 2)
