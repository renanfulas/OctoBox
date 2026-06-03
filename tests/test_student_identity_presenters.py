"""
ARQUIVO: testes de student_identity.presenters.

POR QUE EXISTE:
- StudentInvitationOperationsPresenter centraliza labels, tons e snapshots
  prontos para a tela operacional. O coverage report do PR #115 apontou
  presenters.py em ~61% — a maioria dos ramos de status/tom sem cobertura.

CAMADA: L1 (unit). Presenter e logica pura: sem banco, sem tenant. Usa o enum
real (StudentInvitationDeliveryStatus / StudentBoxMembershipStatus /
StudentOnboardingJourney) e objetos simples (SimpleNamespace / MagicMock).

SOURCE-UNDER-TEST:
- student_identity/presenters.py (StudentInvitationOperationsPresenter)

CONTRATO DE MOCK:
- request: MagicMock (build_absolute_uri previsivel).
- reverse: mockado no namespace do modulo para nao depender de URLconf.
"""

from __future__ import annotations

import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from student_identity.models import (
    StudentBoxMembershipStatus,
    StudentInvitationDeliveryStatus,
    StudentOnboardingJourney,
)
from student_identity.presenters import StudentInvitationOperationsPresenter


D = StudentInvitationDeliveryStatus
M = StudentBoxMembershipStatus
J = StudentOnboardingJourney
SENT_AT = datetime(2026, 1, 2, 15, 30)


def _presenter(*, can_view_invite_links=True, can_operate_invites=True):
    request = MagicMock()
    request.build_absolute_uri.side_effect = lambda path: f'https://box.local{path}'
    return StudentInvitationOperationsPresenter(
        request=request,
        access_matrix={
            'can_view_invite_links': can_view_invite_links,
            'can_operate_invites': can_operate_invites,
        },
    )


def _invitation(*, accepted_at=None, is_expired=False, invited_email='a@e.com'):
    return SimpleNamespace(accepted_at=accepted_at, is_expired=is_expired, invited_email=invited_email)


def _delivery(status, *, sent_at=SENT_AT, failed_at=SENT_AT, provider='resend'):
    return SimpleNamespace(status=status, sent_at=sent_at, failed_at=failed_at, provider=provider)


class MembershipAndInvitationToneTest(unittest.TestCase):
    def test_membership_status_tone_all_branches(self):
        p = _presenter()
        self.assertEqual(p.build_membership_status_tone(M.ACTIVE), 'ok')
        self.assertEqual(p.build_membership_status_tone(M.PENDING_APPROVAL), 'attention')
        self.assertEqual(p.build_membership_status_tone(M.SUSPENDED_FINANCIAL), 'danger')
        self.assertEqual(p.build_membership_status_tone(M.REVOKED), 'danger')
        self.assertEqual(p.build_membership_status_tone(M.INACTIVE), 'muted')

    def test_status_label_and_tone(self):
        p = _presenter()
        self.assertEqual(p.build_status_label(_invitation(accepted_at=SENT_AT)), 'Aceito')
        self.assertEqual(p.build_status_label(_invitation(is_expired=True)), 'Expirado')
        self.assertEqual(p.build_status_label(_invitation()), 'Pendente')
        self.assertEqual(p.build_status_tone(_invitation(accepted_at=SENT_AT)), 'ok')
        self.assertEqual(p.build_status_tone(_invitation(is_expired=True)), 'muted')
        self.assertEqual(p.build_status_tone(_invitation()), 'attention')


class BoxInviteLinkTest(unittest.TestCase):
    def _link(self, **kw):
        defaults = dict(
            id=1, token='tok', use_count=3, max_uses=200, expires_at=SENT_AT,
            is_revoked=False, is_paused=False, is_expired=False, is_exhausted=False,
            can_accept=True, can_operate=True,
        )
        defaults.update(kw)
        return SimpleNamespace(**defaults)

    def test_status_label_all_branches(self):
        p = _presenter()
        self.assertEqual(p.build_box_invite_link_status_label(self._link(is_revoked=True)), 'Revogado')
        self.assertEqual(p.build_box_invite_link_status_label(self._link(is_paused=True)), 'Pausado')
        self.assertEqual(p.build_box_invite_link_status_label(self._link(is_expired=True)), 'Expirado')
        self.assertEqual(p.build_box_invite_link_status_label(self._link(is_exhausted=True)), 'Limite atingido')
        self.assertEqual(p.build_box_invite_link_status_label(self._link()), 'Disponivel')

    def test_status_tone_all_branches(self):
        p = _presenter()
        self.assertEqual(p.build_box_invite_link_status_tone(self._link(can_accept=True)), 'ok')
        self.assertEqual(p.build_box_invite_link_status_tone(self._link(can_accept=False, is_paused=True)), 'attention')
        self.assertEqual(p.build_box_invite_link_status_tone(self._link(can_accept=False, is_paused=False)), 'muted')

    def test_active_payload_none_returns_none(self):
        self.assertIsNone(_presenter().build_active_box_invite_link_payload(active_box_invite_link=None))

    @patch('student_identity.presenters.reverse', return_value='/box-invite/tok/')
    def test_active_payload_with_view_permission_builds_url(self, _reverse):
        p = _presenter(can_view_invite_links=True)
        payload = p.build_active_box_invite_link_payload(active_box_invite_link=self._link())
        self.assertEqual(payload['invite_url'], 'https://box.local/box-invite/tok/')
        self.assertEqual(payload['status_label'], 'Disponivel')

    @patch('student_identity.presenters.reverse', return_value='/box-invite/tok/')
    def test_active_payload_without_view_permission_blanks_url(self, _reverse):
        p = _presenter(can_view_invite_links=False)
        payload = p.build_active_box_invite_link_payload(active_box_invite_link=self._link())
        self.assertEqual(payload['invite_url'], '')


class EmailDeliveryTest(unittest.TestCase):
    def test_label_all_branches(self):
        p = _presenter()
        self.assertIn('Nenhum envio', p.build_last_email_delivery_label(None))
        self.assertIn('enviado', p.build_last_email_delivery_label(_delivery(D.SENT)))
        self.assertIn('entregue', p.build_last_email_delivery_label(_delivery(D.DELIVERED)))
        self.assertIn('falha', p.build_last_email_delivery_label(_delivery(D.BOUNCED)))
        self.assertIn('atrasado', p.build_last_email_delivery_label(_delivery(D.DELAYED)))
        # status fora dos ramos -> fallback "Ultimo status"
        self.assertIn('Ultimo status', p.build_last_email_delivery_label(_delivery('weird')))

    def test_status_label_mapping_and_fallback(self):
        p = _presenter()
        self.assertEqual(p.build_last_email_delivery_status_label(None), 'Sem envio')
        self.assertEqual(p.build_last_email_delivery_status_label(_delivery(D.COMPLAINED)), 'Complaint')
        self.assertEqual(p.build_last_email_delivery_status_label(_delivery('weird')), 'weird')

    def test_status_tone_all_branches(self):
        p = _presenter()
        self.assertEqual(p.build_last_email_delivery_status_tone(None), 'muted')
        self.assertEqual(p.build_last_email_delivery_status_tone(_delivery(D.DELIVERED)), 'ok')
        self.assertEqual(p.build_last_email_delivery_status_tone(_delivery(D.BOUNCED)), 'danger')
        self.assertEqual(p.build_last_email_delivery_status_tone(_delivery(D.SENT)), 'attention')
        self.assertEqual(p.build_last_email_delivery_status_tone(_delivery('weird')), 'muted')


class WhatsAppDeliveryTest(unittest.TestCase):
    def test_label_and_status_and_tone(self):
        p = _presenter()
        self.assertIn('Nenhum envio', p.build_last_whatsapp_delivery_label(None))
        self.assertIn('aberta', p.build_last_whatsapp_delivery_label(_delivery(D.SENT)))
        self.assertIn('Ultimo status', p.build_last_whatsapp_delivery_label(_delivery(D.FAILED)))
        self.assertEqual(p.build_last_whatsapp_delivery_status_label(None), 'Sem mensagem')
        self.assertEqual(p.build_last_whatsapp_delivery_status_label(_delivery(D.SENT)), 'Mensagem aberta')
        self.assertEqual(p.build_last_whatsapp_delivery_status_label(_delivery(D.FAILED)), D.FAILED)
        self.assertEqual(p.build_last_whatsapp_delivery_status_tone(None), 'muted')
        self.assertEqual(p.build_last_whatsapp_delivery_status_tone(_delivery(D.SENT)), 'ok')
        self.assertEqual(p.build_last_whatsapp_delivery_status_tone(_delivery(D.FAILED)), 'attention')


class StalledInvitationTest(unittest.TestCase):
    def test_is_stalled_branches(self):
        p = _presenter()
        # aceito/expirado -> nao travado
        self.assertFalse(p.is_stalled_invitation(invitation=_invitation(accepted_at=SENT_AT), email_delivery=None, whatsapp_delivery=None))
        # whatsapp enviado -> nao travado
        self.assertFalse(p.is_stalled_invitation(invitation=_invitation(), email_delivery=_delivery(D.BOUNCED), whatsapp_delivery=_delivery(D.SENT)))
        # sem email delivery -> nao travado
        self.assertFalse(p.is_stalled_invitation(invitation=_invitation(), email_delivery=None, whatsapp_delivery=None))
        # email bounced e sem whatsapp -> travado
        self.assertTrue(p.is_stalled_invitation(invitation=_invitation(), email_delivery=_delivery(D.BOUNCED), whatsapp_delivery=None))
        # email entregue -> nao travado
        self.assertFalse(p.is_stalled_invitation(invitation=_invitation(), email_delivery=_delivery(D.DELIVERED), whatsapp_delivery=None))

    def test_stalled_reason_label(self):
        p = _presenter()
        self.assertIn('Sem handoff', p.build_stalled_reason_label(None))
        self.assertIn('devolvido', p.build_stalled_reason_label(_delivery(D.BOUNCED)))
        self.assertIn('reclamou', p.build_stalled_reason_label(_delivery(D.COMPLAINED)))
        self.assertIn('bloqueado', p.build_stalled_reason_label(_delivery(D.SUPPRESSED)))
        self.assertIn('Falta enviar', p.build_stalled_reason_label(_delivery(D.SENT)))

    def test_stalled_priority_rank_label_tone(self):
        p = _presenter()
        self.assertEqual(p.build_stalled_priority_rank(None), 99)
        self.assertEqual(p.build_stalled_priority_rank(_delivery(D.COMPLAINED)), 0)
        self.assertEqual(p.build_stalled_priority_rank(_delivery(D.BOUNCED)), 1)
        self.assertEqual(p.build_stalled_priority_rank(_delivery(D.SUPPRESSED)), 2)
        self.assertEqual(p.build_stalled_priority_rank(_delivery(D.SENT)), 99)

        self.assertEqual(p.build_stalled_priority_label(None), 'Fila')
        self.assertEqual(p.build_stalled_priority_label(_delivery(D.COMPLAINED)), 'Prioridade maxima')
        self.assertEqual(p.build_stalled_priority_label(_delivery(D.BOUNCED)), 'Prioridade alta')
        self.assertEqual(p.build_stalled_priority_label(_delivery(D.SENT)), 'Fila')

        self.assertEqual(p.build_stalled_priority_tone(None), 'muted')
        self.assertEqual(p.build_stalled_priority_tone(_delivery(D.COMPLAINED)), 'danger')
        self.assertEqual(p.build_stalled_priority_tone(_delivery(D.BOUNCED)), 'attention')
        self.assertEqual(p.build_stalled_priority_tone(_delivery(D.SENT)), 'muted')

    def test_stalled_since_label(self):
        p = _presenter()
        self.assertEqual(p.build_stalled_since_label(None), '')
        self.assertIn('Travado desde', p.build_stalled_since_label(SENT_AT))


class CanSendEmailTest(unittest.TestCase):
    def test_branches(self):
        p = _presenter()
        self.assertFalse(p.can_send_email(invitation=_invitation(invited_email=''), delivery=None))
        self.assertFalse(p.can_send_email(invitation=_invitation(is_expired=True), delivery=None))
        self.assertFalse(p.can_send_email(invitation=_invitation(accepted_at=SENT_AT), delivery=None))
        self.assertTrue(p.can_send_email(invitation=_invitation(), delivery=None))
        self.assertTrue(p.can_send_email(invitation=_invitation(), delivery=_delivery(D.SENT)))
        self.assertFalse(p.can_send_email(invitation=_invitation(), delivery=_delivery(D.BOUNCED)))


class EmailActionRecommendationTest(unittest.TestCase):
    def test_label_all_branches(self):
        p = _presenter()
        self.assertIn('concluido', p.build_email_action_recommendation_label(invitation=_invitation(accepted_at=SENT_AT), delivery=None))
        self.assertIn('novo convite', p.build_email_action_recommendation_label(invitation=_invitation(is_expired=True), delivery=None))
        self.assertIn('WhatsApp', p.build_email_action_recommendation_label(invitation=_invitation(invited_email=''), delivery=None))
        self.assertIn('acelerar', p.build_email_action_recommendation_label(invitation=_invitation(), delivery=None))
        self.assertIn('entregue', p.build_email_action_recommendation_label(invitation=_invitation(), delivery=_delivery(D.DELIVERED)))
        self.assertIn('atrasado', p.build_email_action_recommendation_label(invitation=_invitation(), delivery=_delivery(D.DELAYED)))
        self.assertIn('Bounce', p.build_email_action_recommendation_label(invitation=_invitation(), delivery=_delivery(D.BOUNCED)))
        self.assertIn('Complaint', p.build_email_action_recommendation_label(invitation=_invitation(), delivery=_delivery(D.COMPLAINED)))
        self.assertIn('suprimido', p.build_email_action_recommendation_label(invitation=_invitation(), delivery=_delivery(D.SUPPRESSED)))
        self.assertIn('Falha', p.build_email_action_recommendation_label(invitation=_invitation(), delivery=_delivery(D.FAILED)))
        self.assertIn('rota', p.build_email_action_recommendation_label(invitation=_invitation(), delivery=_delivery(D.SENT)))
        self.assertIn('Revise', p.build_email_action_recommendation_label(invitation=_invitation(), delivery=_delivery('weird')))

    def test_tone_all_branches(self):
        p = _presenter()
        self.assertEqual(p.build_email_action_recommendation_tone(invitation=_invitation(accepted_at=SENT_AT), delivery=None), 'ok')
        self.assertEqual(p.build_email_action_recommendation_tone(invitation=_invitation(is_expired=True), delivery=None), 'danger')
        self.assertEqual(p.build_email_action_recommendation_tone(invitation=_invitation(invited_email=''), delivery=None), 'danger')
        self.assertEqual(p.build_email_action_recommendation_tone(invitation=_invitation(), delivery=None), 'muted')
        self.assertEqual(p.build_email_action_recommendation_tone(invitation=_invitation(), delivery=_delivery(D.DELIVERED)), 'ok')
        self.assertEqual(p.build_email_action_recommendation_tone(invitation=_invitation(), delivery=_delivery(D.BOUNCED)), 'danger')
        self.assertEqual(p.build_email_action_recommendation_tone(invitation=_invitation(), delivery=_delivery(D.SENT)), 'attention')
        self.assertEqual(p.build_email_action_recommendation_tone(invitation=_invitation(), delivery=_delivery('weird')), 'muted')


class EmptyJourneyCopyTest(unittest.TestCase):
    def test_mapping_and_fallback(self):
        p = _presenter()
        self.assertIn('link em massa', p.build_empty_journey_copy(journey=J.MASS_BOX_INVITE))
        self.assertIn('recepcao', p.build_empty_journey_copy(journey=J.IMPORTED_LEAD_INVITE))
        self.assertIn('ja cadastrados', p.build_empty_journey_copy(journey=J.REGISTERED_STUDENT_INVITE))
        self.assertIn('volume', p.build_empty_journey_copy(journey='desconhecido'))


if __name__ == '__main__':
    unittest.main()
