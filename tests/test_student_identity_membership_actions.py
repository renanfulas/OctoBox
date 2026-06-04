"""
ARQUIVO: testes de student_identity.staff_membership_actions.

POR QUE EXISTE:
- StudentInvitationMembershipActionsMixin concentra o ciclo de vida de
  membership (aprovar, trocar e-mail, suspender, reativar, revogar) e o
  realinhamento de identidade. O coverage report do PR #115 apontou
  staff_membership_actions.py em ~61% — guard de role, not-found, guards de
  estado e caminhos felizes em sua maioria sem cobertura.

CAMADA: L1 (unit). Sem banco e sem tenant real: a view e instanciada solta
e membership/identity/AuditEvent sao mockados, espelhando o harness ja
estabelecido em tests/test_student_identity_staff_views.py.

SOURCE-UNDER-TEST:
- student_identity/staff_membership_actions.py
  (_handle_approve/_change_email/_suspend/_reactivate/_revoke_membership,
   _realign_identity_after_membership_loss, _update_student_email_in_tenant)

CONTRATO DE MOCK:
- StudentBoxMembership.objects / AuditEvent / messages / redirect / timezone:
  mockados no namespace do modulo.
- _require_action_roles: stub na view de teste (retorna None = autorizado,
  ou um sentinel = negado), espelhando o contrato real.
- StudentBoxMembershipStatus: usa os valores reais do enum.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from access.roles import ROLE_RECEPTION
from student_identity.models import StudentBoxMembershipStatus


REDIRECT_SENTINEL = 'REDIRECT::student-invitation-operations'
DENIED_SENTINEL = 'DENIED::role'


def _make_view(*, denied: bool = False):
    """View minima com os stubs que o mixin espera da view real."""
    from student_identity.staff_membership_actions import (
        StudentInvitationMembershipActionsMixin,
    )

    class _V(StudentInvitationMembershipActionsMixin):
        membership_approval_roles = ('reception', 'manager', 'owner', 'dev')
        invite_operator_roles = ('owner', 'dev', 'manager', 'reception')
        membership_lifecycle_roles = ('manager', 'owner', 'dev')

        def _get_actor_role_slug(self, request):
            return 'manager'

        def _require_action_roles(self, request, *, allowed_roles, denied_message):
            return DENIED_SENTINEL if denied else None

    return _V()


def _make_request(post=None):
    request = MagicMock()
    request.user = MagicMock()
    request.user.id = 7
    request.POST = post or {'membership_id': '1'}
    return request


def _make_membership(**overrides):
    membership = MagicMock()
    membership.id = 1
    membership.student_id = 55
    membership.identity_id = 9
    membership.identity = MagicMock(
        id=9, email='old@example.com', student_name='Aluno Teste',
        primary_box_root_slug='academia-x',
    )
    membership.box_root_slug = 'academia-x'
    membership.status = StudentBoxMembershipStatus.ACTIVE
    for key, value in overrides.items():
        setattr(membership, key, value)
    return membership


def _patch_membership_lookup(membership):
    """Faz _get_membership_for_management/approve lookup -> membership."""
    chain = MagicMock()
    chain.select_related.return_value.filter.return_value.first.return_value = membership
    return patch(
        'student_identity.staff_membership_actions.StudentBoxMembership.objects',
        chain,
    )


@patch('student_identity.staff_membership_actions.redirect', return_value=REDIRECT_SENTINEL)
@patch('student_identity.staff_membership_actions.messages')
@patch('student_identity.staff_membership_actions.AuditEvent')
class ApproveMembershipTest(unittest.TestCase):
    def test_denied_role_short_circuits(self, mock_audit, mock_messages, mock_redirect):
        result = _make_view(denied=True)._handle_approve_membership(_make_request())
        self.assertEqual(result, DENIED_SENTINEL)
        mock_audit.objects.create.assert_not_called()

    def test_not_found_shows_error(self, mock_audit, mock_messages, mock_redirect):
        with _patch_membership_lookup(None):
            result = _make_view()._handle_approve_membership(_make_request())
        mock_messages.error.assert_called_once()
        self.assertEqual(result, REDIRECT_SENTINEL)

    def test_happy_path_marks_active_and_audits(self, mock_audit, mock_messages, mock_redirect):
        membership = _make_membership(status=StudentBoxMembershipStatus.PENDING_APPROVAL)
        with _patch_membership_lookup(membership):
            result = _make_view()._handle_approve_membership(_make_request())
        membership.mark_active.assert_called_once()
        membership.save.assert_called_once()
        mock_audit.objects.create.assert_called_once()
        mock_messages.success.assert_called_once()
        self.assertEqual(result, REDIRECT_SENTINEL)


@patch('student_identity.staff_membership_actions.redirect', return_value=REDIRECT_SENTINEL)
@patch('student_identity.staff_membership_actions.messages')
@patch('student_identity.staff_membership_actions.AuditEvent')
@patch('student_identity.staff_membership_actions._update_student_email_in_tenant')
class ChangeEmailTest(unittest.TestCase):
    def test_denied_role_short_circuits(self, mock_update, mock_audit, mock_messages, mock_redirect):
        result = _make_view(denied=True)._handle_change_email(_make_request())
        self.assertEqual(result, DENIED_SENTINEL)

    def test_not_found_shows_error(self, mock_update, mock_audit, mock_messages, mock_redirect):
        with _patch_membership_lookup(None):
            _make_view()._handle_change_email(_make_request())
        mock_messages.error.assert_called_once()

    def test_blank_email_shows_error(self, mock_update, mock_audit, mock_messages, mock_redirect):
        membership = _make_membership()
        req = _make_request({'membership_id': '1', 'new_email': '   '})
        with _patch_membership_lookup(membership):
            _make_view()._handle_change_email(req)
        mock_messages.error.assert_called_once()
        mock_update.assert_not_called()

    def test_invalid_email_shows_error(self, mock_update, mock_audit, mock_messages, mock_redirect):
        membership = _make_membership()
        req = _make_request({'membership_id': '1', 'new_email': 'not-an-email'})
        with _patch_membership_lookup(membership):
            _make_view()._handle_change_email(req)
        mock_messages.error.assert_called_once()
        mock_update.assert_not_called()

    def test_same_email_shows_info(self, mock_update, mock_audit, mock_messages, mock_redirect):
        membership = _make_membership()
        membership.identity.email = 'same@example.com'
        req = _make_request({'membership_id': '1', 'new_email': 'same@example.com'})
        with _patch_membership_lookup(membership):
            _make_view()._handle_change_email(req)
        mock_messages.info.assert_called_once()
        mock_update.assert_not_called()

    def test_happy_path_updates_identity_and_tenant(self, mock_update, mock_audit, mock_messages, mock_redirect):
        membership = _make_membership()
        req = _make_request({'membership_id': '1', 'new_email': 'new@example.com', 'change_reason': 'pedido'})
        with _patch_membership_lookup(membership):
            result = _make_view()._handle_change_email(req)
        self.assertEqual(membership.identity.email, 'new@example.com')
        membership.identity.save.assert_called_once()
        mock_update.assert_called_once()
        mock_audit.objects.create.assert_called_once()
        mock_messages.success.assert_called_once()
        self.assertEqual(result, REDIRECT_SENTINEL)

    @patch('student_identity.staff_membership_actions.timezone')
    def test_reception_second_change_blocked(self, mock_tz, mock_update, mock_audit, mock_messages, mock_redirect):
        # ROLE_RECEPTION com 1 troca recente no mes -> bloqueia a segunda
        view = _make_view()
        view._get_actor_role_slug = lambda request: ROLE_RECEPTION
        membership = _make_membership()
        mock_audit.objects.filter.return_value.count.return_value = 1
        req = _make_request({'membership_id': '1', 'new_email': 'new@example.com'})
        with _patch_membership_lookup(membership):
            result = view._handle_change_email(req)
        mock_messages.error.assert_called_once()
        mock_update.assert_not_called()
        self.assertEqual(result, REDIRECT_SENTINEL)

    @patch('student_identity.staff_membership_actions.timezone')
    def test_reception_first_change_allowed(self, mock_tz, mock_update, mock_audit, mock_messages, mock_redirect):
        # ROLE_RECEPTION com 0 trocas recentes -> primeira troca passa normalmente
        view = _make_view()
        view._get_actor_role_slug = lambda request: ROLE_RECEPTION
        membership = _make_membership()
        mock_audit.objects.filter.return_value.count.return_value = 0
        req = _make_request({'membership_id': '1', 'new_email': 'new@example.com'})
        with _patch_membership_lookup(membership):
            result = view._handle_change_email(req)
        self.assertEqual(membership.identity.email, 'new@example.com')
        mock_update.assert_called_once()
        mock_messages.success.assert_called_once()
        self.assertEqual(result, REDIRECT_SENTINEL)


@patch('student_identity.staff_membership_actions.redirect', return_value=REDIRECT_SENTINEL)
@patch('student_identity.staff_membership_actions.messages')
@patch('student_identity.staff_membership_actions.AuditEvent')
class SuspendMembershipTest(unittest.TestCase):
    def test_denied_role_short_circuits(self, mock_audit, mock_messages, mock_redirect):
        result = _make_view(denied=True)._handle_suspend_membership(_make_request())
        self.assertEqual(result, DENIED_SENTINEL)

    def test_not_found_shows_error(self, mock_audit, mock_messages, mock_redirect):
        with _patch_membership_lookup(None):
            _make_view()._handle_suspend_membership(_make_request())
        mock_messages.error.assert_called_once()

    def test_non_active_shows_info(self, mock_audit, mock_messages, mock_redirect):
        membership = _make_membership(status=StudentBoxMembershipStatus.REVOKED)
        with _patch_membership_lookup(membership):
            _make_view()._handle_suspend_membership(_make_request())
        mock_messages.info.assert_called_once()

    def test_happy_path_suspends_realigns_and_audits(self, mock_audit, mock_messages, mock_redirect):
        membership = _make_membership(status=StudentBoxMembershipStatus.ACTIVE)
        # sem fallback ativo -> realign nao altera identity
        with patch.object(
            type(_make_view()), '_find_fallback_active_membership', return_value=None
        ):
            with _patch_membership_lookup(membership):
                _make_view()._handle_suspend_membership(_make_request())
        membership.mark_suspended_financial.assert_called_once()
        mock_audit.objects.create.assert_called_once()
        mock_messages.success.assert_called_once()


@patch('student_identity.staff_membership_actions.redirect', return_value=REDIRECT_SENTINEL)
@patch('student_identity.staff_membership_actions.messages')
@patch('student_identity.staff_membership_actions.AuditEvent')
class ReactivateMembershipTest(unittest.TestCase):
    def test_denied_role_short_circuits(self, mock_audit, mock_messages, mock_redirect):
        result = _make_view(denied=True)._handle_reactivate_membership(_make_request())
        self.assertEqual(result, DENIED_SENTINEL)

    def test_not_found_shows_error(self, mock_audit, mock_messages, mock_redirect):
        with _patch_membership_lookup(None):
            _make_view()._handle_reactivate_membership(_make_request())
        mock_messages.error.assert_called_once()

    def test_happy_path_keeps_existing_primary(self, mock_audit, mock_messages, mock_redirect):
        membership = _make_membership(status=StudentBoxMembershipStatus.REVOKED)
        membership.identity.primary_box_root_slug = 'academia-x'  # ja setado -> nao re-salva identity
        with _patch_membership_lookup(membership):
            _make_view()._handle_reactivate_membership(_make_request())
        membership.mark_active.assert_called_once()
        membership.identity.save.assert_not_called()
        mock_audit.objects.create.assert_called_once()

    def test_invalid_status_shows_info(self, mock_audit, mock_messages, mock_redirect):
        membership = _make_membership(status=StudentBoxMembershipStatus.ACTIVE)
        with _patch_membership_lookup(membership):
            _make_view()._handle_reactivate_membership(_make_request())
        mock_messages.info.assert_called_once()

    def test_happy_path_reactivates_and_sets_primary_when_missing(self, mock_audit, mock_messages, mock_redirect):
        membership = _make_membership(status=StudentBoxMembershipStatus.SUSPENDED_FINANCIAL)
        membership.identity.primary_box_root_slug = ''  # dispara o set de primary
        with _patch_membership_lookup(membership):
            _make_view()._handle_reactivate_membership(_make_request())
        membership.mark_active.assert_called_once()
        membership.identity.save.assert_called_once()
        mock_audit.objects.create.assert_called_once()
        mock_messages.success.assert_called_once()


@patch('student_identity.staff_membership_actions.redirect', return_value=REDIRECT_SENTINEL)
@patch('student_identity.staff_membership_actions.messages')
@patch('student_identity.staff_membership_actions.AuditEvent')
class RevokeMembershipTest(unittest.TestCase):
    def test_denied_role_short_circuits(self, mock_audit, mock_messages, mock_redirect):
        result = _make_view(denied=True)._handle_revoke_membership(_make_request())
        self.assertEqual(result, DENIED_SENTINEL)

    def test_not_found_shows_error(self, mock_audit, mock_messages, mock_redirect):
        with _patch_membership_lookup(None):
            _make_view()._handle_revoke_membership(_make_request())
        mock_messages.error.assert_called_once()

    def test_already_revoked_shows_info(self, mock_audit, mock_messages, mock_redirect):
        membership = _make_membership(status=StudentBoxMembershipStatus.REVOKED)
        with _patch_membership_lookup(membership):
            _make_view()._handle_revoke_membership(_make_request())
        mock_messages.info.assert_called_once()

    def test_happy_path_revokes_with_default_reason(self, mock_audit, mock_messages, mock_redirect):
        membership = _make_membership(status=StudentBoxMembershipStatus.ACTIVE)
        with patch.object(
            type(_make_view()), '_find_fallback_active_membership', return_value=None
        ):
            with _patch_membership_lookup(membership):
                _make_view()._handle_revoke_membership(_make_request({'membership_id': '1'}))
        membership.mark_revoked.assert_called_once()
        mock_audit.objects.create.assert_called_once()
        mock_messages.success.assert_called_once()


class RealignIdentityTest(unittest.TestCase):
    """L1: _realign_identity_after_membership_loss com e sem fallback ativo."""

    def test_fallback_found_repoints_identity(self):
        view = _make_view()
        identity = MagicMock()
        affected = _make_membership()
        fallback = MagicMock(box_root_slug='academia-y')
        with patch.object(view, '_find_fallback_active_membership', return_value=fallback):
            view._realign_identity_after_membership_loss(identity=identity, affected_membership=affected)
        self.assertEqual(identity.primary_box_root_slug, 'academia-y')
        identity.save.assert_called_once()

    def test_no_fallback_leaves_identity_untouched(self):
        view = _make_view()
        identity = MagicMock()
        affected = _make_membership()
        with patch.object(view, '_find_fallback_active_membership', return_value=None):
            view._realign_identity_after_membership_loss(identity=identity, affected_membership=affected)
        identity.save.assert_not_called()


class UpdateStudentEmailInTenantTest(unittest.TestCase):
    """L1: _update_student_email_in_tenant — sem student_id, com schema, e erro silencioso."""

    def test_no_student_id_is_noop(self):
        from student_identity.staff_membership_actions import _update_student_email_in_tenant
        membership = MagicMock(student_id=None)
        # nao deve levantar
        _update_student_email_in_tenant(membership=membership, new_email='x@example.com')

    def test_error_is_swallowed(self):
        from student_identity.staff_membership_actions import _update_student_email_in_tenant
        membership = MagicMock(student_id=55, box_id=None)
        # students.models.Student.objects.filter levanta -> deve ser engolido (log)
        with patch('students.models.Student') as mock_student:
            mock_student.objects.filter.side_effect = RuntimeError('boom')
            _update_student_email_in_tenant(membership=membership, new_email='x@example.com')

    def test_with_schema_uses_schema_context(self):
        from student_identity.staff_membership_actions import _update_student_email_in_tenant
        membership = MagicMock(student_id=55, box_id=3)
        membership.box.schema_name = 'box_academia-x'
        with patch('students.models.Student') as mock_student, \
                patch('django_tenants.utils.schema_context') as mock_ctx:
            _update_student_email_in_tenant(membership=membership, new_email='x@example.com')
        # entrou no schema do box e atualizou o Student
        mock_ctx.assert_called_once_with('box_academia-x')
        mock_student.objects.filter.assert_called_once_with(pk=55)


if __name__ == '__main__':
    unittest.main()
