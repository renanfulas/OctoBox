from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from public_workouts.models import PublicWorkoutOutboxMessage, PublicWorkoutOutboxStatus
from public_workouts.outbox import drain_public_workout_outbox, enqueue_outbox


class PublicWorkoutOutboxTests(TestCase):
    def _message(self):
        return enqueue_outbox(
            topic='program_ready', aggregate_type='program', aggregate_id=42, version=1,
        )

    def test_enqueue_is_idempotent_per_aggregate_version(self):
        first = self._message()
        second = self._message()

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(PublicWorkoutOutboxMessage.objects.count(), 1)

    @patch('public_workouts.outbox._dispatch', return_value=True)
    def test_successful_delivery_is_marked_sent_once(self, dispatch):
        message = self._message()

        result = drain_public_workout_outbox()
        message.refresh_from_db()

        self.assertEqual(result['sent'], 1)
        self.assertEqual(message.status, PublicWorkoutOutboxStatus.SENT)
        self.assertEqual(message.attempt_count, 1)
        self.assertIsNone(message.processing_started_at)
        self.assertIsNotNone(message.processed_at)
        drain_public_workout_outbox()
        dispatch.assert_called_once()

    @patch('public_workouts.outbox._dispatch', side_effect=RuntimeError('gateway indisponivel'))
    def test_failure_returns_to_pending_with_backoff(self, _dispatch):
        message = self._message()
        before = timezone.now()

        result = drain_public_workout_outbox()
        message.refresh_from_db()

        self.assertEqual(result['retried'], 1)
        self.assertEqual(message.status, PublicWorkoutOutboxStatus.PENDING)
        self.assertGreater(message.next_attempt_at, before)
        self.assertIn('gateway indisponivel', message.last_error)
        self.assertIsNone(message.processing_started_at)

    @patch('public_workouts.outbox._dispatch', return_value=True)
    def test_stale_processing_lease_is_recovered(self, dispatch):
        message = self._message()
        PublicWorkoutOutboxMessage.objects.filter(pk=message.pk).update(
            status=PublicWorkoutOutboxStatus.PROCESSING,
            processing_started_at=timezone.now() - timedelta(minutes=11),
        )

        result = drain_public_workout_outbox()
        message.refresh_from_db()

        self.assertEqual(result['recovered'], 1)
        self.assertEqual(result['sent'], 1)
        self.assertEqual(message.status, PublicWorkoutOutboxStatus.SENT)
        dispatch.assert_called_once()

    @patch('public_workouts.outbox._dispatch', side_effect=RuntimeError('falha permanente'))
    def test_fifth_failure_moves_message_to_dead_letter(self, _dispatch):
        message = self._message()
        PublicWorkoutOutboxMessage.objects.filter(pk=message.pk).update(attempt_count=4)

        result = drain_public_workout_outbox()
        message.refresh_from_db()

        self.assertEqual(result['dead'], 1)
        self.assertEqual(message.status, PublicWorkoutOutboxStatus.DEAD)
        self.assertEqual(message.attempt_count, 5)

