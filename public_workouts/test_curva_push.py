"""Inscrição, outbox e contrato com o gateway Web Push, sem envio externo."""

from datetime import timedelta
from decimal import Decimal
import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from public_workouts.models import (
    PublicWorkoutAccount, PublicWorkoutOutboxMessage, PublicWorkoutOutboxStatus, PublicWorkoutPushSubscription,
    PublicWorkoutLoginToken, PublicWorkoutSubscription,
)
from public_workouts.outbox import (
    TOPIC_PROGRAM_PUSH_READY, TOPIC_PUSH_WELCOME, TOPIC_TRAINING_COMPLETED,
    _dispatch, drain_public_workout_outbox, enqueue_outbox,
)
from public_workouts.push import configured, send as send_push, subscribe
from public_workouts.schema import build_example_payload
from public_workouts.services import publish_program
from public_workouts.training_sessions import finish_session, record_set, start_session


@override_settings(
    STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY='test-public',
    STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY='test-private',
    STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT='mailto:test@example.com',
    PUBLIC_WORKOUT_PUSH_ALLOWED_HOSTS='fcm.googleapis.com',
)
class CurvaPushIntegrationTest(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='push-curva@example.test')
        PublicWorkoutSubscription.objects.create(account=self.account, plan_slug='bruno')
        self.subscription = {
            'endpoint': 'https://fcm.googleapis.com/fcm/send/device-1',
            'keys': {'p256dh': 'public-device-key', 'auth': 'auth-device-key'},
        }

    def test_device_opt_in_is_scoped_to_account_and_reusable(self):
        self.assertTrue(configured())
        first = subscribe(account_id=self.account.pk, data=self.subscription)
        again = subscribe(account_id=self.account.pk, data=self.subscription)
        self.assertEqual(first.pk, again.pk)
        self.assertEqual(PublicWorkoutPushSubscription.objects.filter(account=self.account).count(), 1)

    def test_link_possession_cannot_bind_push_device_to_legacy_owner(self):
        publish_program(slug='bruno', payload=build_example_payload())
        page = self.client.get('/renan/bruno')
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'Entrar para ativar')
        self.assertNotContains(page, 'data-workout-push-enable')

        response = self.client.post(
            reverse('public-workout-push', kwargs={'plan_slug': 'bruno'}),
            data=json.dumps({'subscription': self.subscription}), content_type='application/json',
        )
        self.assertEqual(response.status_code, 401)
        self.assertFalse(PublicWorkoutPushSubscription.objects.exists())

    def test_verified_login_can_activate_push_for_owned_plan(self):
        publish_program(slug='bruno', payload=build_example_payload())
        token = PublicWorkoutLoginToken.objects.create(
            account=self.account, expires_at=timezone.now() + timedelta(minutes=15),
        )
        login = self.client.get(reverse('public-workout-login'), {
            'token': str(token.token), 'next': '/renan/bruno',
        })
        self.assertEqual(login.status_code, 302)
        page = self.client.get('/renan/bruno')
        self.assertContains(page, 'data-workout-push-enable')
        self.assertContains(page, 'data-workout-push-profile-enable')
        self.assertContains(page, 'data-workout-push-disable')
        self.assertContains(page, 'data-workout-install-status')
        self.assertContains(page, 'data-workout-push-home')

        response = self.client.post(
            reverse('public-workout-push', kwargs={'plan_slug': 'bruno'}),
            data=json.dumps({'subscription': self.subscription}), content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PublicWorkoutPushSubscription.objects.filter(account=self.account).count(), 1)

    def test_publishing_program_queues_push_after_device_opt_in(self):
        subscribe(account_id=self.account.pk, data=self.subscription)
        publish_program(slug='bruno', payload=build_example_payload())
        self.assertTrue(PublicWorkoutOutboxMessage.objects.filter(topic=TOPIC_PROGRAM_PUSH_READY).exists())

    @override_settings(PUBLIC_WORKOUT_PUBLIC_BASE_URL='https://curva.example.test')
    @patch('public_workouts.push.notify_account', return_value=True)
    def test_real_completion_queues_one_account_scoped_notification(self, notify):
        subscribe(account_id=self.account.pk, data=self.subscription)
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['guided_prescription'] = {
            'version': 1, 'stages': [
                {'stage_id': 'top', 'role': 'top_set', 'min_sets': 1, 'max_sets': 1,
                 'reps_min': 6, 'reps_max': 8, 'rest_seconds': 90,
                 'load_rule': {'kind': 'suggested_top'}},
            ],
        }
        publish_program(slug='bruno', payload=payload)
        session = start_session(account_id=self.account.pk, plan_slug='bruno', day_id='seg')
        record_set(
            account_id=self.account.pk, plan_slug='bruno', session_id=session.pk,
            movement_index=0, set_number=1, movement_slug='agachamento-livre',
            role='top_set', weight=Decimal('50.00'), reps=7, rir=None,
        )
        finish_session(account_id=self.account.pk, plan_slug='bruno', session_id=session.pk)
        finish_session(account_id=self.account.pk, plan_slug='bruno', session_id=session.pk)
        messages = PublicWorkoutOutboxMessage.objects.filter(
            topic=TOPIC_TRAINING_COMPLETED, aggregate_id=str(session.pk),
        )
        self.assertEqual(messages.count(), 1)
        self.assertTrue(_dispatch(messages.get()))
        self.assertEqual(notify.call_args.kwargs['account_id'], self.account.pk)
        self.assertEqual(notify.call_args.kwargs['url'], 'https://curva.example.test/renan/bruno')

    def test_other_account_cannot_claim_live_device(self):
        subscribe(account_id=self.account.pk, data=self.subscription)
        other = PublicWorkoutAccount.objects.create(email='push-other@example.test')
        with self.assertRaises(ValueError):
            subscribe(account_id=other.pk, data=self.subscription)

    @override_settings(STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY='')
    def test_push_message_is_retained_if_credentials_are_missing_at_dispatch(self):
        device = subscribe(account_id=self.account.pk, data=self.subscription)
        message = enqueue_outbox(
            topic=TOPIC_PUSH_WELCOME, aggregate_type='push_subscription',
            aggregate_id=device.pk, version=1, payload={'plan_slug': 'bruno'},
        )
        result = drain_public_workout_outbox()
        message.refresh_from_db()
        # O banco de testes pode conter outras mensagens pendentes criadas
        # pelo seed; a garantia é sobre esta mensagem, não o lote inteiro.
        self.assertGreaterEqual(result['retried'], 1)
        self.assertEqual(message.status, PublicWorkoutOutboxStatus.PENDING)
        self.assertIn('push nao configurado', message.last_error)

    @override_settings(PUBLIC_WORKOUT_PUBLIC_BASE_URL='https://curva.example.test')
    @patch('public_workouts.push.send', return_value=True)
    def test_welcome_dispatch_targets_only_enrolled_test_device(self, send):
        device = subscribe(account_id=self.account.pk, data=self.subscription)
        message = enqueue_outbox(
            topic=TOPIC_PUSH_WELCOME, aggregate_type='push_subscription',
            aggregate_id=device.pk, version=1, payload={'plan_slug': 'bruno'},
        )
        result = drain_public_workout_outbox()
        message.refresh_from_db()
        self.assertEqual(result['sent'], 1)
        self.assertEqual(message.status, PublicWorkoutOutboxStatus.SENT)
        self.assertEqual(send.call_args.kwargs['subscription'].pk, device.pk)
        self.assertEqual(send.call_args.kwargs['url'], 'https://curva.example.test/renan/bruno')

    @patch('student_identity.push_notifications._build_vapid_private_key', return_value='test-pem')
    @patch('pywebpush.webpush')
    def test_gateway_receives_notification_payload_and_marks_device_sent(self, gateway, _private_key):
        device = subscribe(account_id=self.account.pk, data=self.subscription)
        self.assertTrue(send_push(
            subscription=device, title='Treino concluído', body='Seu treino foi salvo.',
            url='https://curva.example.test/renan/bruno', tag='training-test',
        ))
        payload = json.loads(gateway.call_args.kwargs['data'])
        self.assertEqual(payload['tag'], 'training-test')
        self.assertEqual(payload['url'], 'https://curva.example.test/renan/bruno')
        self.assertEqual(gateway.call_args.kwargs['subscription_info'], self.subscription)
        device.refresh_from_db()
        self.assertIsNotNone(device.last_push_sent_at)
