from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from public_workouts.acquisition import ACQUISITION_COOKIE_NAME
from public_workouts.funnel_analytics import build_acquisition_report, build_influencer_report
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutAcquisitionSession,
    PublicWorkoutFunnelEvent,
    PublicWorkoutPayment,
    PublicWorkoutPaymentStatus,
    PublicWorkoutStaffCredential,
    PublicWorkoutSubscription,
)


@override_settings(PUBLIC_WORKOUT_FUNNEL_TRACKING_ENABLED=True)
class PublicWorkoutInfluencerAnalyticsTests(TestCase):
    def test_jully_landing_sets_partner_attribution_and_does_not_assign_experiment(self):
        response = self.client.get(
            reverse('public-workout-landing-jully'),
            {'utm_source': 'instagram', 'utm_campaign': 'jully'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(ACQUISITION_COOKIE_NAME, response.cookies)
        self.assertContains(response, 'Jully × Curva')
        self.assertContains(response, 'data-partner-code="jully"')
        session = PublicWorkoutAcquisitionSession.objects.get()
        self.assertEqual(session.partner_code, 'jully')
        self.assertIsNotNone(session.partner_first_seen_at)
        self.assertEqual(session.first_source, 'instagram')
        self.assertEqual(
            set(PublicWorkoutFunnelEvent.objects.values_list('event_type', flat=True)),
            {'landing_viewed', 'influencer_link_clicked'},
        )
        self.assertEqual(PublicWorkoutFunnelEvent.objects.get(
            event_type='influencer_link_clicked',
        ).partner_code, 'jully')

    def test_influencer_traffic_is_excluded_from_own_acquisition_report(self):
        self.client.get(reverse('public-workout-landing-jully'), {'utm_source': 'instagram'})
        self.client.get(reverse('public-workout-landing'), {'utm_source': 'google'})
        self.assertEqual(
            PublicWorkoutAcquisitionSession.objects.get().partner_code,
            'jully',
        )
        own_browser = self.client_class()
        own_browser.get(reverse('public-workout-landing'), {'utm_source': 'google'})

        report = build_acquisition_report(at=timezone.now())

        self.assertEqual(report['visitors'], 1)
        self.assertEqual([row['source'] for row in report['channels']], ['google'])

    def test_jully_attribution_survives_signup_and_checkout_creation(self):
        from unittest.mock import MagicMock, patch

        from public_workouts.models import PublicWorkoutTier

        self.client.get(reverse('public-workout-landing-jully'))
        with self.settings(
            PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL='price_e', STRIPE_SECRET_KEY='sk_test'
        ), patch('stripe.checkout.Session.create') as create:
            create.return_value = MagicMock(url='https://stripe.test/session')
            response = self.client.post(reverse('public-workout-cold-signup'), {
                'email': 'jully-checkout@example.com',
                'tier': PublicWorkoutTier.ESSENCIAL,
                'accept_contract': '1',
            })

        self.assertEqual(response.status_code, 200)
        session = PublicWorkoutAcquisitionSession.objects.select_related('subscription').get()
        self.assertEqual(session.partner_code, 'jully')
        self.assertIsNotNone(session.subscription_id)
        self.assertEqual(
            set(PublicWorkoutFunnelEvent.objects.values_list('partner_code', flat=True)),
            {'jully'},
        )

    def test_jully_report_counts_one_paid_invoice_and_estimates_only_one_time_commission(self):
        at = timezone.now()
        partner_seen = at - timedelta(days=10)
        account = PublicWorkoutAccount.objects.create(email='jully-report@example.com')
        subscription = PublicWorkoutSubscription.objects.create(account=account)
        session = PublicWorkoutAcquisitionSession.objects.create(
            account=account,
            subscription=subscription,
            partner_code='jully',
            partner_first_seen_at=partner_seen,
            first_seen_at=partner_seen,
        )
        for event_type, occurred_at in (
            ('landing_viewed', partner_seen),
            ('influencer_link_clicked', partner_seen),
            ('signup_submitted', partner_seen + timedelta(hours=1)),
            ('checkout_started', partner_seen + timedelta(hours=2)),
        ):
            PublicWorkoutFunnelEvent.objects.create(
                acquisition_session=session,
                partner_code='jully',
                event_type=event_type,
                occurred_at=occurred_at,
            )
        for days_after in (1, 8):
            PublicWorkoutPayment.objects.create(
                subscription=subscription,
                gross_amount=Decimal('100.00'),
                status=PublicWorkoutPaymentStatus.PAID,
                due_date=(partner_seen + timedelta(days=days_after)).date(),
                paid_at=partner_seen + timedelta(days=days_after),
            )

        report = build_influencer_report(partner_code='jully', at=at)

        self.assertEqual(report['clicks'], 1)
        self.assertEqual(report['visitors'], 1)
        self.assertEqual(report['signups'], 1)
        self.assertEqual(report['checkouts'], 1)
        self.assertEqual(report['paid'], 1)
        self.assertEqual(report['revenue'], Decimal('100.00'))
        self.assertEqual(report['commission_estimate'], Decimal('60.00'))

    def test_jully_dashboard_uses_internal_analytics_authentication(self):
        PublicWorkoutStaffCredential.objects.create(
            username='analytics-jully-test',
            password_hash=make_password('test-only-password'),
            is_active=True,
        )
        url = reverse('public-workout-influencer-analytics-jully')

        denied = self.client.get(url)
        self.assertRedirects(denied, reverse('public-workout-funnel-analytics-login'))

        login = self.client.post(reverse('public-workout-funnel-analytics-login'), {
            'username': 'analytics-jully-test',
            'password': 'test-only-password',
        })
        self.assertRedirects(login, reverse('public-workout-funnel-analytics'))
        page = self.client.get(url)
        self.assertContains(page, 'Comissão estimada')
        self.assertContains(page, 'não registra saldo nem faz repasse')
        report = self.client.get(url, {'format': 'json'}).json()
        self.assertEqual(report['partner_code'], 'jully')
