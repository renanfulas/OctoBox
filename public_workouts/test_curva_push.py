"""L2: inscrição Curva e enfileiramento transacional, sem rede externa."""

from django.test import TestCase, override_settings

from public_workouts.models import (
    PublicWorkoutAccount, PublicWorkoutOutboxMessage, PublicWorkoutPushSubscription,
    PublicWorkoutSubscription,
)
from public_workouts.outbox import TOPIC_PROGRAM_PUSH_READY
from public_workouts.push import configured, subscribe
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
