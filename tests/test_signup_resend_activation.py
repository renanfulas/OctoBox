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

from shared_support.platform_cache import platform_cache
from signup.models import PendingSignup, PendingSignupPlan, PendingSignupStatus


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

    def test_returns_404_for_nonexistent_pending(self):
        response = self.client.post(reverse('signup-resend-activation', args=[999_999]))
        self.assertEqual(response.status_code, 404)

    def test_returns_409_when_already_activated(self):
        pending = _make_pending(status=PendingSignupStatus.ACTIVATED)

        response = self.client.post(self._url(pending))

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'already-activated')

    def test_returns_409_when_not_paid_yet(self):
        pending = _make_pending(status=PendingSignupStatus.PENDING)

        response = self.client.post(self._url(pending))

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'not-paid-yet')

    @patch('signup.views.send_onboarding_email', return_value=True)
    def test_resends_email_for_paid_pending(self, mock_send):
        pending = _make_pending(status=PendingSignupStatus.PAID)

        response = self.client.post(self._url(pending))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['ok'])
        self.assertIn(pending.email, body['message'])
        mock_send.assert_called_once()
        _, kwargs = mock_send.call_args
        self.assertIn(f'/onboarding/', kwargs['activation_url'])

    @patch('signup.views.send_onboarding_email', return_value=False)
    def test_returns_502_when_email_gateway_fails(self, _mock_send):
        pending = _make_pending(status=PendingSignupStatus.PAID)

        response = self.client.post(self._url(pending))

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()['code'], 'send-failed')

    @patch('signup.views.send_onboarding_email', return_value=True)
    def test_second_request_within_cooldown_is_rate_limited(self, _mock_send):
        pending = _make_pending(status=PendingSignupStatus.PAID)

        first = self.client.post(self._url(pending))
        second = self.client.post(self._url(pending))

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second.json()['code'], 'rate-limited')


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
