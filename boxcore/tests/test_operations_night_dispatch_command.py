"""
ARQUIVO: testes do comando de disparo noturno dos imports de leads.

POR QUE ELE EXISTE:
- protege a janela economica oficial dos jobs `async_night`.

O QUE ESTE ARQUIVO FAZ:
1. valida que o comando nao dispara fora da janela.
2. valida que o comando dispara a task dentro da janela.
3. valida que o modo `--force` ignora a janela.

PONTOS CRITICOS:
- se estes testes quebrarem, o sistema pode gastar recurso em horario comercial ou deixar de processar a fila noturna.
"""

from datetime import datetime
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from operations.management.commands.run_due_nightly_lead_import_jobs import is_within_night_window


class LeadImportNightDispatchCommandTests(TestCase):
    def _aware_datetime(self, hour: int, minute: int = 0):
        naive = datetime(2026, 4, 17, hour, minute)
        return timezone.make_aware(naive)

    def test_is_within_night_window_handles_standard_window(self):
        self.assertTrue(
            is_within_night_window(
                current_time=self._aware_datetime(0, 30),
                start_hour=0,
                end_hour=4,
            )
        )
        self.assertFalse(
            is_within_night_window(
                current_time=self._aware_datetime(4, 0),
                start_hour=0,
                end_hour=4,
            )
        )

    @override_settings(
        LEAD_IMPORT_NIGHT_WINDOW_START_HOUR=0,
        LEAD_IMPORT_NIGHT_WINDOW_END_HOUR=4,
        LEAD_IMPORT_NIGHT_SWEEP_LIMIT=12,
    )
    @patch('operations.management.commands.run_due_nightly_lead_import_jobs.count_due_nightly_lead_import_jobs')
    @patch('operations.management.commands.run_due_nightly_lead_import_jobs.dispatch_nightly_lead_import_jobs.delay')
    @patch('operations.management.commands.run_due_nightly_lead_import_jobs.timezone.localtime')
    def test_command_skips_outside_window(self, localtime_mock, delay_mock, due_count_mock):
        localtime_mock.return_value = self._aware_datetime(10, 15)
        out = StringIO()

        call_command('run_due_nightly_lead_import_jobs', stdout=out)

        due_count_mock.assert_not_called()
        delay_mock.assert_not_called()
        self.assertIn('Fora da janela noturna de imports.', out.getvalue())

    @override_settings(
        LEAD_IMPORT_NIGHT_WINDOW_START_HOUR=0,
        LEAD_IMPORT_NIGHT_WINDOW_END_HOUR=4,
        LEAD_IMPORT_NIGHT_SWEEP_LIMIT=9,
    )
    @patch('operations.management.commands.run_due_nightly_lead_import_jobs.count_due_nightly_lead_import_jobs')
    @patch('operations.management.commands.run_due_nightly_lead_import_jobs.dispatch_nightly_lead_import_jobs.delay')
    @patch('operations.management.commands.run_due_nightly_lead_import_jobs.timezone.localtime')
    def test_command_dispatches_inside_window(self, localtime_mock, delay_mock, due_count_mock):
        localtime_mock.return_value = self._aware_datetime(1, 5)
        due_count_mock.return_value = 4
        delay_mock.return_value = type('AsyncResult', (), {'id': 'task-123'})()
        out = StringIO()

        call_command('run_due_nightly_lead_import_jobs', stdout=out)

        due_count_mock.assert_called_once()
        delay_mock.assert_called_once_with(limit=9)
        self.assertIn('Sweep noturno de imports disparado.', out.getvalue())
        self.assertIn('Pendentes elegiveis: 4.', out.getvalue())
        self.assertIn('task-123', out.getvalue())

    @override_settings(
        LEAD_IMPORT_NIGHT_WINDOW_START_HOUR=0,
        LEAD_IMPORT_NIGHT_WINDOW_END_HOUR=4,
    )
    @patch('operations.management.commands.run_due_nightly_lead_import_jobs.count_due_nightly_lead_import_jobs')
    @patch('operations.management.commands.run_due_nightly_lead_import_jobs.dispatch_nightly_lead_import_jobs.delay')
    @patch('operations.management.commands.run_due_nightly_lead_import_jobs.timezone.localtime')
    def test_command_force_dispatches_outside_window(self, localtime_mock, delay_mock, due_count_mock):
        localtime_mock.return_value = self._aware_datetime(15, 45)
        due_count_mock.return_value = 2
        delay_mock.return_value = type('AsyncResult', (), {'id': 'task-force'})()
        out = StringIO()

        call_command('run_due_nightly_lead_import_jobs', '--force', '--limit', '3', stdout=out)

        due_count_mock.assert_called_once()
        delay_mock.assert_called_once_with(limit=3)
        self.assertIn('Sweep noturno de imports disparado.', out.getvalue())

    @override_settings(
        LEAD_IMPORT_NIGHT_WINDOW_START_HOUR=0,
        LEAD_IMPORT_NIGHT_WINDOW_END_HOUR=4,
        LEAD_IMPORT_NIGHT_SWEEP_LIMIT=9,
    )
    @patch('operations.management.commands.run_due_nightly_lead_import_jobs.count_due_nightly_lead_import_jobs')
    @patch('operations.management.commands.run_due_nightly_lead_import_jobs.dispatch_nightly_lead_import_jobs.delay')
    @patch('operations.management.commands.run_due_nightly_lead_import_jobs.timezone.localtime')
    def test_command_skips_when_there_are_no_due_jobs(self, localtime_mock, delay_mock, due_count_mock):
        localtime_mock.return_value = self._aware_datetime(1, 5)
        due_count_mock.return_value = 0
        out = StringIO()

        call_command('run_due_nightly_lead_import_jobs', stdout=out)

        due_count_mock.assert_called_once()
        delay_mock.assert_not_called()
        self.assertIn('Nenhum import noturno pendente para esta janela.', out.getvalue())
