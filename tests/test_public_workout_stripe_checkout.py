"""
ARQUIVO: testes do checkout proprio do corredor de treinos (Onda B2, Fatia B).

POR QUE ELE EXISTE:
- garante que o checkout nunca aciona o fluxo do box (N2): mode=subscription
  na conta reusada (STRIPE_SECRET_KEY do box), sem stripe_connected_account_id,
  com metadata.product='coaching' — o discriminador que o webhook handler
  usa pra decidir se o evento e do corredor.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from public_workouts.billing import get_or_create_subscription
from public_workouts.models import PublicWorkoutAccount
from public_workouts.stripe_checkout import PublicWorkoutStripeNotConfiguredError, start_subscription_checkout


class StartSubscriptionCheckoutTests(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='aluno@example.com')
        self.subscription = get_or_create_subscription(account=self.account, plan_slug='giovanna')

    @override_settings(PUBLIC_WORKOUT_STRIPE_PRICE_ID='', STRIPE_SECRET_KEY='sk_test_x')
    def test_raises_when_price_id_not_configured(self):
        with self.assertRaises(PublicWorkoutStripeNotConfiguredError):
            start_subscription_checkout(
                subscription=self.subscription, success_url='https://x/success', cancel_url='https://x/cancel'
            )

    @override_settings(PUBLIC_WORKOUT_STRIPE_PRICE_ID='price_123', STRIPE_SECRET_KEY='')
    def test_raises_when_secret_key_not_configured(self):
        with self.assertRaises(PublicWorkoutStripeNotConfiguredError):
            start_subscription_checkout(
                subscription=self.subscription, success_url='https://x/success', cancel_url='https://x/cancel'
            )

    @override_settings(PUBLIC_WORKOUT_STRIPE_PRICE_ID='price_123', STRIPE_SECRET_KEY='sk_test_x')
    @patch('stripe.checkout.Session.create')
    def test_creates_session_in_subscription_mode_with_coaching_metadata(self, mock_create):
        mock_create.return_value = MagicMock(url='https://checkout.stripe.com/pay/cs_test_123')

        url = start_subscription_checkout(
            subscription=self.subscription, success_url='https://x/success', cancel_url='https://x/cancel'
        )

        self.assertEqual(url, 'https://checkout.stripe.com/pay/cs_test_123')
        _, kwargs = mock_create.call_args
        self.assertEqual(kwargs['mode'], 'subscription')
        self.assertEqual(kwargs['line_items'], [{'price': 'price_123', 'quantity': 1}])
        self.assertEqual(kwargs['metadata']['product'], 'coaching')
        self.assertEqual(kwargs['metadata']['public_workout_subscription_id'], str(self.subscription.pk))
        self.assertEqual(kwargs['subscription_data']['metadata']['product'], 'coaching')
        # Sem Connect Express (C5): nenhuma chave de conta conectada no payload.
        self.assertNotIn('stripe_account', kwargs)
        self.assertNotIn('on_behalf_of', kwargs)
        self.assertNotIn('application_fee_percent', kwargs)

    @override_settings(PUBLIC_WORKOUT_STRIPE_PRICE_ID='price_123', STRIPE_SECRET_KEY='sk_test_x')
    @patch('stripe.checkout.Session.create')
    def test_idempotency_key_includes_subscription_id(self, mock_create):
        mock_create.return_value = MagicMock(url='https://checkout.stripe.com/pay/cs_test_123')

        start_subscription_checkout(
            subscription=self.subscription, success_url='https://x/success', cancel_url='https://x/cancel'
        )

        _, kwargs = mock_create.call_args
        self.assertIn(str(self.subscription.pk), kwargs['idempotency_key'])
