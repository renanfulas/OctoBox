"""
ARQUIVO: testes de auditing.services e signals (trilha de auditoria regulatória).

POR QUE EXISTE:
- AuditEvent vive em TENANT_APPS — INSERT em schema=public estoura
  ProgrammingError. _ensure_tenant_for_audit_write é a salvaguarda que
  resolve tenant antes da escrita.
- Antes deste arquivo: 0 testes para esse path. Auditoria perdida em
  fluxos pre-auth (login, logout, webhook) era silenciosa.
- Cobre Sprint 6 do plano de hardening.

CAMADA: L1 (signals) + L2 (services com banco).

SOURCE-UNDER-TEST:
- auditing/services.py:29 (_ensure_tenant_for_audit_write — 7 branches)
- auditing/services.py:76 (async_log_audit_event em PUBLIC_SCHEMA)
- auditing/signals.py:23,36 (handlers de user_logged_in/out)

CONTRATO DE MOCK:
- connection.set_tenant: patch para não exigir django-tenants em SQLite.
- AuditEvent.objects.create: patch para validar parâmetros sem precisar
  do schema tenant criado.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.test import RequestFactory, TestCase

User = get_user_model()


# ===========================================================================
# _ensure_tenant_for_audit_write — 7 branches
# ===========================================================================

class EnsureTenantForAuditWriteTest(TestCase):
    """L2: _ensure_tenant_for_audit_write — auditing/services.py:29.

    Branches:
    1. schema != 'public' → retorna None (já em tenant)
    2. actor com Membership primary_box ativa → set_tenant + retorna box
    3. Strategy 2 levanta exceção → cai para Strategy 3
    4. 1 Box ATIVO (pilot) → set_tenant + retorna box
    5. 0 ou ≥2 boxes ATIVOS → retorna None
    6. Strategy 3 levanta exceção → retorna None
    7. Outer try levanta exceção → retorna None
    """

    def setUp(self):
        self.user = User.objects.create_user(username='audit_actor', email='actor@x.com')

    # Branch 1: já em tenant
    def test_returns_none_when_already_in_tenant_schema(self):
        """Quando schema_name != 'public', função é no-op."""
        from auditing.services import _ensure_tenant_for_audit_write
        from django.db import connection

        with patch.object(connection, 'schema_name', 'box_some_tenant', create=True):
            result = _ensure_tenant_for_audit_write(self.user)
        self.assertIsNone(result)

    # Branch 2: actor com Membership primary
    def test_activates_box_via_actor_primary_membership(self):
        from control.models import Box, Membership
        from auditing.services import _ensure_tenant_for_audit_write
        from django.db import connection

        box = Box.objects.create(
            slug='audit-primary',
            schema_name='box_audit_primary',
            display_name='Audit Primary Box',
            status=Box.Status.ACTIVE,
            owner_user=self.user,
        )
        Membership.objects.create(
            user=self.user,
            box=box,
            role=Membership.Role.OWNER,
            is_primary_box=True,
        )

        # Schema atual = 'public' (default em SQLite)
        with patch.object(connection, 'schema_name', 'public', create=True), \
             patch.object(connection, 'set_tenant', create=True) as mock_set_tenant:
            result = _ensure_tenant_for_audit_write(self.user)

        self.assertEqual(result, box)
        mock_set_tenant.assert_called_once_with(box)

    # Branch 3: Strategy 2 levanta, cai para Strategy 3
    def test_strategy2_exception_falls_through_to_strategy3(self):
        """Erro na consulta de Membership não impede pilot fallback."""
        from control.models import Box
        from auditing.services import _ensure_tenant_for_audit_write
        from django.db import connection

        # Cria 1 box ativo (sem membership para o actor) → strategy 3 deve resolver
        pilot_box = Box.objects.create(
            slug='audit-pilot',
            schema_name='box_audit_pilot',
            display_name='Pilot Box',
            status=Box.Status.ACTIVE,
            owner_user=self.user,
        )

        with patch.object(connection, 'schema_name', 'public', create=True), \
             patch.object(connection, 'set_tenant', create=True) as mock_set_tenant, \
             patch('control.models.Membership.objects') as mock_mgr:
            mock_mgr.select_related.side_effect = RuntimeError('membership lookup falhou')
            result = _ensure_tenant_for_audit_write(self.user)

        self.assertEqual(result, pilot_box)
        mock_set_tenant.assert_called_once_with(pilot_box)

    # Branch 4: pilot fallback (1 box ativo) com actor=None
    def test_activates_single_active_box_when_actor_is_none(self):
        """Sem actor: pula Strategy 2, vai direto para Strategy 3."""
        from control.models import Box
        from auditing.services import _ensure_tenant_for_audit_write
        from django.db import connection

        single_box = Box.objects.create(
            slug='audit-single',
            schema_name='box_audit_single',
            display_name='Single Active Box',
            status=Box.Status.ACTIVE,
            owner_user=self.user,
        )

        with patch.object(connection, 'schema_name', 'public', create=True), \
             patch.object(connection, 'set_tenant', create=True) as mock_set_tenant:
            result = _ensure_tenant_for_audit_write(actor=None)

        self.assertEqual(result, single_box)
        mock_set_tenant.assert_called_once_with(single_box)

    # Branch 5a: 0 boxes ativos → None
    def test_returns_none_when_zero_active_boxes(self):
        from auditing.services import _ensure_tenant_for_audit_write
        from django.db import connection

        with patch.object(connection, 'schema_name', 'public', create=True):
            result = _ensure_tenant_for_audit_write(actor=None)

        self.assertIsNone(result)

    # Branch 5b: 2+ boxes ativos → None (pilot só ativa quando há exatamente 1)
    def test_returns_none_when_multiple_active_boxes(self):
        from control.models import Box
        from auditing.services import _ensure_tenant_for_audit_write
        from django.db import connection

        Box.objects.create(
            slug='b1', schema_name='box_b1', display_name='B1',
            status=Box.Status.ACTIVE, owner_user=self.user,
        )
        Box.objects.create(
            slug='b2', schema_name='box_b2', display_name='B2',
            status=Box.Status.ACTIVE, owner_user=self.user,
        )

        with patch.object(connection, 'schema_name', 'public', create=True):
            result = _ensure_tenant_for_audit_write(actor=None)

        self.assertIsNone(result)

    # Branch 6: Strategy 3 levanta → retorna None
    def test_strategy3_exception_returns_none(self):
        from auditing.services import _ensure_tenant_for_audit_write
        from django.db import connection

        with patch.object(connection, 'schema_name', 'public', create=True), \
             patch('control.models.Box.objects') as mock_box_mgr:
            mock_box_mgr.filter.side_effect = RuntimeError('box lookup falhou')
            result = _ensure_tenant_for_audit_write(actor=None)

        self.assertIsNone(result)


# ===========================================================================
# async_log_audit_event — não pode explodir em PUBLIC_SCHEMA sem actor
# ===========================================================================

class AsyncLogAuditEventTest(TestCase):
    """L2: async_log_audit_event — auditing/services.py:76.

    Contrato: NUNCA propaga exceção, mesmo em schema=public sem tenant.
    """

    def test_does_not_raise_when_in_public_schema_without_actor(self):
        """Cenário: webhook chega sem actor, schema=public, sem boxes ativos.

        Mesmo sem nenhuma strategy resolver, a função engole exceção
        (best-effort audit) e segue. Validamos só que NÃO propaga.
        """
        from auditing.services import async_log_audit_event
        from django.db import connection

        with patch.object(connection, 'schema_name', 'public', create=True):
            # Não levanta — tudo certo
            async_log_audit_event(
                actor_id=None,
                action='webhook.received',
                target_model='',
                target_id='',
                target_label='',
                description='Stripe webhook received',
                metadata={'source': 'stripe'},
            )

    def test_calls_audit_event_create_when_tenant_resolved(self):
        """Quando _ensure_tenant_for_audit_write resolve, AuditEvent.create é chamado."""
        from auditing.services import async_log_audit_event

        with patch('auditing.models.AuditEvent.objects.create') as mock_create, \
             patch('auditing.services._ensure_tenant_for_audit_write', return_value=MagicMock()):
            async_log_audit_event(
                actor_id=None,
                action='test.action',
                target_model='',
                target_id='',
                target_label='',
                description='test',
                metadata={'key': 'value'},
            )

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        self.assertEqual(call_kwargs['action'], 'test.action')
        self.assertEqual(call_kwargs['description'], 'test')

    def test_does_not_raise_when_audit_event_create_raises(self):
        """Best-effort: erro do AuditEvent.create é engolido (except Exception: pass)."""
        from auditing.services import async_log_audit_event

        with patch('auditing.models.AuditEvent.objects.create') as mock_create, \
             patch('auditing.services._ensure_tenant_for_audit_write', return_value=None):
            mock_create.side_effect = RuntimeError('tabela boxcore_auditevent não existe em public')
            # Não levanta — engolido
            async_log_audit_event(
                actor_id=None,
                action='x',
                target_model='',
                target_id='',
                target_label='',
                description='',
                metadata={},
            )

    def test_resolves_role_slug_when_actor_id_present(self):
        """Quando actor_id é dado, busca user e resolve role_slug."""
        from auditing.services import async_log_audit_event

        actor = User.objects.create_user(username='actor_with_role', email='r@x.com')

        with patch('auditing.models.AuditEvent.objects.create') as mock_create, \
             patch('auditing.services._ensure_tenant_for_audit_write', return_value=MagicMock()), \
             patch('access.roles.get_user_role') as mock_role:
            mock_role.return_value = MagicMock(slug='owner')
            async_log_audit_event(
                actor_id=actor.pk,
                action='x',
                target_model='',
                target_id='',
                target_label='',
                description='',
                metadata={},
            )

        mock_create.assert_called_once()
        self.assertEqual(mock_create.call_args.kwargs['actor_role'], 'owner')


# ===========================================================================
# Signal handlers — auditing/signals.py
# ===========================================================================

class AuditingSignalsTest(TestCase):
    """L1+L2: signals user_logged_in/out — auditing/signals.py:23,36."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='signal_user', email='s@x.com')

    def test_user_logged_in_signal_invokes_log_audit_event_with_correct_action(self):
        """Login deve registrar action='user_login' via log_audit_event."""
        request = self.factory.get('/admin/login/')

        with patch('auditing.signals.log_audit_event') as mock_log:
            user_logged_in.send(sender=User, request=request, user=self.user)

        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args.kwargs
        self.assertEqual(call_kwargs['actor'], self.user)
        self.assertEqual(call_kwargs['action'], 'user_login')
        self.assertEqual(call_kwargs['metadata']['path'], '/admin/login/')
        self.assertEqual(call_kwargs['metadata']['method'], 'GET')

    def test_user_logged_out_signal_invokes_log_audit_event_with_correct_action(self):
        """Logout deve registrar action='user_logout'."""
        request = self.factory.post('/admin/logout/')

        with patch('auditing.signals.log_audit_event') as mock_log:
            user_logged_out.send(sender=User, request=request, user=self.user)

        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args.kwargs
        self.assertEqual(call_kwargs['actor'], self.user)
        self.assertEqual(call_kwargs['action'], 'user_logout')
        self.assertEqual(call_kwargs['metadata']['path'], '/admin/logout/')
        self.assertEqual(call_kwargs['metadata']['method'], 'POST')

    def test_login_signal_handles_missing_request_attributes_gracefully(self):
        """request sem path/method (request = None) não deve quebrar."""
        with patch('auditing.signals.log_audit_event') as mock_log:
            user_logged_in.send(sender=User, request=None, user=self.user)

        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args.kwargs
        # getattr com default '' garante que path/method viram strings vazias
        self.assertEqual(call_kwargs['metadata']['path'], '')
        self.assertEqual(call_kwargs['metadata']['method'], '')
