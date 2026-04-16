"""
ARQUIVO: testes da retry policy minima da Signal Mesh.

POR QUE ELE EXISTE:
- protege a decisao canonica entre reprocessar, conter ou desistir.
"""

from datetime import datetime, timezone

from django.test import SimpleTestCase

from integrations.mesh import (
    RETRY_ACTION_CONTAIN,
    RETRY_ACTION_GIVE_UP,
    RETRY_ACTION_RETRY,
    build_backoff_delay_seconds,
    decide_retry,
)


class IntegrationsMeshRetryPolicyTests(SimpleTestCase):
    def test_build_backoff_delay_seconds_grows_exponentially(self):
        self.assertEqual(build_backoff_delay_seconds(attempt_number=1, base_delay_seconds=10), 10)
        self.assertEqual(build_backoff_delay_seconds(attempt_number=2, base_delay_seconds=10), 20)
        self.assertEqual(build_backoff_delay_seconds(attempt_number=3, base_delay_seconds=10), 40)

    def test_retryable_failure_schedules_next_attempt(self):
        decision = decide_retry(
            failure_kind='retryable',
            attempts=0,
            max_attempts=3,
            reason='timeout',
            now=datetime(2026, 4, 16, 12, 0, tzinfo=timezone.utc),
            base_delay_seconds=10,
        )

        self.assertEqual(decision.action, RETRY_ACTION_RETRY)
        self.assertTrue(decision.should_retry)
        self.assertEqual(decision.attempt_number, 1)
        self.assertEqual(decision.max_attempts, 3)
        self.assertEqual(decision.delay_seconds, 10)
        self.assertIsNotNone(decision.next_retry_at)

    def test_duplicate_failure_is_contained(self):
        decision = decide_retry(
            failure_kind='duplicate',
            attempts=1,
            max_attempts=3,
            reason='duplicate-event',
        )

        self.assertEqual(decision.action, RETRY_ACTION_CONTAIN)
        self.assertFalse(decision.should_retry)
        self.assertTrue(decision.terminal)

    def test_non_retryable_failure_gives_up(self):
        decision = decide_retry(
            failure_kind='invalid_payload',
            attempts=0,
            max_attempts=3,
            reason='invalid-json',
        )

        self.assertEqual(decision.action, RETRY_ACTION_GIVE_UP)
        self.assertFalse(decision.should_retry)

    def test_retryable_failure_gives_up_after_budget_exhausted(self):
        decision = decide_retry(
            failure_kind='retryable',
            attempts=2,
            max_attempts=3,
            reason='timeout',
        )

        self.assertEqual(decision.action, RETRY_ACTION_GIVE_UP)
        self.assertFalse(decision.should_retry)
