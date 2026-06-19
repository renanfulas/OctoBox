"""
ARQUIVO: testes das views do fluxo Early Adopter (signup/views.py) + os 2 services
que faltavam cobertura (activate_and_provision, send_onboarding_email).

POR QUE EXISTE:
- signup/views.py e o checkout publico + onboarding pos-pagamento: e onde nasce a
  conta paga (owner + box). Estava a ~24%. Bug aqui = funil de receita quebrado.
- Complementa tests/test_signup_services.py (que ja cobre os services puros).

ESTRATEGIA:
- Views testadas via Client; os services Stripe sao mockados no namespace de
  signup.views (import em nivel de modulo).
- activate_and_provision roda de verdade (com _run_step do provision mockado).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from signup.models import PendingSignup, PendingSignupPlan, PendingSignupStatus
from signup.services import StripeNotConfiguredError, UsernameTakenError, generate_magic_token

User = get_user_model()


def _pending(*, status=PendingSignupStatus.PENDING, email='dono@box.test', plan=PendingSignupPlan.ANNUAL):
    return PendingSignup.objects.create(
        email=email, full_name='Dona do Box', box_name='Box Teste', phone='11999998888',
        plan=plan, status=status,
    )


_VALID_CHECKOUT_POST = {
    'email': 'dono@box.test',
    'full_name': 'Dona do Box',
    'box_name': 'Box Teste',
    'phone': '(11) 99999-8888',
}


# ===========================================================================
# CheckoutFormView  (/checkout/)
# ===========================================================================

class CheckoutFormViewTests(TestCase):

    def test_get_defaults_to_annual_plan(self):
        resp = self.client.get(reverse('signup-checkout'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['plan'], 'annual')
        self.assertEqual(resp.context['plan_display']['label'], 'Anual')
        self.assertEqual(resp.context['post_program_price'], 'R$ 197/mês')

    def test_get_with_monthly_plan(self):
        resp = self.client.get(reverse('signup-checkout') + '?plan=monthly')
        self.assertEqual(resp.context['plan'], 'monthly')
        self.assertEqual(resp.context['plan_display']['label'], 'Mensal')

    def test_get_with_invalid_plan_falls_back_to_annual(self):
        resp = self.client.get(reverse('signup-checkout') + '?plan=pirata')
        self.assertEqual(resp.context['plan'], 'annual')

    @patch('signup.views.create_checkout_session', return_value='https://checkout.stripe/cs_x')
    def test_post_valid_creates_pending_and_redirects_to_stripe(self, mock_create):
        resp = self.client.post(reverse('signup-checkout') + '?plan=monthly', _VALID_CHECKOUT_POST)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], 'https://checkout.stripe/cs_x')
        pending = PendingSignup.objects.get(email='dono@box.test')
        self.assertEqual(pending.plan, 'monthly')
        self.assertEqual(pending.phone, '11999998888')  # normalizado
        mock_create.assert_called_once()

    @patch('signup.views.create_checkout_session', side_effect=StripeNotConfiguredError('off'))
    def test_post_stripe_not_configured_redirects_to_pending(self, _mock):
        resp = self.client.post(reverse('signup-checkout'), _VALID_CHECKOUT_POST)
        self.assertEqual(resp.status_code, 302)
        pending = PendingSignup.objects.get(email='dono@box.test')
        self.assertEqual(
            resp['Location'],
            reverse('signup-checkout-pending', kwargs={'pending_id': pending.pk}),
        )

    @patch('signup.views.create_checkout_session', side_effect=RuntimeError('boom'))
    def test_post_unexpected_error_redirects_to_pending(self, _mock):
        resp = self.client.post(reverse('signup-checkout'), _VALID_CHECKOUT_POST)
        self.assertEqual(resp.status_code, 302)
        pending = PendingSignup.objects.get(email='dono@box.test')
        self.assertIn(str(pending.pk), resp['Location'])

    def test_post_invalid_form_rerenders_without_creating_pending(self):
        bad = dict(_VALID_CHECKOUT_POST, phone='123')  # telefone curto
        resp = self.client.post(reverse('signup-checkout'), bad)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(PendingSignup.objects.filter(email='dono@box.test').exists())


# ===========================================================================
# CheckoutSuccessView  (/checkout/sucesso/)
# ===========================================================================

class CheckoutSuccessViewTests(TestCase):

    def _url(self, pending=None, session_id=None):
        url = reverse('signup-checkout-success')
        params = []
        if pending is not None:
            params.append(f'pending={pending}')
        if session_id is not None:
            params.append(f'session_id={session_id}')
        return url + ('?' + '&'.join(params) if params else '')

    @patch('signup.views.query_stripe_session_status')
    def test_paid_marks_pending_paid(self, mock_status):
        pending = _pending(status=PendingSignupStatus.PENDING)
        mock_status.return_value = {
            'paid': True, 'customer_id': 'cus_x', 'subscription_id': 'sub_x',
            'amount_total': 9700, 'payment_status': 'paid',
        }
        resp = self.client.get(self._url(pending=pending.pk, session_id='cs_x'))
        self.assertEqual(resp.status_code, 200)
        pending.refresh_from_db()
        self.assertEqual(pending.status, PendingSignupStatus.PAID)
        self.assertEqual(pending.stripe_customer_id, 'cus_x')
        self.assertEqual(resp.context['stripe_status']['amount_brl'], 'R$ 97,00')

    @patch('signup.views.query_stripe_session_status', return_value={'paid': False, 'amount_total': 0})
    def test_unpaid_does_not_mark_pending(self, _mock):
        pending = _pending(status=PendingSignupStatus.PENDING)
        resp = self.client.get(self._url(pending=pending.pk, session_id='cs_x'))
        self.assertEqual(resp.status_code, 200)
        pending.refresh_from_db()
        self.assertEqual(pending.status, PendingSignupStatus.PENDING)

    def test_no_session_id_renders_without_stripe_status(self):
        pending = _pending()
        resp = self.client.get(self._url(pending=pending.pk))
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context['stripe_status'])
        self.assertEqual(resp.context['mode'], 'success')

    def test_invalid_pending_id_renders_gracefully(self):
        resp = self.client.get(self._url(pending='abc', session_id='cs_x'))
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context['pending'])


# ===========================================================================
# CheckoutCanceledView  (/checkout/cancelado/)
# ===========================================================================

class CheckoutCanceledViewTests(TestCase):

    def test_pending_is_marked_canceled(self):
        pending = _pending(status=PendingSignupStatus.PENDING)
        resp = self.client.get(reverse('signup-checkout-canceled') + f'?pending={pending.pk}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['mode'], 'canceled')
        pending.refresh_from_db()
        self.assertEqual(pending.status, PendingSignupStatus.CANCELED)

    def test_paid_pending_is_not_canceled(self):
        pending = _pending(status=PendingSignupStatus.PAID)
        self.client.get(reverse('signup-checkout-canceled') + f'?pending={pending.pk}')
        pending.refresh_from_db()
        self.assertEqual(pending.status, PendingSignupStatus.PAID)

    def test_no_pending_renders(self):
        resp = self.client.get(reverse('signup-checkout-canceled'))
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context['pending'])


# ===========================================================================
# CheckoutPendingStripeView  (/checkout/aguardando/<id>/)
# ===========================================================================

class CheckoutPendingStripeViewTests(TestCase):

    def test_renders_for_existing_pending(self):
        pending = _pending()
        resp = self.client.get(reverse('signup-checkout-pending', kwargs={'pending_id': pending.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['mode'], 'manual_followup')
        self.assertEqual(resp.context['pending'].pk, pending.pk)

    def test_404_for_missing_pending(self):
        resp = self.client.get(reverse('signup-checkout-pending', kwargs={'pending_id': 999999}))
        self.assertEqual(resp.status_code, 404)


# ===========================================================================
# OnboardingWizardView  (/onboarding/<token>/)
# ===========================================================================

class OnboardingWizardViewTests(TestCase):

    def _valid_post(self, username='donobox'):
        return {'username': username, 'password': 'senhaforte123', 'password_confirm': 'senhaforte123'}

    def test_get_valid_token_renders_form_with_suggested_username(self):
        pending = _pending(status=PendingSignupStatus.PAID, email='joao.silva@box.test')
        token = generate_magic_token(pending)
        resp = self.client.get(reverse('signup-onboarding', kwargs={'token': token}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['pending'].pk, pending.pk)
        self.assertEqual(resp.context['suggested_username'], 'joao.silva')
        self.assertIsNone(resp.context['token_error'])

    def test_get_invalid_token_shows_error(self):
        resp = self.client.get(reverse('signup-onboarding', kwargs={'token': 'lixo-invalido'}))
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context['pending'])
        self.assertEqual(resp.context['token_error'], 'token-invalido')
        self.assertEqual(resp.context['suggested_username'], '')

    @patch('signup.views.activate_and_provision')
    def test_post_valid_activates_logs_in_and_redirects_to_thank_you(self, mock_activate):
        pending = _pending(status=PendingSignupStatus.PAID)
        token = generate_magic_token(pending)
        user = User.objects.create_user(username='donobox', email='dono@box.test')
        mock_activate.return_value = (user, MagicMock())

        resp = self.client.post(
            reverse('signup-onboarding', kwargs={'token': token}), self._valid_post()
        )

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], reverse('signup-thank-you'))
        mock_activate.assert_called_once()
        self.assertIn('_auth_user_id', self.client.session)  # logou

    def test_post_with_invalid_token_shows_error_and_does_not_create_user(self):
        resp = self.client.post(
            reverse('signup-onboarding', kwargs={'token': 'lixo-invalido'}), self._valid_post()
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username='donobox').exists())

    @patch('signup.views.activate_and_provision', side_effect=UsernameTakenError('donobox'))
    def test_post_username_taken_shows_field_error(self, _mock):
        pending = _pending(status=PendingSignupStatus.PAID)
        token = generate_magic_token(pending)
        resp = self.client.post(
            reverse('signup-onboarding', kwargs={'token': token}), self._valid_post()
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'já está em uso')

    @patch('signup.views.activate_and_provision', side_effect=RuntimeError('db down'))
    def test_post_unexpected_error_rerenders(self, _mock):
        pending = _pending(status=PendingSignupStatus.PAID)
        token = generate_magic_token(pending)
        resp = self.client.post(
            reverse('signup-onboarding', kwargs={'token': token}), self._valid_post()
        )
        self.assertEqual(resp.status_code, 200)


# ===========================================================================
# ThankYouView  (/obrigado/)
# ===========================================================================

class ThankYouViewTests(TestCase):

    def test_anonymous_redirected_to_login(self):
        resp = self.client.get(reverse('signup-thank-you'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp['Location'])

    def test_authenticated_user_sees_welcome(self):
        user = User.objects.create_user(username='ownerwelcome', email='ow@box.test', first_name='Ana')
        self.client.force_login(user)
        resp = self.client.get(reverse('signup-thank-you'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['user_first_name'], 'Ana')


# ===========================================================================
# activate_and_provision  (orquestra owner + box; ainda nao coberto)
# ===========================================================================

@pytest.mark.public_schema
class ActivateAndProvisionTests(TestCase):

    def setUp(self):
        self.pending = _pending(status=PendingSignupStatus.PAID, email='dono2@box.test')

    @patch('control.services._run_step')
    def test_creates_owner_and_provisions_box(self, mock_step):
        mock_step.return_value = None
        from control.models import Box
        from signup.services import activate_and_provision

        user, box = activate_and_provision(
            pending_signup=self.pending, username='dono2box', raw_password='senhaforte123',
        )

        self.assertEqual(user.username, 'dono2box')
        self.assertEqual(box.owner_user_id, user.pk)
        self.assertEqual(box.status, Box.Status.ACTIVE)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, PendingSignupStatus.ACTIVATED)
        self.assertEqual(self.pending.activated_user_id, user.pk)


# ===========================================================================
# send_onboarding_email  (gateway de email; ainda nao coberto)
# ===========================================================================

class SendOnboardingEmailTests(TestCase):

    def setUp(self):
        self.pending = _pending(status=PendingSignupStatus.PAID)

    @patch('signup.email_sender.send_html_email')
    def test_returns_true_on_success(self, mock_send):
        from signup.services import send_onboarding_email
        ok = send_onboarding_email(self.pending, activation_url='https://octoboxfit.com.br/onboarding/t/')
        self.assertTrue(ok)
        mock_send.assert_called_once()

    @patch('signup.email_sender.send_html_email')
    def test_returns_false_on_delivery_error(self, mock_send):
        from student_identity.delivery_gateways import StudentEmailDeliveryError
        from signup.services import send_onboarding_email
        mock_send.side_effect = StudentEmailDeliveryError('smtp recusou')
        ok = send_onboarding_email(self.pending, activation_url='https://octoboxfit.com.br/onboarding/t/')
        self.assertFalse(ok)

    @patch('signup.email_sender.send_html_email', side_effect=RuntimeError('inesperado'))
    def test_returns_false_on_unexpected_error(self, _mock):
        from signup.services import send_onboarding_email
        ok = send_onboarding_email(self.pending, activation_url='https://octoboxfit.com.br/onboarding/t/')
        self.assertFalse(ok)
