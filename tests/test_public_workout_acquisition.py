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
    def test_known_crawler_does_not_create_a_visitor(self):
        response = self.client.get(reverse('public-workout-landing'), HTTP_USER_AGENT='Googlebot/2.1')
        self.assertNotIn(ACQUISITION_COOKIE_NAME, response.cookies)
        self.assertFalse(PublicWorkoutAcquisitionSession.objects.exists())
        self.assertFalse(PublicWorkoutFunnelEvent.objects.exists())
        self.assertContains(response, 'data-funnel-enabled="false"')

    def test_staff_navigation_does_not_create_visitor(self):
        from unittest.mock import Mock
        from django.test import RequestFactory
        from public_workouts.acquisition import ensure_acquisition_session
        request = RequestFactory().get('/treinos/')
        request.user = Mock(is_staff=True)
        self.assertEqual(ensure_acquisition_session(request), (None, False))

    def test_event_rate_limit_rejects_excess_without_writing(self):
        from unittest.mock import patch
        self.client.get(reverse('public-workout-landing'))
        with patch('shared_support.platform_cache.platform_cache.add', return_value=False), patch(
            'shared_support.platform_cache.platform_cache.incr', return_value=61,
        ):
            response = self.client.post(reverse('public-workout-funnel-event'),
                data=json.dumps({'event_type': 'cta_clicked', 'client_event_id': str(uuid.uuid4())}),
                content_type='application/json')
        self.assertEqual(response.status_code, 429)
        self.assertFalse(PublicWorkoutFunnelEvent.objects.filter(event_type='cta_clicked').exists())

    def test_rebinding_another_browser_preserves_original_acquisition(self):
        from public_workouts.acquisition import bind_acquisition_session
        from public_workouts.models import PublicWorkoutAccount, PublicWorkoutSubscription
        original = PublicWorkoutAcquisitionSession.objects.create(first_source='instagram')
        returning = PublicWorkoutAcquisitionSession.objects.create(first_source='google')
        account = PublicWorkoutAccount.objects.create(email='returning@example.com')
        subscription = PublicWorkoutSubscription.objects.create(account=account)
        bind_acquisition_session(original, account=account, subscription=subscription)
        result = bind_acquisition_session(returning, account=account, subscription=subscription)
        self.assertEqual(result.pk, original.pk)
        returning.refresh_from_db()
        self.assertIsNone(returning.subscription_id)

    def test_internal_referral_does_not_overwrite_campaign(self):
        self.client.get(reverse('public-workout-landing'), {'utm_source': 'instagram'})
        self.client.get(reverse('public-workout-landing'), HTTP_REFERER='http://testserver/treinos/conta?email=private')
        self.assertEqual(PublicWorkoutAcquisitionSession.objects.get().last_source, 'instagram')

    def test_external_referral_never_stores_path_or_query(self):
        self.client.get(reverse('public-workout-landing'), HTTP_REFERER='https://example.com/private/person?email=test')
        self.assertEqual(PublicWorkoutAcquisitionSession.objects.get().first_referrer, 'https://example.com')

    def test_events_need_a_valid_acquisition_cookie(self):
        response = self.client.post(reverse('public-workout-funnel-event'),
            data=json.dumps({'event_type': 'pricing_viewed', 'client_event_id': str(uuid.uuid4())}),
            content_type='application/json')
        self.assertFalse(response.json()['accepted'])
        self.assertFalse(PublicWorkoutFunnelEvent.objects.exists())

    def test_client_cannot_claim_payment_or_send_unvalidated_tier(self):
        self.client.get(reverse('public-workout-landing'))
        for extra in ({'event_type': 'invoice_paid'}, {'event_type': []}, {'tier': 'private@example.com'}):
            payload = {'event_type': 'signup_started', 'client_event_id': str(uuid.uuid4()), **extra}
            response = self.client.post(reverse('public-workout-funnel-event'), data=json.dumps(payload), content_type='application/json')
            self.assertEqual(response.status_code, 400)

    def test_form_signal_accepts_known_tier_only(self):
        self.client.get(reverse('public-workout-landing'))
        response = self.client.post(reverse('public-workout-funnel-event'),
            data=json.dumps({'event_type': 'signup_started', 'client_event_id': str(uuid.uuid4()), 'tier': 'completo'}),
            content_type='application/json')
        self.assertTrue(response.json()['accepted'])
        self.assertEqual(PublicWorkoutFunnelEvent.objects.get(event_type='signup_started').tier, 'completo')

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
