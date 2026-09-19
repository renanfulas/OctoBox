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
from public_workouts.models import PublicWorkoutAccount, PublicWorkoutTier
from public_workouts.stripe_checkout import (
    PublicWorkoutStripeNotConfiguredError,
    start_customer_portal_session,
    start_subscription_checkout,
)


class StartSubscriptionCheckoutTests(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='aluno@example.com')
        self.subscription = get_or_create_subscription(account=self.account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='giovanna')

    @override_settings(PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL='', STRIPE_SECRET_KEY='sk_test_x')
    def test_raises_when_price_id_not_configured(self):
        with self.assertRaises(PublicWorkoutStripeNotConfiguredError):
            start_subscription_checkout(
                subscription=self.subscription, success_url='https://x/success', cancel_url='https://x/cancel'
            )

    @override_settings(PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL='price_123', STRIPE_SECRET_KEY='')
    def test_raises_when_secret_key_not_configured(self):
        with self.assertRaises(PublicWorkoutStripeNotConfiguredError):
            start_subscription_checkout(
                subscription=self.subscription, success_url='https://x/success', cancel_url='https://x/cancel'
            )

    @override_settings(PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL='price_123', STRIPE_SECRET_KEY='sk_test_x')
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
        self.assertEqual(kwargs['metadata']['tier'], PublicWorkoutTier.ESSENCIAL)
        self.assertEqual(kwargs['subscription_data']['metadata']['product'], 'coaching')
        self.assertEqual(kwargs['subscription_data']['metadata']['tier'], PublicWorkoutTier.ESSENCIAL)
        # Sem Connect Express (C5): nenhuma chave de conta conectada no payload.
        self.assertNotIn('stripe_account', kwargs)
        self.assertNotIn('on_behalf_of', kwargs)
        self.assertNotIn('application_fee_percent', kwargs)

    @override_settings(PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL='price_123', STRIPE_SECRET_KEY='sk_test_x')
    @patch('stripe.checkout.Session.create')
    def test_idempotency_key_includes_subscription_id(self, mock_create):
        mock_create.return_value = MagicMock(url='https://checkout.stripe.com/pay/cs_test_123')

        start_subscription_checkout(
            subscription=self.subscription, success_url='https://x/success', cancel_url='https://x/cancel'
        )

        _, kwargs = mock_create.call_args
        self.assertIn(str(self.subscription.pk), kwargs['idempotency_key'])

    @override_settings(
        PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL='price_essencial',
        PUBLIC_WORKOUT_STRIPE_PRICE_ID_COMPLETO='price_completo',
        PUBLIC_WORKOUT_STRIPE_PRICE_ID_PREMIUM='price_premium',
        STRIPE_SECRET_KEY='sk_test_x',
    )
    @patch('stripe.checkout.Session.create')
    def test_each_tier_resolves_its_own_price_id(self, mock_create):
        mock_create.return_value = MagicMock(url='https://checkout.stripe.com/pay/cs_test_123')
        expected_price_by_tier = {
            PublicWorkoutTier.ESSENCIAL: 'price_essencial',
            PublicWorkoutTier.COMPLETO: 'price_completo',
            PublicWorkoutTier.PREMIUM: 'price_premium',
        }

        for tier, expected_price_id in expected_price_by_tier.items():
            self.subscription.tier = tier
            self.subscription.save(update_fields=['tier'])

            start_subscription_checkout(
                subscription=self.subscription, success_url='https://x/success', cancel_url='https://x/cancel'
            )

            _, kwargs = mock_create.call_args
            self.assertEqual(kwargs['line_items'], [{'price': expected_price_id, 'quantity': 1}])
            self.assertEqual(kwargs['metadata']['tier'], tier)

    @override_settings(PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL='price_123', STRIPE_SECRET_KEY='sk_test_x')
    @patch('stripe.checkout.Session.create')
    def test_subscription_has_the_trial_period_configured(self, mock_create):
        # Decisao do Renan: cartao capturado no checkout, sem cobrar por 2
        # dias — trial nativo da Stripe (subscription_data.trial_period_days),
        # nao um cupom que zeraria o valor da fatura.
        from public_workouts.stripe_checkout import PUBLIC_WORKOUT_TRIAL_PERIOD_DAYS

        mock_create.return_value = MagicMock(url='https://checkout.stripe.com/pay/cs_test_123')

        start_subscription_checkout(
            subscription=self.subscription, success_url='https://x/success', cancel_url='https://x/cancel'
        )

        _, kwargs = mock_create.call_args
        self.assertEqual(kwargs['subscription_data']['trial_period_days'], PUBLIC_WORKOUT_TRIAL_PERIOD_DAYS)
        self.assertEqual(PUBLIC_WORKOUT_TRIAL_PERIOD_DAYS, 2)

    @override_settings(PUBLIC_WORKOUT_STRIPE_PRICE_ID_COMPLETO='', STRIPE_SECRET_KEY='sk_test_x')
    def test_raises_a_clear_error_when_a_tiers_price_id_is_not_configured(self):
        self.subscription.tier = PublicWorkoutTier.COMPLETO
        self.subscription.save(update_fields=['tier'])

        with self.assertRaisesMessage(PublicWorkoutStripeNotConfiguredError, 'PUBLIC_WORKOUT_STRIPE_PRICE_ID_COMPLETO'):
            start_subscription_checkout(
                subscription=self.subscription, success_url='https://x/success', cancel_url='https://x/cancel'
            )


class StartCustomerPortalSessionTests(TestCase):
    # Onda B2, item 6 (Customer Portal) — ultimo item pendente da onda.

    @override_settings(STRIPE_SECRET_KEY='')
    def test_raises_when_secret_key_not_configured(self):
        with self.assertRaises(PublicWorkoutStripeNotConfiguredError):
            start_customer_portal_session(customer_id='cus_123', return_url='https://x/voltar')

    @override_settings(STRIPE_SECRET_KEY='sk_test_x')
    @patch('stripe.billing_portal.Session.create')
    def test_creates_portal_session_for_the_given_customer(self, mock_create):
        mock_create.return_value = MagicMock(url='https://billing.stripe.com/session/bps_test_123')

        url = start_customer_portal_session(customer_id='cus_123', return_url='https://x/voltar')

        self.assertEqual(url, 'https://billing.stripe.com/session/bps_test_123')
        _, kwargs = mock_create.call_args
        self.assertEqual(kwargs['customer'], 'cus_123')
        self.assertEqual(kwargs['return_url'], 'https://x/voltar')
        # Sem Connect Express (C5, mesma decisao do checkout): nenhuma chave
        # de conta conectada no payload.
        self.assertNotIn('stripe_account', kwargs)
