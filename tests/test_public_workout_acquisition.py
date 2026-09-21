import json
import uuid

from django.test import TestCase, override_settings
from django.urls import reverse

from public_workouts.acquisition import ACQUISITION_COOKIE_NAME
from public_workouts.models import (
    PublicWorkoutAcquisitionSession,
    PublicWorkoutFunnelEvent,
    PublicWorkoutTier,
)


@override_settings(PUBLIC_WORKOUT_FUNNEL_TRACKING_ENABLED=True)
class PublicWorkoutAcquisitionTests(TestCase):
    def test_landing_creates_signed_first_party_session_and_view_event(self):
        response = self.client.get(
            reverse('public-workout-landing'),
            {'utm_source': 'instagram', 'utm_medium': 'paid_social', 'utm_campaign': 'curva-setembro'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(ACQUISITION_COOKIE_NAME, response.cookies)
        session = PublicWorkoutAcquisitionSession.objects.get()
        self.assertEqual(session.first_source, 'instagram')
        self.assertEqual(session.last_source, 'instagram')
        event = PublicWorkoutFunnelEvent.objects.get(event_type='landing_viewed')
        self.assertEqual(event.acquisition_session, session)

    def test_return_visit_preserves_first_touch_and_updates_last_touch(self):
        self.client.get(reverse('public-workout-landing'), {
            'utm_source': 'instagram', 'utm_medium': 'organic', 'utm_campaign': 'first',
        })
        self.client.get(reverse('public-workout-landing'), {
            'utm_source': 'google', 'utm_medium': 'cpc', 'utm_campaign': 'conversion',
        })

        session = PublicWorkoutAcquisitionSession.objects.get()
        self.assertEqual(session.first_source, 'instagram')
        self.assertEqual(session.first_campaign, 'first')
        self.assertEqual(session.last_source, 'google')
        self.assertEqual(session.last_campaign, 'conversion')

    def test_cold_signup_binds_session_and_records_server_side_events(self):
        self.client.get(reverse('public-workout-landing'), {'utm_source': 'indicacao'})
        with self.settings(
            PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL='price_e', STRIPE_SECRET_KEY='sk_test'
        ):
            from unittest.mock import MagicMock, patch

            with patch('stripe.checkout.Session.create') as create:
                create.return_value = MagicMock(url='https://stripe.test/session')
                response = self.client.post(reverse('public-workout-cold-signup'), {
                    'email': 'origem@example.com', 'tier': PublicWorkoutTier.ESSENCIAL,
                    'accept_contract': '1',
                })

        self.assertEqual(response.status_code, 200)
        session = PublicWorkoutAcquisitionSession.objects.select_related('account', 'subscription').get()
        self.assertEqual(session.account.email, 'origem@example.com')
        self.assertEqual(session.subscription.account, session.account)
        self.assertEqual(
            set(PublicWorkoutFunnelEvent.objects.values_list('event_type', flat=True)),
            {'landing_viewed', 'tier_selected', 'checkout_started'},
        )

    def test_tracking_flag_off_does_not_write_or_set_cookie(self):
        with self.settings(PUBLIC_WORKOUT_FUNNEL_TRACKING_ENABLED=False):
            response = self.client.get(reverse('public-workout-landing'), {'utm_source': 'ignored'})

        self.assertNotIn(ACQUISITION_COOKIE_NAME, response.cookies)
        self.assertFalse(PublicWorkoutAcquisitionSession.objects.exists())
        self.assertFalse(PublicWorkoutFunnelEvent.objects.exists())

    def test_client_event_rejects_extra_payload_and_is_idempotent(self):
        self.client.get(reverse('public-workout-landing'))
        event_id = str(uuid.uuid4())
        first = self.client.post(
            reverse('public-workout-funnel-event'),
            data=json.dumps({'event_type': 'cta_clicked', 'client_event_id': event_id}),
            content_type='application/json',
        )
        second = self.client.post(
            reverse('public-workout-funnel-event'),
            data=json.dumps({'event_type': 'cta_clicked', 'client_event_id': event_id}),
            content_type='application/json',
        )
        rejected = self.client.post(
            reverse('public-workout-funnel-event'),
            data=json.dumps({
                'event_type': 'cta_clicked', 'client_event_id': str(uuid.uuid4()),
                'email': 'nao-pode@example.com',
            }),
            content_type='application/json',
        )

        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 202)
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(PublicWorkoutFunnelEvent.objects.filter(event_type='cta_clicked').count(), 1)
