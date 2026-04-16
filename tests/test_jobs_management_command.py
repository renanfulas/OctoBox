"""
ARQUIVO: testes do comando operacional de retry de jobs.

POR QUE ELE EXISTE:
- protege a ligacao entre o corredor oficial da malha e o scheduler institucional.
"""

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings


class JobsManagementCommandTests(SimpleTestCase):
    @patch('jobs.management.commands.run_due_async_job_retries.reprocess_due_async_jobs')
    @override_settings(JOB_RETRY_SWEEP_LIMIT=13)
    def test_run_due_async_job_retries_uses_configured_default_limit(self, reprocess_mock):
        reprocess_mock.return_value = {'dispatched_count': 2, 'skipped_count': 1}
        stdout = StringIO()

        call_command('run_due_async_job_retries', stdout=stdout)

        reprocess_mock.assert_called_once_with(limit=13)
        self.assertIn('Jobs reprocessados: 2 disparados, 1 ignorados.', stdout.getvalue())

    @patch('jobs.management.commands.run_due_async_job_retries.reprocess_due_async_jobs')
    def test_run_due_async_job_retries_accepts_explicit_limit(self, reprocess_mock):
        reprocess_mock.return_value = {'dispatched_count': 1, 'skipped_count': 0}
        stdout = StringIO()

        call_command('run_due_async_job_retries', limit=7, stdout=stdout)

        reprocess_mock.assert_called_once_with(limit=7)
