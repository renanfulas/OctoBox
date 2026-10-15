"""
ARQUIVO: testes do reenvio self-service do email de ativacao.

POR QUE ELE EXISTE:
- Achado S4 do relatorio de simulacao de 30 dias (docs/reports/simulation_30_days_e2e_box.md):
  cliente que pagou mas cujo email de ativacao falhou ficava sem nenhum
  caminho na tela de sucesso. Cobre a nova ResendActivationEmailView e o
  throttle de reenvio em signup/services.py.

SOURCE-UNDER-TEST: signup/views.py (ResendActivationEmailView), signup/services.py
(resend_activation_rate_limit_exceeded).
"""

from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from freezegun import freeze_time

from shared_support.platform_cache import platform_cache
from signup.models import PendingSignup, PendingSignupPlan, PendingSignupStatus
from signup.services import generate_magic_token
from signup.views import ResendActivationEmailView


def _make_pending(*, status: str = PendingSignupStatus.PAID) -> PendingSignup:
    return PendingSignup.objects.create(
        email='owner@academia.test',
        full_name='Maria Silva',
        box_name='Academia Forte',
        plan=PendingSignupPlan.MONTHLY,
        status=status,
    )


class ResendActivationEmailViewTests(TestCase):
    def setUp(self):
        platform_cache.clear()

    def _url(self, pending):
        return reverse('signup-resend-activation', args=[pending.pk])

    def _assert_generic(self, response):
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body, {'ok': True, 'message': ResendActivationEmailView.GENERIC_MESSAGE})
        self.assertNotIn('@', body['message'])

    @patch('signup.views.send_onboarding_email', return_value=True)
    def test_nonexistent_pending_gets_same_generic_answer(self, mock_send):
        response = self.client.post(reverse('signup-resend-activation', args=[999_999]))

        self._assert_generic(response)
        mock_send.assert_not_called()

    @patch('signup.views.send_onboarding_email', return_value=True)
    def test_already_activated_gets_same_generic_answer_and_sends_nothing(self, mock_send):
        pending = _make_pending(status=PendingSignupStatus.ACTIVATED)

        self._assert_generic(self.client.post(self._url(pending)))
        mock_send.assert_not_called()

    @patch('signup.views.send_onboarding_email', return_value=True)
    def test_not_paid_yet_gets_same_generic_answer_and_sends_nothing(self, mock_send):
        pending = _make_pending(status=PendingSignupStatus.PENDING)

        self._assert_generic(self.client.post(self._url(pending)))
        mock_send.assert_not_called()

    @patch('signup.views.send_onboarding_email', return_value=True)
    def test_resends_email_for_paid_pending_without_echoing_the_address(self, mock_send):
        pending = _make_pending(status=PendingSignupStatus.PAID)

        response = self.client.post(self._url(pending))

        self._assert_generic(response)
        self.assertNotIn(pending.email, response.content.decode())
        mock_send.assert_called_once()
        _, kwargs = mock_send.call_args
        self.assertIn('/onboarding/', kwargs['activation_url'])

    @patch('signup.views.send_onboarding_email', return_value=False)
    def test_email_gateway_failure_looks_the_same_to_the_caller(self, _mock_send):
        pending = _make_pending(status=PendingSignupStatus.PAID)

        self._assert_generic(self.client.post(self._url(pending)))
    @patch('signup.views.send_onboarding_email', return_value=True)
    def test_second_request_within_cooldown_is_rate_limited(self, _mock_send):
        pending = _make_pending(status=PendingSignupStatus.PAID)

        first = self.client.post(self._url(pending))
        second = self.client.post(self._url(pending))

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second.json()['code'], 'rate-limited')


class ExpiredOnboardingLinkResendTests(TestCase):
    def setUp(self):
        platform_cache.clear()

    def _expired_token(self, pending):
        with freeze_time('2026-01-01 12:00:00'):
            token = generate_magic_token(pending)
        return token

    def test_expired_token_page_offers_resend_button_for_that_signup(self):
        pending = _make_pending(status=PendingSignupStatus.PAID)
        token = self._expired_token(pending)

        with freeze_time('2026-02-01 12:00:00'):
            response = self.client.get(reverse('signup-onboarding', kwargs={'token': token}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-resend-activation')
        self.assertContains(response, reverse('signup-resend-activation', args=[pending.pk]))

    def test_tampered_token_does_not_get_a_resend_button(self):
        pending = _make_pending(status=PendingSignupStatus.PAID)
        token = self._expired_token(pending) + 'x'

        response = self.client.get(reverse('signup-onboarding', kwargs={'token': token}))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'data-resend-activation')


class CheckoutSuccessResendPanelRenderingTests(TestCase):
    def setUp(self):
        platform_cache.clear()

    def test_resend_panel_renders_for_paid_pending(self):
        pending = _make_pending(status=PendingSignupStatus.PAID)

        response = self.client.get(reverse('signup-checkout-success'), {'pending': pending.pk})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reenviar e-mail de ativação')
        self.assertContains(response, reverse('signup-resend-activation', args=[pending.pk]))

    def test_resend_panel_absent_when_no_pending(self):
        response = self.client.get(reverse('signup-checkout-success'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Reenviar e-mail de ativação')
