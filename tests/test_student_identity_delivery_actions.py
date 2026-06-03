"""
ARQUIVO: testes de student_identity.staff_delivery_actions.

POR QUE EXISTE:
- StudentInvitationDeliveryActionsMixin separa o corredor de entrega de
  e-mail e WhatsApp da view monolitica. As guard clauses (convite nao
  encontrado, ja aceito, expirado, sem e-mail, sem telefone) e o caminho
  feliz de handoff nunca foram cobertos — o coverage report do PR #115
  apontou staff_delivery_actions.py em 60% (linhas 36-86 sem cobertura).

CAMADA: L1 (unit). Sem banco e sem tenant real: a view e instanciada
solta e request/invitation sao MagicMock, espelhando o harness ja
estabelecido em tests/test_student_identity_staff_views.py.

SOURCE-UNDER-TEST:
- student_identity/staff_delivery_actions.py
  (StudentInvitationDeliveryActionsMixin._handle_send_email / _handle_open_whatsapp)

CONTRATO DE MOCK:
- StudentAppInvitation.objects: mockado para retornar o invitation de teste
  (ou None) sem tocar o banco.
- messages / redirect / reverse: mockados no namespace do modulo.
- send_invitation_email / build_invitation_whatsapp_url /
  record_student_invitation_whatsapp_handoff / record_student_onboarding_event:
  mockados para validar invocacao sem efeitos colaterais.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from student_identity.staff_delivery_actions import (
    StudentInvitationDeliveryActionsMixin,
)
from student_identity.delivery_gateways import StudentEmailDeliveryError


REDIRECT_SENTINEL = 'REDIRECT::student-invitation-operations'
WHATSAPP_REDIRECT_SENTINEL = 'REDIRECT::whatsapp'


class _DeliveryView(StudentInvitationDeliveryActionsMixin):
    """View minima que expoe o mixin sem o resto da hierarquia Django."""

    def _get_actor_role_slug(self, request):  # noqa: D401 - stub de teste
        return 'manager'


def _make_request():
    request = MagicMock()
    request.user = MagicMock()
    request.user.id = 7
    request.POST = {'invitation_id': '123'}
    request.build_absolute_uri.side_effect = lambda path: f'https://box.local{path}'
    return request


def _make_invitation(**overrides):
    invitation = MagicMock()
    invitation.pk = 123
    invitation.id = 123
    invitation.token = 'tok-abc'
    invitation.accepted_at = None
    invitation.is_expired = False
    invitation.invited_email = 'aluno@example.com'
    invitation.onboarding_journey = 'registered_student_invite'
    invitation.student_id = 55
    invitation.student_name = 'Aluno Teste'
    invitation.box_root_slug = 'academia-x'
    for key, value in overrides.items():
        setattr(invitation, key, value)
    return invitation


def _patch_invitation_lookup(invitation):
    """Faz StudentAppInvitation.objects.all().filter(...).first() -> invitation."""
    chain = MagicMock()
    chain.filter.return_value.first.return_value = invitation
    return patch(
        'student_identity.staff_delivery_actions.StudentAppInvitation.objects.all',
        return_value=chain,
    )


@patch('student_identity.staff_delivery_actions.reverse', return_value='/invite/tok-abc/')
@patch('student_identity.staff_delivery_actions.redirect')
@patch('student_identity.staff_delivery_actions.messages')
@patch('student_identity.staff_delivery_actions.get_box_runtime_slug', return_value='academia-x')
class HandleSendEmailTest(unittest.TestCase):
    """L1: _handle_send_email — todas as guard clauses + caminho feliz."""

    def test_invitation_not_found_shows_error(self, _slug, mock_messages, mock_redirect, _reverse):
        mock_redirect.return_value = REDIRECT_SENTINEL
        with _patch_invitation_lookup(None):
            result = _DeliveryView()._handle_send_email(_make_request())
        mock_messages.error.assert_called_once()
        mock_redirect.assert_called_once_with('student-invitation-operations')
        self.assertEqual(result, REDIRECT_SENTINEL)

    def test_already_accepted_shows_info(self, _slug, mock_messages, mock_redirect, _reverse):
        invitation = _make_invitation(accepted_at='2026-01-01T00:00:00Z')
        with _patch_invitation_lookup(invitation):
            _DeliveryView()._handle_send_email(_make_request())
        mock_messages.info.assert_called_once()
        mock_messages.success.assert_not_called()

    def test_expired_shows_error(self, _slug, mock_messages, mock_redirect, _reverse):
        invitation = _make_invitation(is_expired=True)
        with _patch_invitation_lookup(invitation):
            _DeliveryView()._handle_send_email(_make_request())
        mock_messages.error.assert_called_once()

    def test_missing_email_shows_error(self, _slug, mock_messages, mock_redirect, _reverse):
        invitation = _make_invitation(invited_email='')
        with _patch_invitation_lookup(invitation):
            _DeliveryView()._handle_send_email(_make_request())
        mock_messages.error.assert_called_once()

    @patch('student_identity.staff_delivery_actions.send_invitation_email')
    def test_delivery_error_shows_error(
        self, mock_send, _slug, mock_messages, mock_redirect, _reverse
    ):
        mock_send.side_effect = StudentEmailDeliveryError('falhou')
        invitation = _make_invitation()
        with _patch_invitation_lookup(invitation):
            _DeliveryView()._handle_send_email(_make_request())
        mock_send.assert_called_once()
        mock_messages.error.assert_called_once()
        mock_messages.success.assert_not_called()

    @patch('student_identity.staff_delivery_actions.send_invitation_email')
    def test_happy_path_sends_and_reports_success(
        self, mock_send, _slug, mock_messages, mock_redirect, _reverse
    ):
        mock_send.return_value = MagicMock(provider='resend')
        invitation = _make_invitation()
        with _patch_invitation_lookup(invitation):
            _DeliveryView()._handle_send_email(_make_request())
        mock_send.assert_called_once()
        mock_messages.success.assert_called_once()
        # mensagem de sucesso menciona destino e provider
        success_text = mock_messages.success.call_args.args[1]
        self.assertIn('aluno@example.com', success_text)
        self.assertIn('resend', success_text)


@patch('student_identity.staff_delivery_actions.record_student_onboarding_event')
@patch('student_identity.staff_delivery_actions.record_student_invitation_whatsapp_handoff')
@patch('student_identity.staff_delivery_actions.build_invitation_whatsapp_url')
@patch('student_identity.staff_delivery_actions.reverse', return_value='/invite/tok-abc/')
@patch('student_identity.staff_delivery_actions.redirect')
@patch('student_identity.staff_delivery_actions.messages')
@patch('student_identity.staff_delivery_actions.get_box_runtime_slug', return_value='academia-x')
class HandleOpenWhatsAppTest(unittest.TestCase):
    """L1: _handle_open_whatsapp — guard clauses + caminho feliz com auditoria."""

    def test_invitation_not_found_shows_error(
        self, _slug, mock_messages, mock_redirect, _reverse, mock_build, mock_handoff, mock_event
    ):
        with _patch_invitation_lookup(None):
            _DeliveryView()._handle_open_whatsapp(_make_request())
        mock_messages.error.assert_called_once()
        mock_build.assert_not_called()

    def test_already_accepted_shows_info(
        self, _slug, mock_messages, mock_redirect, _reverse, mock_build, mock_handoff, mock_event
    ):
        invitation = _make_invitation(accepted_at='2026-01-01T00:00:00Z')
        with _patch_invitation_lookup(invitation):
            _DeliveryView()._handle_open_whatsapp(_make_request())
        mock_messages.info.assert_called_once()
        mock_handoff.assert_not_called()

    def test_expired_shows_error(
        self, _slug, mock_messages, mock_redirect, _reverse, mock_build, mock_handoff, mock_event
    ):
        invitation = _make_invitation(is_expired=True)
        with _patch_invitation_lookup(invitation):
            _DeliveryView()._handle_open_whatsapp(_make_request())
        mock_messages.error.assert_called_once()
        mock_handoff.assert_not_called()

    def test_missing_phone_shows_error(
        self, _slug, mock_messages, mock_redirect, _reverse, mock_build, mock_handoff, mock_event
    ):
        mock_build.return_value = ''  # sem telefone valido
        invitation = _make_invitation()
        with _patch_invitation_lookup(invitation):
            _DeliveryView()._handle_open_whatsapp(_make_request())
        mock_messages.error.assert_called_once()
        mock_handoff.assert_not_called()

    @patch(
        'student_identity.notifications._get_invitation_student_phone',
        return_value='+5511999999999',
    )
    def test_happy_path_records_handoff_and_event_then_redirects(
        self, _phone, _slug, mock_messages, mock_redirect, _reverse, mock_build, mock_handoff, mock_event
    ):
        mock_build.return_value = 'https://wa.me/5511999999999'
        mock_redirect.return_value = WHATSAPP_REDIRECT_SENTINEL
        invitation = _make_invitation()
        with _patch_invitation_lookup(invitation):
            result = _DeliveryView()._handle_open_whatsapp(_make_request())

        mock_handoff.assert_called_once()
        mock_event.assert_called_once()
        # redireciona para a URL do WhatsApp construida
        mock_redirect.assert_called_once_with('https://wa.me/5511999999999')
        self.assertEqual(result, WHATSAPP_REDIRECT_SENTINEL)
        # evento de onboarding carrega o journey e o id do convite
        event_kwargs = mock_event.call_args.kwargs
        self.assertEqual(event_kwargs['event'], 'whatsapp_handoff_opened')
        self.assertEqual(event_kwargs['journey'], 'registered_student_invite')


if __name__ == '__main__':
    unittest.main()
