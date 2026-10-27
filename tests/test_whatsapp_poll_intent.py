"""PostgreSQL integration coverage for tenant-local WhatsApp poll intents."""

from unittest.mock import patch

from django.db import connection
from django.test import TestCase, override_settings
from django.utils import timezone
from django_tenants.utils import schema_context

from integrations.whatsapp.contracts import WhatsAppInboundPollVote
from integrations.whatsapp.models import WhatsAppPollWebhookIntent
from integrations.whatsapp.poll_processor import process_poll_vote_webhook
from operations.model_definitions import Attendance, ClassSession, ClassType
from students.model_definitions import Student


@override_settings(PHONE_BLIND_INDEX_KEY='test-whatsapp-poll-blind-index')
class WhatsAppPollIntentProcessingTests(TestCase):
    def setUp(self):
        self.now = timezone.now().replace(second=0, microsecond=0)
        self.phone = '+5511998765432'
        self.student = Student.objects.create(full_name='Poll Test Student', phone=self.phone)
        session_start = timezone.localtime(self.now).replace(minute=20, second=0, microsecond=0)
        self.session = ClassSession.objects.create(
            title='CrossFit',
            class_type=ClassType.CROSS,
            scheduled_at=session_start,
        )
        self.vote = WhatsAppInboundPollVote(
            phone=self.phone,
            poll_title='Check-in',
            option_voted=f'{session_start.hour}h',
            event_id='evt-poll-integration-1',
            external_id='evt-poll-integration-1',
        )

    def test_processing_is_atomic_and_replay_does_not_duplicate_attendance(self):
        first = process_poll_vote_webhook(
            poll_vote=self.vote,
            tenant_schema='box_test',
            now=self.now,
        )
        replay = process_poll_vote_webhook(
            poll_vote=self.vote,
            tenant_schema='box_test',
            now=self.now,
        )

        self.assertTrue(first.accepted)
        self.assertTrue(replay.accepted)
        self.assertEqual(replay.failure_kind, 'duplicate')
        self.assertEqual(Attendance.objects.filter(student=self.student, session=self.session).count(), 1)
        self.assertEqual(
            WhatsAppPollWebhookIntent.objects.filter(
                provider='evolution', event_id=self.vote.event_id,
                status=WhatsAppPollWebhookIntent.Status.PROCESSED,
            ).count(),
            1,
        )

    def test_same_event_id_with_different_body_is_contained(self):
        first = process_poll_vote_webhook(
            poll_vote=self.vote,
            tenant_schema='box_test',
            now=self.now,
        )
        conflicting_vote = WhatsAppInboundPollVote(
            phone='+5511990000000',
            poll_title=self.vote.poll_title,
            option_voted=self.vote.option_voted,
            event_id=self.vote.event_id,
            external_id=self.vote.event_id,
        )
        conflict = process_poll_vote_webhook(
            poll_vote=conflicting_vote,
            tenant_schema='box_test',
            now=self.now,
        )

        self.assertTrue(first.accepted)
        self.assertFalse(conflict.accepted)
        self.assertEqual(conflict.reason, 'event-payload-conflict')
        self.assertEqual(Attendance.objects.filter(student=self.student, session=self.session).count(), 1)

    def test_encrypted_phone_is_tenant_local_and_not_stored_in_plaintext(self):
        process_poll_vote_webhook(
            poll_vote=self.vote,
            tenant_schema='box_test',
            now=self.now,
        )

        with schema_context('box_test'):
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT phone FROM boxcore_whatsapp_poll_intent WHERE event_id = %s',
                    [self.vote.event_id],
                )
                stored_phone = cursor.fetchone()[0]
        self.assertNotEqual(stored_phone, self.phone)
        self.assertEqual(
            WhatsAppPollWebhookIntent.objects.get(event_id=self.vote.event_id).phone,
            self.phone,
        )

    @patch('integrations.whatsapp.poll_processor.generate_blind_index', return_value='')
    def test_missing_blind_index_fails_closed_without_attendance(self, _blind_index):
        result = process_poll_vote_webhook(
            poll_vote=self.vote,
            tenant_schema='box_test',
            now=self.now,
        )

        self.assertFalse(result.accepted)
        self.assertEqual(result.reason, 'phone-lookup-unavailable')
        self.assertEqual(Attendance.objects.filter(student=self.student, session=self.session).count(), 0)
