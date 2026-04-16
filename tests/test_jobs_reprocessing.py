"""
ARQUIVO: testes do reprocessamento programado de jobs.

POR QUE ELE EXISTE:
- garante que jobs vencidos por `next_retry_at` entrem no corredor oficial da malha.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from jobs.reprocessing import reprocess_due_async_jobs


class JobsReprocessingTests(SimpleTestCase):
    @patch('jobs.reprocessing.record_retry_sweep')
    @patch('jobs.reprocessing.get_alert_siren_defense_policy')
    @patch('jobs.reprocessing.dispatch_async_job')
    @patch('jobs.reprocessing.AsyncJob.objects.filter')
    def test_reprocess_due_async_jobs_caps_flow_when_alert_siren_requests_containment(
        self,
        async_job_filter_mock,
        dispatch_mock,
        defense_policy_mock,
        record_retry_sweep_mock,
    ):
        job_one = SimpleNamespace(
            id=17,
            job_type='student_import_csv',
            result={'dispatch_context': {'job_type': 'student_import_csv'}},
            next_retry_at=datetime(2026, 4, 16, 12, 0, tzinfo=timezone.utc),
        )
        job_two = SimpleNamespace(
            id=18,
            job_type='student_import_csv',
            result={'dispatch_context': {'job_type': 'student_import_csv'}},
            next_retry_at=datetime(2026, 4, 16, 12, 0, tzinfo=timezone.utc),
        )
        job_one.mark_retry_dispatched = lambda result=None: None
        job_two.mark_retry_dispatched = lambda result=None: None
        defense_policy_mock.return_value = {
            'level': 'medium',
            'job_limit_cap': 1,
            'pause_webhook_retries': False,
        }
        queryset_mock = async_job_filter_mock.return_value
        queryset_mock.count.return_value = 2
        queryset_mock.order_by.return_value.__getitem__.side_effect = lambda item: [job_one] if getattr(item, 'stop', 0) == 1 else [job_one, job_two]
        dispatch_mock.return_value = SimpleNamespace(id='task-17')

        result = reprocess_due_async_jobs(
            limit=10,
            now=datetime(2026, 4, 16, 12, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(result['dispatched_count'], 1)
        self.assertEqual(result['effective_limit'], 1)
        record_retry_sweep_mock.assert_called_once()

    @patch('jobs.reprocessing.record_retry_sweep')
    @patch('jobs.reprocessing.get_alert_siren_defense_policy')
    @patch('jobs.reprocessing.dispatch_async_job')
    @patch('jobs.reprocessing.AsyncJob.objects.filter')
    def test_reprocess_due_async_jobs_dispatches_due_jobs(self, async_job_filter_mock, dispatch_mock, defense_policy_mock, record_retry_sweep_mock):
        due_job = SimpleNamespace(
            id=17,
            job_type='student_import_csv',
            result={'dispatch_context': {'job_type': 'student_import_csv'}},
            next_retry_at=datetime(2026, 4, 16, 12, 0, tzinfo=timezone.utc),
        )
        due_job.mark_retry_dispatched = lambda result=None: None
        defense_policy_mock.return_value = {
            'level': 'silent',
            'job_limit_cap': None,
            'pause_webhook_retries': False,
        }
        async_job_filter_mock.return_value.count.return_value = 1
        async_job_filter_mock.return_value.order_by.return_value.__getitem__.return_value = [due_job]
        dispatch_mock.return_value = SimpleNamespace(id='task-17')

        result = reprocess_due_async_jobs(
            limit=10,
            now=datetime(2026, 4, 16, 12, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(result['dispatched_count'], 1)
        self.assertEqual(result['dispatched'][0]['job_id'], 17)
        self.assertEqual(result['dispatched'][0]['task_id'], 'task-17')
        record_retry_sweep_mock.assert_called_once()

    @patch('jobs.reprocessing.record_retry_sweep')
    @patch('jobs.reprocessing.get_alert_siren_defense_policy')
    @patch('jobs.reprocessing.AsyncJob.objects.filter')
    def test_reprocess_due_async_jobs_skips_job_without_dispatch_context(self, async_job_filter_mock, defense_policy_mock, record_retry_sweep_mock):
        due_job = SimpleNamespace(
            id=18,
            job_type='student_import_csv',
            result={},
            next_retry_at=datetime(2026, 4, 16, 12, 0, tzinfo=timezone.utc),
        )
        defense_policy_mock.return_value = {
            'level': 'silent',
            'job_limit_cap': None,
            'pause_webhook_retries': False,
        }
        async_job_filter_mock.return_value.count.return_value = 1
        async_job_filter_mock.return_value.order_by.return_value.__getitem__.return_value = [due_job]

        result = reprocess_due_async_jobs(
            limit=10,
            now=datetime(2026, 4, 16, 12, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(result['dispatched_count'], 0)
        self.assertEqual(result['skipped'][0]['reason'], 'missing-dispatch-context')
        record_retry_sweep_mock.assert_called_once()
