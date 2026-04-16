"""
ARQUIVO: testes da propagacao do SignalEnvelope nos tasks de operations.

POR QUE ELE EXISTE:
- protege o rastro da malha ao entrar no worker assincrono.
"""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from operations.tasks import run_csv_student_import_job


class OperationsTasksTests(SimpleTestCase):
    @patch('operations.tasks.os.remove')
    @patch('operations.tasks.StudentImporter')
    @patch('operations.tasks.AsyncJob.objects.filter')
    def test_run_csv_student_import_job_returns_signal_envelope_payload(
        self,
        async_job_filter_mock,
        student_importer_mock,
        os_remove_mock,
    ):
        async_job_filter_mock.return_value.first.return_value = None
        student_importer_mock.return_value.import_from_file.return_value = {'imported': 3}
        envelope = {
            'correlation_id': 'corr-task-1',
            'idempotency_key': 'idem-task-1',
            'source_channel': 'api.v1.jobs',
            'occurred_at': '2026-04-16T12:00:00+00:00',
            'raw_reference': 'upload:students.csv',
        }

        result = run_csv_student_import_job(
            None,
            file_path='C:\\temp\\octobox_import_students.csv',
            actor_id=7,
            job_id=None,
            signal_envelope=envelope,
        )

        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['signal_envelope']['correlation_id'], 'corr-task-1')
        self.assertEqual(result['signal_envelope']['idempotency_key'], 'idem-task-1')
        os_remove_mock.assert_called_once()

    def test_already_running_payload_is_classified_as_duplicate(self):
        from operations.tasks import _build_already_running_payload, _hydrate_signal_envelope

        payload = _build_already_running_payload(
            envelope=_hydrate_signal_envelope(
                {
                    'correlation_id': 'corr-task-2',
                    'idempotency_key': 'idem-task-2',
                    'source_channel': 'api.v1.jobs',
                    'occurred_at': '2026-04-16T12:00:00+00:00',
                    'raw_reference': 'upload:students.csv',
                },
                fallback_source_channel='operations.student_import',
            )
        )

        self.assertEqual(payload['failure_kind'], 'duplicate')
        self.assertFalse(payload['retryable'])

    def test_failed_payload_schedules_retry_when_attempt_budget_remains(self):
        from operations.tasks import _build_failed_job_payload, _hydrate_signal_envelope

        payload = _build_failed_job_payload(
            envelope=_hydrate_signal_envelope(
                {
                    'correlation_id': 'corr-task-3',
                    'idempotency_key': 'idem-task-3',
                    'source_channel': 'api.v1.jobs',
                    'occurred_at': '2026-04-16T12:00:00+00:00',
                    'raw_reference': 'upload:students.csv',
                },
                fallback_source_channel='operations.student_import',
            ),
            error=RuntimeError('boom'),
            attempts=0,
            max_attempts=3,
        )

        self.assertEqual(payload['failure_kind'], 'retryable')
        self.assertEqual(payload['retry_action'], 'retry')
        self.assertEqual(payload['attempt_number'], 1)
        self.assertEqual(payload['max_attempts'], 3)
        self.assertTrue(payload['next_retry_at'])
