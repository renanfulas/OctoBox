from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from public_workouts.metrics import build_metrics_snapshot, capture_daily_metrics
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutCampaignSpend,
    PublicWorkoutFunnelEvent,
    PublicWorkoutMetricSnapshot,
    PublicWorkoutSubscription,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTier,
    PublicWorkoutWorkItem,
    PublicWorkoutWorkItemType,
)


@override_settings(PUBLIC_WORKOUT_CAPACITY_MODE='observe')
class PublicWorkoutMetricsTests(TestCase):
    def test_missing_cost_never_reports_zero_cac(self):
        PublicWorkoutFunnelEvent.objects.create(
            event_type='invoice_paid', source='instagram', campaign='setembro',
        )

        snapshot = build_metrics_snapshot()

        self.assertEqual(snapshot['commercial']['campaign_economics'], [])

    def test_campaign_spend_without_customer_has_unavailable_cac(self):
        PublicWorkoutCampaignSpend.objects.create(
            source='google', campaign='search', starts_on=date.today() - timedelta(days=5),
            ends_on=date.today(), amount=Decimal('300.00'),
        )

        snapshot = build_metrics_snapshot()

        self.assertIsNone(snapshot['commercial']['campaign_economics'][0]['cac'])

    def test_attribution_rate_distinguishes_known_paid_events(self):
        PublicWorkoutFunnelEvent.objects.create(event_type='invoice_paid', source='instagram')
        PublicWorkoutFunnelEvent.objects.create(event_type='invoice_paid', source='')

        snapshot = build_metrics_snapshot()

        self.assertEqual(snapshot['commercial']['attribution'], {
            'paid_events': 2, 'known_paid_events': 1, 'known_paid_rate': 0.5,
        })

    def test_overdue_work_turns_growth_gate_red(self):
        account = PublicWorkoutAccount.objects.create(email='metricas@example.com')
        subscription = PublicWorkoutSubscription.objects.create(
            account=account, tier=PublicWorkoutTier.ESSENCIAL,
            status=PublicWorkoutSubscriptionStatus.ACTIVE,
        )
        PublicWorkoutWorkItem.objects.create(
            account=account, subscription=subscription,
            item_type=PublicWorkoutWorkItemType.TRAINING_PROGRAM,
            cycle_key='metricas', due_at=timezone.now() - timedelta(hours=1),
        )

        snapshot = build_metrics_snapshot()

        self.assertEqual(snapshot['growth_gate']['status'], 'red')
        self.assertIn('work_items_overdue', snapshot['growth_gate']['blockers'])

    def test_daily_capture_updates_same_day_instead_of_duplicating(self):
        capture_daily_metrics()
        capture_daily_metrics()

        self.assertEqual(PublicWorkoutMetricSnapshot.objects.count(), 1)
