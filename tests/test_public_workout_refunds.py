from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.utils import timezone

from public_workouts.billing import get_or_create_subscription
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutPayment,
    PublicWorkoutPaymentStatus,
    PublicWorkoutRefundRequestStatus,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTier,
)
from public_workouts.refunds import (
    RefundNotEligibleError,
    process_refund_request,
    submit_refund_request,
)


class PublicWorkoutRefundTests(TestCase):
    def setUp(self):
        account = PublicWorkoutAccount.objects.create(email='garantia@example.com')
        self.subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL)
        self.subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
        self.subscription.stripe_subscription_id = 'sub_guarantee'
        self.subscription.save(update_fields=['status', 'stripe_subscription_id'])

    def _payment(self, *, days_ago=1):
        return PublicWorkoutPayment.objects.create(
            subscription=self.subscription, due_date=date.today(),
            paid_at=timezone.now() - timedelta(days=days_ago),
            gross_amount=Decimal('97.00'), status=PublicWorkoutPaymentStatus.PAID,
            stripe_invoice_id='in_guarantee',
        )

    def test_request_is_idempotent_inside_seven_days(self):
        self._payment()

        first = submit_refund_request(subscription=self.subscription, reason='Nao me adaptei')
        second = submit_refund_request(subscription=self.subscription, reason='Outro clique')

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.reason, 'Nao me adaptei')

    def test_request_after_deadline_is_rejected(self):
        self._payment(days_ago=8)

        with self.assertRaises(RefundNotEligibleError):
            submit_refund_request(subscription=self.subscription)

    @override_settings(STRIPE_SECRET_KEY='sk_test_x')
    @patch('stripe.Subscription.cancel')
    @patch('stripe.Refund.create', return_value={'id': 're_guarantee'})
    @patch('stripe.Invoice.retrieve', return_value={'payment_intent': 'pi_guarantee'})
    def test_processing_refunds_and_cancels_subscription(self, _invoice, refund_create, cancel):
        payment = self._payment()
        request_obj = submit_refund_request(subscription=self.subscription)

        processed = process_refund_request(request_obj.pk)
        payment.refresh_from_db()
        self.subscription.refresh_from_db()

        self.assertEqual(processed.status, PublicWorkoutRefundRequestStatus.REFUNDED)
        self.assertEqual(payment.status, PublicWorkoutPaymentStatus.REFUNDED)
        self.assertEqual(self.subscription.status, PublicWorkoutSubscriptionStatus.CANCELED)
        refund_create.assert_called_once()
        cancel.assert_called_once_with('sub_guarantee')
