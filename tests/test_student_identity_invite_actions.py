"""
ARQUIVO: testes de student_identity.staff_invite_actions.

POR QUE EXISTE:
- StudentInvitationInviteActionsMixin separa o corredor de invites da view
  monolitica. O coverage report do PR #115 apontou staff_invite_actions.py
  com a branch de pausa de link (147-153) e outros caminhos sem cobertura.

CAMADA: L1 (unit). Sem banco e sem tenant real: a view e instanciada solta
e request/use-cases/AuditEvent sao mockados, espelhando o harness ja
estabelecido em tests/test_student_identity_staff_views.py.

SOURCE-UNDER-TEST:
- student_identity/staff_invite_actions.py
  (StudentInvitationInviteActionsMixin._handle_create_invite /
   _handle_create_box_link / _handle_pause_box_link)

CONTRATO DE MOCK:
- CreateStudentInvitation / CreateStudentBoxInviteLink: mockados para devolver
  um result com success/failure_reason/invitation controlados.
- AuditEvent.objects.create / record_student_onboarding_event / messages /
  redirect / reverse / StudentBoxInviteLink.objects: mockados no namespace
  do modulo.
- StudentInvitationCreateForm: mockado para controlar is_valid()/cleaned_data.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch


REDIRECT_SENTINEL = 'REDIRECT::student-invitation-operations'
RENDER_SENTINEL = 'RENDER::form'


class _InviteView:
    """View minima: injeta o mixin + os stubs que ele espera da view real."""

    def __init__(self):
        from student_identity.staff_invite_actions import (
            StudentInvitationInviteActionsMixin,
        )

        class _V(StudentInvitationInviteActionsMixin):
            def _get_actor_role_slug(self, request):
                return 'manager'

            def _track_invite_creation_anomalies(self, request, *, invitation):
                # comportamento coberto em test_student_identity_staff_views.py
                self.tracked = invitation

            def _map_failure_reason(self, reason):
                return f'erro:{reason}'

            def get_context_data(self, **kwargs):
                return kwargs

            def render_to_response(self, context):
                self.rendered_context = context
                return RENDER_SENTINEL

        return_view = _V()
        self._view = return_view

    def get(self):
        return self._view


def _make_request():
    request = MagicMock()
    request.user = MagicMock()
    request.user.id = 7
    request.POST = {}
    request.build_absolute_uri.side_effect = lambda path: f'https://box.local{path}'
    return request


def _make_invitation():
    invitation = MagicMock()
    invitation.id = 123
    invitation.token = 'tok-abc'
    invitation.student_id = 55
    invitation.student_name = 'Aluno Teste'
    invitation.invite_type = 'individual'
    invitation.invited_email = ''
    invitation.onboarding_journey = 'registered_student_invite'
    invitation.box_root_slug = 'academia-x'
    return invitation


@patch('student_identity.staff_invite_actions.reverse', return_value='/invite/tok-abc/')
@patch('student_identity.staff_invite_actions.redirect', return_value=REDIRECT_SENTINEL)
@patch('student_identity.staff_invite_actions.messages')
@patch('student_identity.staff_invite_actions.record_student_onboarding_event')
@patch('student_identity.staff_invite_actions.AuditEvent')
@patch('student_identity.staff_invite_actions.get_box_runtime_slug', return_value='academia-x')
@patch('student_identity.staff_invite_actions.CreateStudentInvitation')
@patch('student_identity.staff_invite_actions.DjangoStudentIdentityRepository')
@patch('student_identity.staff_invite_actions.StudentInvitationCreateForm')
class HandleCreateInviteTest(unittest.TestCase):
    """L1: _handle_create_invite — form invalido, sucesso, rate-limit, falha generica."""

    def _form_valid(self, mock_form):
        student = MagicMock(id=55, full_name='Aluno Teste')
        form = MagicMock()
        form.is_valid.return_value = True
        form.cleaned_data = {
            'student': student,
            'invite_type': 'individual',
            'onboarding_journey': 'registered_student_invite',
            'expires_in_days': 7,
        }
        mock_form.return_value = form
        return form

    def test_invalid_form_rerenders(
        self, mock_form, _repo, mock_uc, _slug, mock_audit, mock_event, mock_messages, mock_redirect, _reverse
    ):
        form = MagicMock()
        form.is_valid.return_value = False
        mock_form.return_value = form

        result = _InviteView().get()._handle_create_invite(_make_request())
        self.assertEqual(result, RENDER_SENTINEL)
        mock_uc.assert_not_called()

    def test_success_audits_and_redirects(
        self, mock_form, _repo, mock_uc, _slug, mock_audit, mock_event, mock_messages, mock_redirect, _reverse
    ):
        self._form_valid(mock_form)
        invitation = _make_invitation()
        mock_uc.return_value.execute.return_value = MagicMock(
            success=True, invitation=invitation, failure_reason=None
        )

        result = _InviteView().get()._handle_create_invite(_make_request())
        mock_audit.objects.create.assert_called_once()
        mock_event.assert_called_once()
        mock_messages.success.assert_called_once()
        self.assertEqual(result, REDIRECT_SENTINEL)

    def test_rate_limit_failure_audits_block_and_rerenders(
        self, mock_form, _repo, mock_uc, _slug, mock_audit, mock_event, mock_messages, mock_redirect, _reverse
    ):
        self._form_valid(mock_form)
        mock_uc.return_value.execute.return_value = MagicMock(
            success=False, invitation=None, failure_reason='open-box-rate-limit-exceeded'
        )

        result = _InviteView().get()._handle_create_invite(_make_request())
        # registra AuditEvent de bloqueio + mostra erro mapeado + re-renderiza
        mock_audit.objects.create.assert_called_once()
        mock_messages.error.assert_called_once()
        self.assertEqual(result, RENDER_SENTINEL)

    def test_generic_failure_rerenders_without_block_audit(
        self, mock_form, _repo, mock_uc, _slug, mock_audit, mock_event, mock_messages, mock_redirect, _reverse
    ):
        self._form_valid(mock_form)
        mock_uc.return_value.execute.return_value = MagicMock(
            success=False, invitation=None, failure_reason='student-not-found'
        )

        result = _InviteView().get()._handle_create_invite(_make_request())
        mock_audit.objects.create.assert_not_called()
        mock_messages.error.assert_called_once()
        self.assertEqual(result, RENDER_SENTINEL)


@patch('student_identity.staff_invite_actions.reverse', return_value='/box-invite/tok-xyz/')
@patch('student_identity.staff_invite_actions.redirect', return_value=REDIRECT_SENTINEL)
@patch('student_identity.staff_invite_actions.messages')
@patch('student_identity.staff_invite_actions.record_student_onboarding_event')
@patch('student_identity.staff_invite_actions.get_box_runtime_slug', return_value='academia-x')
@patch('student_identity.staff_invite_actions.CreateStudentBoxInviteLink')
@patch('student_identity.staff_invite_actions.DjangoStudentIdentityRepository')
class HandleCreateBoxLinkTest(unittest.TestCase):
    """L1: _handle_create_box_link — cria/renova link e registra evento."""

    def test_creates_link_records_event_and_redirects(
        self, _repo, mock_uc, _slug, mock_event, mock_messages, mock_redirect, _reverse
    ):
        mock_uc.return_value.execute.return_value = MagicMock(
            id=9, token='tok-xyz', max_uses=200
        )

        result = _InviteView().get()._handle_create_box_link(_make_request())
        mock_messages.success.assert_called_once()
        mock_event.assert_called_once()
        event_kwargs = mock_event.call_args.kwargs
        self.assertEqual(event_kwargs['event'], 'link_created')
        self.assertEqual(result, REDIRECT_SENTINEL)


@patch('student_identity.staff_invite_actions.redirect', return_value=REDIRECT_SENTINEL)
@patch('student_identity.staff_invite_actions.messages')
@patch('student_identity.staff_invite_actions.timezone')
@patch('student_identity.staff_invite_actions.get_box_runtime_slug', return_value='academia-x')
@patch('student_identity.staff_invite_actions.StudentBoxInviteLink')
class HandlePauseBoxLinkTest(unittest.TestCase):
    """L1: _handle_pause_box_link — link nao encontrado vs pausa com sucesso."""

    def _lookup_returns(self, mock_model, link):
        mock_model.objects.filter.return_value.first.return_value = link

    def test_link_not_found_shows_error(
        self, mock_model, _slug, _tz, mock_messages, mock_redirect
    ):
        self._lookup_returns(mock_model, None)
        result = _InviteView().get()._handle_pause_box_link(_make_request())
        mock_messages.error.assert_called_once()
        self.assertEqual(result, REDIRECT_SENTINEL)

    def test_pauses_link_and_saves(
        self, mock_model, _slug, _tz, mock_messages, mock_redirect
    ):
        link = MagicMock()
        self._lookup_returns(mock_model, link)

        result = _InviteView().get()._handle_pause_box_link(_make_request())
        # marca paused_at e salva os campos esperados
        link.save.assert_called_once()
        save_kwargs = link.save.call_args.kwargs
        self.assertIn('paused_at', save_kwargs['update_fields'])
        mock_messages.success.assert_called_once()
        self.assertEqual(result, REDIRECT_SENTINEL)


if __name__ == '__main__':
    unittest.main()
