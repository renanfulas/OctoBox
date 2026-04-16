"""
ARQUIVO: testes do smoke operacional pre-VPS.

POR QUE ELE EXISTE:
- garante que o checklist executavel do deploy continue cobrindo dashboard, AsyncJob, Beacon e sweeps.
"""

from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import SimpleTestCase


class PreVpsOperationalSmokeCommandTests(SimpleTestCase):
    @patch('shared_support.management.commands.run_pre_vps_operational_smoke.reprocess_due_webhook_events')
    @patch('shared_support.management.commands.run_pre_vps_operational_smoke.reprocess_due_async_jobs')
    @patch('shared_support.management.commands.run_pre_vps_operational_smoke.AsyncJob.objects.get')
    @patch('shared_support.management.commands.run_pre_vps_operational_smoke.AsyncJob.objects.create')
    @patch('shared_support.management.commands.run_pre_vps_operational_smoke.build_red_beacon_snapshot')
    @patch('shared_support.management.commands.run_pre_vps_operational_smoke.build_dashboard_snapshot')
    def test_command_runs_operational_smoke_suite(
        self,
        build_dashboard_snapshot_mock,
        build_red_beacon_snapshot_mock,
        async_job_create_mock,
        async_job_get_mock,
        reprocess_due_async_jobs_mock,
        reprocess_due_webhook_events_mock,
    ):
        build_dashboard_snapshot_mock.return_value = {
            'red_beacon_snapshot': {
                'label': 'Red Beacon',
                'alert_siren': {'level': 'silent'},
            }
        }
        build_red_beacon_snapshot_mock.return_value = {
            'signal_mesh': {'total_due_backlog': 0},
        }
        smoke_job = MagicMock(id=91)
        async_job_create_mock.return_value = smoke_job
        async_job_get_mock.return_value = MagicMock(id=91, status='pending', job_type='smoke_test')
        reprocess_due_async_jobs_mock.return_value = {'dispatched_count': 0, 'skipped_count': 0}
        reprocess_due_webhook_events_mock.return_value = {'processed_count': 0, 'skipped_count': 0}
        stdout = StringIO()

        call_command('run_pre_vps_operational_smoke', stdout=stdout)

        self.assertIn('dashboard_red_beacon=Red Beacon', stdout.getvalue())
        self.assertIn('asyncjob_create_ok id=91', stdout.getvalue())
        self.assertIn('Pre-VPS smoke test operacional concluido.', stdout.getvalue())
        smoke_job.delete.assert_called_once()
