"""
ARQUIVO: testes do verificador institucional de integridade historica.

POR QUE ELE EXISTE:
- garante que a checagem de FKs orfas continue detectando e reparando o caso seguro de AuditEvent.
"""

from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import SimpleTestCase


class HistoricalIntegrityCommandTests(SimpleTestCase):
    @patch('shared_support.management.commands.check_historical_integrity._find_orphaned_foreign_keys')
    def test_command_reports_clean_database(self, find_orphans_mock):
        find_orphans_mock.return_value = []
        stdout = StringIO()

        call_command('check_historical_integrity', stdout=stdout)

        self.assertIn('orphaned_foreign_keys=0', stdout.getvalue())
        self.assertIn('Nenhuma FK orfa encontrada.', stdout.getvalue())

    @patch('shared_support.management.commands.check_historical_integrity._repair_safe_orphans')
    @patch('shared_support.management.commands.check_historical_integrity._find_orphaned_foreign_keys')
    def test_command_can_repair_safe_orphans(self, find_orphans_mock, repair_mock):
        find_orphans_mock.side_effect = [
            [
                {
                    'table': 'boxcore_auditevent',
                    'column': 'actor_id',
                    'remote_table': 'auth_user',
                    'remote_column': 'id',
                    'constraint_name': 'fk_actor',
                    'orphan_count': 4,
                    'repairable': True,
                }
            ],
            [],
        ]
        repair_mock.return_value = [
            {
                'table': 'boxcore_auditevent',
                'column': 'actor_id',
                'label': 'audit_event_actor_set_null',
                'updated_rows': 4,
            }
        ]
        stdout = StringIO()

        call_command('check_historical_integrity', repair_safe=True, stdout=stdout)

        self.assertIn('repair=audit_event_actor_set_null', stdout.getvalue())
        self.assertIn('orphaned_foreign_keys_after_repair=0', stdout.getvalue())

    @patch('shared_support.management.commands.check_historical_integrity._find_orphaned_foreign_keys')
    def test_command_fails_when_orphans_exist_and_fail_flag_is_enabled(self, find_orphans_mock):
        find_orphans_mock.return_value = [
            {
                'table': 'boxcore_auditevent',
                'column': 'actor_id',
                'remote_table': 'auth_user',
                'remote_column': 'id',
                'constraint_name': 'fk_actor',
                'orphan_count': 1,
                'repairable': True,
            }
        ]
        stdout = StringIO()
        stderr = StringIO()

        with self.assertRaises(SystemExit):
            call_command(
                'check_historical_integrity',
                fail_on_orphans=True,
                stdout=stdout,
                stderr=stderr,
            )

        self.assertIn('FKs orfas', stderr.getvalue())
