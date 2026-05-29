"""
ARQUIVO: testes de student_identity.staff_views e oauth_actions.

POR QUE EXISTE:
- StudentInvitationOperationsView._track_invite_creation_anomalies aplica
  rate limit + anomaly alert. Sem teste: convites em massa passam silenciosos.
- finalize_student_oauth_callback é o ponto de saída do OAuth de aluno.
  Fluxos especiais (reativação, transferência), redirects e cookies
  nunca foram testados.
- Cobre Sprint 8 do plano de hardening.

CAMADA: L1 (unit) para _track_invite_creation_anomalies (mock de rate_limit
e alert). L1 para branches de finalize_student_oauth_callback (mock de
repository, messages, redirect).

SOURCE-UNDER-TEST:
- student_identity/staff_views.py:53 (_track_invite_creation_anomalies)
- student_identity/oauth_actions.py:68 (finalize_student_oauth_callback)

CONTRATO DE MOCK:
- check_student_flow_rate_limit + maybe_emit_student_anomaly_alert:
  mockados via unittest.mock.patch para validar invocação.
- request.user: MagicMock com .id (não precisa criar User real).
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, override_settings


# ===========================================================================
# StudentInvitationOperationsView._track_invite_creation_anomalies
# ===========================================================================

class TrackInviteCreationAnomaliesTest(unittest.TestCase):
    """L1: _track_invite_creation_anomalies — staff_views.py:53.

    Branches:
    - Actor rate limit OK + Box rate limit OK → nenhum alert
    - Actor rate limit EXCEDIDO → emit alert por ator
    - Box rate limit EXCEDIDO → emit alert por box
    - Ambos excedidos → 2 alerts
    """

    def _make_view(self):
        """Cria instância da view sem invocar setup completo do Django."""
        from student_identity.staff_views import StudentInvitationOperationsView
        view = StudentInvitationOperationsView()
        return view

    def _make_request(self, user_id: int = 42):
        request = MagicMock()
        request.user = MagicMock()
        request.user.id = user_id
        return request

    def _make_invitation(self, box_slug: str = 'academia-x', student_id: int = 1):
        invitation = MagicMock()
        invitation.box_root_slug = box_slug
        invitation.invite_type = 'individual'
        invitation.student_id = student_id
        return invitation

    @patch('student_identity.staff_views.maybe_emit_student_anomaly_alert')
    @patch('student_identity.staff_views.check_student_flow_rate_limit')
    @patch('student_identity.staff_views.get_student_operations_actor_role_slug')
    def test_no_alert_when_both_rate_limits_ok(self, mock_role, mock_rate, mock_alert):
        mock_role.return_value = 'manager'
        # Tupla (allowed, info) — allowed=True significa abaixo do limite
        mock_rate.return_value = (True, {})

        view = self._make_view()
        view._track_invite_creation_anomalies(
            self._make_request(), invitation=self._make_invitation()
        )

        # Rate limit verificado 2 vezes (actor + box)
        self.assertEqual(mock_rate.call_count, 2)
        # Nenhum alert emitido
        mock_alert.assert_not_called()

    @patch('student_identity.staff_views.maybe_emit_student_anomaly_alert')
    @patch('student_identity.staff_views.check_student_flow_rate_limit')
    @patch('student_identity.staff_views.get_student_operations_actor_role_slug')
    def test_actor_alert_emitted_when_actor_rate_limit_exceeded(
        self, mock_role, mock_rate, mock_alert
    ):
        mock_role.return_value = 'manager'
        # Primeiro call (actor) excede; segundo (box) está OK
        mock_rate.side_effect = [(False, {}), (True, {})]

        view = self._make_view()
        view._track_invite_creation_anomalies(
            self._make_request(user_id=99), invitation=self._make_invitation()
        )

        # 1 alert emitido (por ator)
        self.assertEqual(mock_alert.call_count, 1)
        call_kwargs = mock_alert.call_args.kwargs
        self.assertEqual(call_kwargs['scope'], 'student-invite-creation-actor')
        self.assertEqual(call_kwargs['target_label'], '99')

    @patch('student_identity.staff_views.maybe_emit_student_anomaly_alert')
    @patch('student_identity.staff_views.check_student_flow_rate_limit')
    @patch('student_identity.staff_views.get_student_operations_actor_role_slug')
    def test_box_alert_emitted_when_box_rate_limit_exceeded(
        self, mock_role, mock_rate, mock_alert
    ):
        mock_role.return_value = 'manager'
        # Actor OK, Box excede
        mock_rate.side_effect = [(True, {}), (False, {})]

        view = self._make_view()
        view._track_invite_creation_anomalies(
            self._make_request(), invitation=self._make_invitation(box_slug='academia-y')
        )

        self.assertEqual(mock_alert.call_count, 1)
        call_kwargs = mock_alert.call_args.kwargs
        self.assertEqual(call_kwargs['scope'], 'student-invite-creation-box')
        self.assertEqual(call_kwargs['target_label'], 'academia-y')

    @patch('student_identity.staff_views.maybe_emit_student_anomaly_alert')
    @patch('student_identity.staff_views.check_student_flow_rate_limit')
    @patch('student_identity.staff_views.get_student_operations_actor_role_slug')
    def test_both_alerts_emitted_when_both_rate_limits_exceeded(
        self, mock_role, mock_rate, mock_alert
    ):
        mock_role.return_value = 'manager'
        mock_rate.return_value = (False, {})

        view = self._make_view()
        view._track_invite_creation_anomalies(
            self._make_request(), invitation=self._make_invitation()
        )

        # 2 alerts: ator + box
        self.assertEqual(mock_alert.call_count, 2)
        scopes_emitted = {c.kwargs['scope'] for c in mock_alert.call_args_list}
        self.assertEqual(scopes_emitted, {
            'student-invite-creation-actor',
            'student-invite-creation-box',
        })

    @patch('student_identity.staff_views.maybe_emit_student_anomaly_alert')
    @patch('student_identity.staff_views.check_student_flow_rate_limit')
    @patch('student_identity.staff_views.get_student_operations_actor_role_slug')
    @override_settings(STUDENT_INVITE_CREATION_ACTOR_ALERT_THRESHOLD=5)
    def test_actor_threshold_uses_settings_override(
        self, mock_role, mock_rate, mock_alert
    ):
        """check_student_flow_rate_limit recebe o limite vindo de settings."""
        mock_role.return_value = 'manager'
        mock_rate.return_value = (True, {})

        view = self._make_view()
        view._track_invite_creation_anomalies(
            self._make_request(), invitation=self._make_invitation()
        )

        # Primeira chamada (actor) passa limit=5
        first_call_kwargs = mock_rate.call_args_list[0].kwargs
        self.assertEqual(first_call_kwargs['limit'], 5)

    @patch('student_identity.staff_views.maybe_emit_student_anomaly_alert')
    @patch('student_identity.staff_views.check_student_flow_rate_limit')
    @patch('student_identity.staff_views.get_student_operations_actor_role_slug')
    @override_settings(STUDENT_INVITE_CREATION_ACTOR_ALERT_THRESHOLD=0)
    def test_actor_threshold_minimum_enforced(self, mock_role, mock_rate, mock_alert):
        """Threshold mínimo é 1 — settings.X=0 vira max(1, 0)=1."""
        mock_role.return_value = 'manager'
        mock_rate.return_value = (True, {})

        view = self._make_view()
        view._track_invite_creation_anomalies(
            self._make_request(), invitation=self._make_invitation()
        )

        first_call_kwargs = mock_rate.call_args_list[0].kwargs
        self.assertEqual(first_call_kwargs['limit'], 1)

    @patch('student_identity.staff_views.maybe_emit_student_anomaly_alert')
    @patch('student_identity.staff_views.check_student_flow_rate_limit')
    @patch('student_identity.staff_views.get_student_operations_actor_role_slug')
    @override_settings(STUDENT_INVITE_CREATION_ACTOR_ALERT_WINDOW_SECONDS=30)
    def test_actor_window_minimum_enforced(self, mock_role, mock_rate, mock_alert):
        """Janela mínima é 60s — settings.X=30 vira max(60, 30)=60."""
        mock_role.return_value = 'manager'
        mock_rate.return_value = (True, {})

        view = self._make_view()
        view._track_invite_creation_anomalies(
            self._make_request(), invitation=self._make_invitation()
        )

        first_call_kwargs = mock_rate.call_args_list[0].kwargs
        self.assertEqual(first_call_kwargs['window_seconds'], 60)

    @patch('student_identity.staff_views.maybe_emit_student_anomaly_alert')
    @patch('student_identity.staff_views.check_student_flow_rate_limit')
    @patch('student_identity.staff_views.get_student_operations_actor_role_slug')
    def test_actor_alert_includes_invitation_metadata(
        self, mock_role, mock_rate, mock_alert
    ):
        """Metadata do alert deve conter box, invite_type, student_id."""
        mock_role.return_value = 'manager'
        mock_rate.side_effect = [(False, {}), (True, {})]
        inv = self._make_invitation(box_slug='academia-z', student_id=777)

        view = self._make_view()
        view._track_invite_creation_anomalies(self._make_request(), invitation=inv)

        metadata = mock_alert.call_args.kwargs['metadata']
        self.assertEqual(metadata['box_root_slug'], 'academia-z')
        self.assertEqual(metadata['invite_type'], 'individual')
        self.assertEqual(metadata['student_id'], 777)


# ===========================================================================
# finalize_student_oauth_callback — branches críticos
# ===========================================================================

class FinalizeStudentOAuthCallbackTest(unittest.TestCase):
    """L1: finalize_student_oauth_callback — oauth_actions.py:68.

    Branches:
    - handle_student_special_oauth_journey retorna redirect → retorna esse redirect
    - authentication_result.success=False → redirect para login + messages.error
    - failure_reason em invite-fail set → NÃO seta cookie student_invite_pending
    - failure_reason fora do set + invite_token presente → seta cookie
    """

    def _make_state_payload(self, invite_token: str = '') -> dict:
        return {'invite_token': invite_token}

    def _make_auth_result(self, success: bool = False, failure_reason: str = '', identity=None):
        result = MagicMock()
        result.success = success
        result.failure_reason = failure_reason
        result.identity = identity
        return result

    @patch('student_identity.oauth_actions.handle_student_special_oauth_journey')
    def test_returns_special_journey_redirect_when_provided(self, mock_special):
        """Se jornada especial detectada, retorna redirect dela imediatamente."""
        from student_identity.oauth_actions import finalize_student_oauth_callback

        expected_redirect = MagicMock(name='SpecialRedirect')
        mock_special.return_value = expected_redirect

        result = finalize_student_oauth_callback(
            request=MagicMock(),
            provider='google',
            state_payload=self._make_state_payload(),
            identity_payload=MagicMock(),
            authentication_result=self._make_auth_result(),
            identity_repository_class=MagicMock,
            map_failure_reason=lambda r: 'mapped',
        )

        self.assertIs(result, expected_redirect)

    @patch('student_identity.oauth_actions.messages')
    @patch('student_identity.oauth_actions.redirect')
    @patch('student_identity.oauth_actions.handle_student_special_oauth_journey')
    def test_failure_redirects_to_login_with_error_message(
        self, mock_special, mock_redirect, mock_messages
    ):
        from student_identity.oauth_actions import finalize_student_oauth_callback

        mock_special.return_value = None  # sem jornada especial
        mock_response = MagicMock()
        mock_response.set_cookie = MagicMock()
        mock_redirect.return_value = mock_response

        finalize_student_oauth_callback(
            request=MagicMock(),
            provider='google',
            state_payload=self._make_state_payload(),
            identity_payload=MagicMock(),
            authentication_result=self._make_auth_result(success=False, failure_reason='provider-subject-required'),
            identity_repository_class=MagicMock,
            map_failure_reason=lambda r: f'Mensagem para: {r}',
        )

        mock_messages.error.assert_called_once()
        # A mensagem mapeada deve ser passada ao messages.error
        error_message = mock_messages.error.call_args.args[1]
        self.assertEqual(error_message, 'Mensagem para: provider-subject-required')
        mock_redirect.assert_called_with('student-identity-login')

    @patch('student_identity.oauth_actions.messages')
    @patch('student_identity.oauth_actions.redirect')
    @patch('student_identity.oauth_actions.handle_student_special_oauth_journey')
    def test_cookie_set_when_failure_reason_is_outside_invite_failure_set(
        self, mock_special, mock_redirect, mock_messages
    ):
        """failure_reason NÃO é invite-related → cookie é setado."""
        from student_identity.oauth_actions import finalize_student_oauth_callback

        mock_special.return_value = None
        mock_response = MagicMock()
        mock_redirect.return_value = mock_response

        finalize_student_oauth_callback(
            request=MagicMock(),
            provider='google',
            state_payload=self._make_state_payload(invite_token='tok-abc'),
            identity_payload=MagicMock(),
            authentication_result=self._make_auth_result(
                success=False, failure_reason='student-email-ambiguous'
            ),
            identity_repository_class=MagicMock,
            map_failure_reason=lambda r: 'msg',
        )

        # Cookie student_invite_pending DEVE ser setado
        mock_response.set_cookie.assert_called_once()
        cookie_args = mock_response.set_cookie.call_args
        self.assertEqual(cookie_args.args[0], 'student_invite_pending')
        self.assertEqual(cookie_args.args[1], 'tok-abc')

    @patch('student_identity.oauth_actions.messages')
    @patch('student_identity.oauth_actions.redirect')
    @patch('student_identity.oauth_actions.handle_student_special_oauth_journey')
    def test_cookie_NOT_set_for_invite_specific_failure_reasons(
        self, mock_special, mock_redirect, mock_messages
    ):
        """failure_reason em invite-fail set → cookie NÃO é setado.

        Set: invite-not-found, invite-expired, invite-email-mismatch, invite-box-mismatch.
        """
        from student_identity.oauth_actions import finalize_student_oauth_callback

        for failure_reason in [
            'invite-not-found',
            'invite-expired',
            'invite-email-mismatch',
            'invite-box-mismatch',
        ]:
            mock_special.return_value = None
            mock_response = MagicMock()
            mock_redirect.return_value = mock_response

            finalize_student_oauth_callback(
                request=MagicMock(),
                provider='google',
                state_payload=self._make_state_payload(invite_token='tok-abc'),
                identity_payload=MagicMock(),
                authentication_result=self._make_auth_result(
                    success=False, failure_reason=failure_reason
                ),
                identity_repository_class=MagicMock,
                map_failure_reason=lambda r: 'msg',
            )

            mock_response.set_cookie.assert_not_called()

    @patch('student_identity.oauth_actions.messages')
    @patch('student_identity.oauth_actions.redirect')
    @patch('student_identity.oauth_actions.handle_student_special_oauth_journey')
    def test_cookie_NOT_set_when_invite_token_is_empty(
        self, mock_special, mock_redirect, mock_messages
    ):
        """Sem invite_token: cookie NÃO é setado mesmo se failure_reason permitir."""
        from student_identity.oauth_actions import finalize_student_oauth_callback

        mock_special.return_value = None
        mock_response = MagicMock()
        mock_redirect.return_value = mock_response

        finalize_student_oauth_callback(
            request=MagicMock(),
            provider='google',
            state_payload=self._make_state_payload(invite_token=''),
            identity_payload=MagicMock(),
            authentication_result=self._make_auth_result(
                success=False, failure_reason='student-email-ambiguous'
            ),
            identity_repository_class=MagicMock,
            map_failure_reason=lambda r: 'msg',
        )

        mock_response.set_cookie.assert_not_called()
