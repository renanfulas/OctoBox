from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from public_workouts.acquisition import ACQUISITION_COOKIE_NAME
from public_workouts.funnel_analytics import build_acquisition_report
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutAcquisitionSession,
    PublicWorkoutFunnelEvent,
    PublicWorkoutPayment,
    PublicWorkoutPaymentStatus,
    PublicWorkoutSubscription,
)


@override_settings(PUBLIC_WORKOUT_FUNNEL_TRACKING_ENABLED=True)
class PublicWorkoutInfluencerAttributionTests(TestCase):
    def test_jully_landing_marks_partner_without_overwriting_campaign_channels(self):
        response = self.client.get(
            reverse('public-workout-landing-jully'),
            {'utm_source': 'instagram', 'utm_medium': 'creator', 'utm_campaign': 'jully'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(ACQUISITION_COOKIE_NAME, response.cookies)
        self.assertContains(response, 'Jully × Curva')
        session = PublicWorkoutAcquisitionSession.objects.get()
        self.assertEqual(session.partner_code, 'jully')
        self.assertIsNotNone(session.partner_first_seen_at)
        self.assertEqual(session.first_source, 'instagram')
        event = PublicWorkoutFunnelEvent.objects.get(event_type='influencer_link_clicked')
        self.assertEqual(event.partner_code, 'jully')

        # Um retorno pela landing geral mantém a indicação e não converte a
        # parceria em uma campanha própria.
        self.client.get(reverse('public-workout-landing'), {'utm_source': 'google'})
        session.refresh_from_db()
        self.assertEqual(session.partner_code, 'jully')
        report = build_acquisition_report(at=timezone.now())
        self.assertEqual(report['channels'], [])
        self.assertEqual(report['influencers'][0]['partner_code'], 'jully')

    def test_influencer_report_counts_only_the_first_paid_invoice(self):
        at = timezone.now()
        first_seen = at - timedelta(days=10)
        account = PublicWorkoutAccount.objects.create(email='jully-customer@example.com')
        subscription = PublicWorkoutSubscription.objects.create(account=account)
        session = PublicWorkoutAcquisitionSession.objects.create(
            account=account,
            subscription=subscription,
            first_seen_at=first_seen,
            partner_code='jully',
            partner_first_seen_at=first_seen,
            first_source='instagram',
            first_medium='creator',
        )
        PublicWorkoutFunnelEvent.objects.create(
            acquisition_session=session,
            event_type='landing_viewed',
            occurred_at=first_seen,
        )
        PublicWorkoutPayment.objects.create(
            subscription=subscription,
            gross_amount=Decimal('100.00'),
            status=PublicWorkoutPaymentStatus.PAID,
            due_date=first_seen.date(),
            paid_at=first_seen + timedelta(days=1),
        )
        PublicWorkoutPayment.objects.create(
            subscription=subscription,
            gross_amount=Decimal('100.00'),
            status=PublicWorkoutPaymentStatus.PAID,
            due_date=(first_seen + timedelta(days=30)).date(),
            paid_at=first_seen + timedelta(days=30),
        )

        report = build_acquisition_report(at=at)

        self.assertEqual(report['channels'], [])
        self.assertEqual(len(report['influencers']), 1)
        self.assertEqual(report['influencers'][0]['paid'], 1)
        self.assertEqual(report['influencers'][0]['revenue'], Decimal('100.00'))
