"""
ARQUIVO: testes do verificador operacional da migracao AsyncJob + Signal Mesh.

POR QUE ELE EXISTE:
- garante que o checklist executavel do deploy continue confiavel.
"""

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase


class AsyncJobSignalMeshMigrationCommandTests(SimpleTestCase):
    @patch('shared_support.management.commands.check_asyncjob_signal_mesh_migration._list_asyncjob_columns')
    @patch('shared_support.management.commands.check_asyncjob_signal_mesh_migration._migration_is_applied')
    def test_command_reports_success_when_schema_is_sane(self, migration_applied_mock, list_columns_mock):
        migration_applied_mock.return_value = True
        list_columns_mock.return_value = {
            'id',
            'job_type',
            'created_by_id',
            'attempts',
            'max_retries',
            'next_retry_at',
            'last_failure_kind',
        }
        stdout = StringIO()

        call_command('check_asyncjob_signal_mesh_migration', stdout=stdout)

        self.assertIn('migration_applied=True', stdout.getvalue())
        self.assertIn('schema saneado', stdout.getvalue())

    @patch('shared_support.management.commands.check_asyncjob_signal_mesh_migration._list_asyncjob_columns')
    @patch('shared_support.management.commands.check_asyncjob_signal_mesh_migration._migration_is_applied')
    def test_command_fails_when_require_applied_and_columns_are_missing(self, migration_applied_mock, list_columns_mock):
        migration_applied_mock.return_value = False
        list_columns_mock.return_value = {'id'}
        stdout = StringIO()
        stderr = StringIO()

        with self.assertRaises(SystemExit):
            call_command(
                'check_asyncjob_signal_mesh_migration',
                require_applied=True,
                stdout=stdout,
                stderr=stderr,
            )

        self.assertIn('ainda nao esta totalmente saneada', stderr.getvalue())
