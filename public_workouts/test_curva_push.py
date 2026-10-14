"""Inscrição, outbox e contrato com o gateway Web Push, sem envio externo."""

import json
from unittest.mock import patch

from django.test import TestCase, override_settings

from public_workouts.models import (
    PublicWorkoutAccount, PublicWorkoutOutboxMessage, PublicWorkoutOutboxStatus, PublicWorkoutPushSubscription,
    PublicWorkoutSubscription,
)
from public_workouts.outbox import TOPIC_PROGRAM_PUSH_READY, TOPIC_PUSH_WELCOME, drain_public_workout_outbox, enqueue_outbox
from public_workouts.push import configured, send as send_push, subscribe
from public_workouts.schema import build_example_payload
from public_workouts.services import publish_program


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

    def test_publishing_program_queues_push_after_device_opt_in(self):
        subscribe(account_id=self.account.pk, data=self.subscription)
        publish_program(slug='bruno', payload=build_example_payload())
        self.assertTrue(PublicWorkoutOutboxMessage.objects.filter(topic=TOPIC_PROGRAM_PUSH_READY).exists())

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
        self.assertEqual(result['retried'], 1)
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
