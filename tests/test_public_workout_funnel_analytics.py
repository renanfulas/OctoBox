from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock

from django.contrib.admin import AdminSite
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase, override_settings
from django.core.management import call_command
from io import StringIO
import json
from django.utils import timezone

from public_workouts.admin import PublicWorkoutAcquisitionSessionAdmin
from public_workouts.funnel_analytics import build_acquisition_report
from public_workouts.models import (
    PublicWorkoutAccount, PublicWorkoutAcquisitionSession, PublicWorkoutFunnelEvent,
    PublicWorkoutPayment, PublicWorkoutPaymentStatus, PublicWorkoutSubscription,
)


@override_settings(PUBLIC_WORKOUT_FUNNEL_TRACKING_ENABLED=True)
class FunnelAnalyticsTests(TestCase):
    def setUp(self):
        self.at = timezone.now()

    def visitor(self, days=10, source='instagram'):
        session = PublicWorkoutAcquisitionSession.objects.create(
            first_seen_at=self.at - timedelta(days=days), first_source=source,
            first_campaign='campanha', first_medium='paid_social', landing_variant='curva3',
        )
        self.signal(session, 'landing_viewed')
        return session

    def signal(self, session, name, days_after=0):
        return PublicWorkoutFunnelEvent.objects.create(
            acquisition_session=session, event_type=name,
            occurred_at=session.first_seen_at + timedelta(days=days_after),
        )

    def pay(self, session, days_after=1, status=PublicWorkoutPaymentStatus.PAID, amount='97'):
        if not session.account_id:
            account = PublicWorkoutAccount.objects.create(email=f'{session.pk}@example.com')
            session.account = account
            session.subscription = PublicWorkoutSubscription.objects.create(account=account)
            session.save()
        return PublicWorkoutPayment.objects.create(
            subscription=session.subscription, gross_amount=Decimal(amount), status=status,
            due_date=self.at.date(), paid_at=session.first_seen_at + timedelta(days=days_after),
        )

    def report(self, **kwargs):
        return build_acquisition_report(at=self.at, **kwargs)

    def test_reloads_renewals_and_duplicate_events_do_not_inflate_conversion(self):
        payer = self.visitor()
        self.visitor()
        for _ in range(4):
            self.signal(payer, 'landing_viewed')
            self.signal(payer, 'checkout_started')
            self.signal(payer, 'invoice_paid')
        self.pay(payer)
        self.pay(payer, days_after=3)
        report = self.report()
        self.assertEqual((report['visitors'], report['paid'], report['conversion_percent']), (2, 1, 50))
        self.assertEqual(report['mature_conversion_percent'], 50)
        self.assertEqual(report['coverage']['new_payers_in_period'], 1)

    def test_browser_payment_claim_does_not_count_as_paid(self):
        visitor = self.visitor()
        self.signal(visitor, 'invoice_paid')
        self.signal(visitor, 'checkout_authorized')
        self.assertEqual(self.report()['paid'], 0)

    def test_payment_without_browser_signals_still_converts(self):
        self.pay(self.visitor())
        report = self.report()
        self.assertEqual([step['visitors'] for step in report['steps']], [1, 1, 1, 1])

    def test_mature_abandonment_excludes_people_still_deciding(self):
        old = self.visitor()
        self.signal(old, 'signup_started')
        self.signal(old, 'tier_selected')
        self.visitor(days=1)
        report = self.report()
        self.assertEqual(report['pending_visitors'], 1)
        self.assertEqual(report['mature_visitors'], 1)
        self.assertEqual(report['steps'][1]['not_advanced'], 1)
        self.assertEqual(report['friction'][1]['not_advanced'], 1)

    def test_existing_payer_and_renewal_are_not_new_acquisition(self):
        visitor = self.visitor()
        self.pay(visitor, days_after=-35)
        self.pay(visitor, days_after=1)
        report = self.report()
        self.assertEqual(report['excluded_existing_customers'], 1)
        self.assertEqual(report['visitors'], 0)
        self.assertEqual(report['coverage']['new_payers_in_period'], 0)
        self.assertIsNone(report['conversion_percent'])

    def test_zero_value_is_not_payment_and_refund_does_not_erase_acquisition(self):
        self.pay(self.visitor(), amount='0')
        self.pay(self.visitor(), status=PublicWorkoutPaymentStatus.REFUNDED)
        report = self.report()
        self.assertEqual(report['paid'], 1)
        self.assertEqual(report['refunded_first_payments'], 1)

    def test_payment_outside_conversion_window_or_in_future_is_not_counted(self):
        self.pay(self.visitor(), days_after=8)
        self.pay(self.visitor(days=1), days_after=2)
        report = self.report()
        self.assertEqual(report['paid'], 0)
        self.assertEqual(report['coverage']['new_payers_in_period'], 1)

    def test_utm_groups_share_the_same_cohort_denominator(self):
        self.pay(self.visitor(source='google'))
        self.visitor(source='instagram')
        rows = {row['source']: row for row in self.report()['channels']}
        self.assertEqual(rows['google']['conversion_percent'], 100)
        self.assertEqual(rows['instagram']['conversion_percent'], 0)

    def test_old_visitor_is_not_new_when_returning_this_month(self):
        visitor = self.visitor(days=40)
        self.signal(visitor, 'landing_viewed', days_after=39)
        self.pay(visitor, days_after=39)
        report = self.report()
        self.assertEqual(report['visitors'], 0)
        self.assertEqual(report['coverage']['new_payers_in_period'], 1)

    def test_dashboard_requires_model_view_permission(self):
        request = RequestFactory().get('/analytics/')
        request.user = Mock(has_perm=Mock(return_value=False))
        model_admin = PublicWorkoutAcquisitionSessionAdmin(PublicWorkoutAcquisitionSession, AdminSite())
        with self.assertRaises(PermissionDenied):
            model_admin.analytics_view(request)

    def test_cli_exports_aggregate_report(self):
        self.pay(self.visitor())
        output = StringIO()
        call_command('report_public_workout_funnel', days=30, stdout=output)
        data = json.loads(output.getvalue())
        self.assertEqual(data['paid'], 1)
        self.assertNotIn('@example.com', output.getvalue())

    def test_snapshot_rates_and_cac_use_first_payers_not_renewals(self):
        from public_workouts.metrics import build_metrics_snapshot
        from public_workouts.models import PublicWorkoutCampaignSpend
        payer = self.visitor()
        self.pay(payer)
        self.pay(payer, days_after=3)
        for _ in range(4):
            self.signal(payer, 'invoice_paid')
        for index, cost in enumerate(('100', '200')):
            PublicWorkoutCampaignSpend.objects.create(
                source='instagram', campaign='campanha', amount=Decimal(cost),
                starts_on=(self.at - timedelta(days=10 - 5 * index)).date(),
                ends_on=(self.at - timedelta(days=6 - 5 * index)).date(),
            )
        report = build_metrics_snapshot(at=self.at)
        self.assertEqual(report['funnel']['rates']['visitor_to_paid'], 1)
        self.assertEqual(len(report['commercial']['campaign_economics']), 1)
        campaign = report['commercial']['campaign_economics'][0]
        self.assertEqual(campaign['paid_customers'], 1)
        self.assertEqual(campaign['cac'], '300.00')

    def test_dashboard_renders_empty_and_populated_states(self):
        request = RequestFactory().get('/analytics/?days=30')
        request.user = Mock(is_active=True, is_staff=True, has_perm=Mock(return_value=True))
        model_admin = PublicWorkoutAcquisitionSessionAdmin(PublicWorkoutAcquisitionSession, AdminSite())
        empty = model_admin.analytics_view(request).render()
        self.assertContains(empty, 'Ainda não há visitantes')
        self.pay(self.visitor())
        rendered = model_admin.analytics_view(request).render()
        self.assertContains(rendered, 'Primeiro pagamento')
        self.assertContains(rendered, 'instagram')
        self.assertContains(rendered, '100,00')
