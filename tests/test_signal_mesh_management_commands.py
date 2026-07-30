"""
ARQUIVO: testes dos comandos operacionais da Signal Mesh.

POR QUE ELE EXISTE:
- protege a ligacao entre scheduler explicito, jobs e webhooks.

PONTOS CRITICOS:
- a perna de `AsyncJob` do sweep e TENANT e passa por `sweep_active_tenants`,
  que consulta `Box` (banco). Estes testes continuam `SimpleTestCase` (sem DB)
  fingindo a varredura com `_fake_sweep`, que executa o handler exatamente uma
  vez — equivalente a um unico box ativo.
"""

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

from shared_support.tenant_sweep import TenantSweepResult


def _fake_sweep(handler, *, only_schema='', raise_on_error=False):
    """Simula uma varredura com um unico box ativo, sem tocar no banco."""
    fake_box = type('Box', (), {'schema_name': 'box_test'})()
    return TenantSweepResult(
        schemas_touched=1,
        results=[('box_test', handler(fake_box))],
    )


class SignalMeshManagementCommandsTests(SimpleTestCase):
    @patch('integrations.management.commands.run_due_webhook_retries.reprocess_due_webhook_events')
    @override_settings(WEBHOOK_RETRY_SWEEP_LIMIT=9)
    def test_run_due_webhook_retries_uses_configured_default_limit(self, reprocess_mock):
        reprocess_mock.return_value = {'processed_count': 2, 'skipped_count': 1}
        stdout = StringIO()

        call_command('run_due_webhook_retries', stdout=stdout)

        reprocess_mock.assert_called_once_with(limit=9)
        self.assertIn('Webhooks reprocessados: 2 processados, 1 ignorados.', stdout.getvalue())

    @patch('shared_support.management.commands.run_signal_mesh_retry_sweep.sweep_active_tenants', _fake_sweep)
    @patch('shared_support.management.commands.run_signal_mesh_retry_sweep.reprocess_due_stripe_webhook_events')
    @patch('shared_support.management.commands.run_signal_mesh_retry_sweep.reprocess_due_webhook_events')
    @patch('shared_support.management.commands.run_signal_mesh_retry_sweep.reprocess_due_async_jobs')
    def test_run_signal_mesh_retry_sweep_runs_all_corridors(self, jobs_mock, webhooks_mock, stripe_mock):
        jobs_mock.return_value = {'dispatched_count': 3, 'skipped_count': 1}
        webhooks_mock.return_value = {'processed_count': 4, 'skipped_count': 2}
        stripe_mock.return_value = {'processed_count': 5, 'skipped_count': 0}
        stdout = StringIO()

        call_command(
            'run_signal_mesh_retry_sweep',
            job_limit=7,
            webhook_limit=11,
            stripe_limit=13,
            stdout=stdout,
        )

        jobs_mock.assert_called_once_with(limit=7)
        webhooks_mock.assert_called_once_with(limit=11)
        stripe_mock.assert_called_once_with(limit=13)
        self.assertIn(
            'jobs=3 disparados/1 ignorados, webhooks=4 processados/2 ignorados, '
            'stripe=5 processados/0 ignorados.',
            stdout.getvalue(),
        )

    @patch('shared_support.management.commands.run_signal_mesh_retry_sweep.sweep_active_tenants', _fake_sweep)
    @patch('shared_support.management.commands.run_signal_mesh_retry_sweep.reprocess_due_stripe_webhook_events')
    @patch('shared_support.management.commands.run_signal_mesh_retry_sweep.reprocess_due_webhook_events')
    @patch('shared_support.management.commands.run_signal_mesh_retry_sweep.reprocess_due_async_jobs')
    @override_settings(STRIPE_RETRY_SWEEP_LIMIT=8)
    def test_run_signal_mesh_retry_sweep_uses_stripe_default_limit(self, jobs_mock, webhooks_mock, stripe_mock):
        jobs_mock.return_value = {'dispatched_count': 0, 'skipped_count': 0}
        webhooks_mock.return_value = {'processed_count': 0, 'skipped_count': 0}
        stripe_mock.return_value = {'processed_count': 0, 'skipped_count': 0}

        call_command('run_signal_mesh_retry_sweep', stdout=StringIO())

        stripe_mock.assert_called_once_with(limit=8)
