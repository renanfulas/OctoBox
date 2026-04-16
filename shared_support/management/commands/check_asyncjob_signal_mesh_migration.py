"""
ARQUIVO: verificador operacional da migracao de AsyncJob para a Signal Mesh.

POR QUE ELE EXISTE:
- transforma o runbook de deploy em checklist executavel.
- confirma migracao aplicada e colunas esperadas antes e depois do deploy.
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from jobs.models import AsyncJob


REQUIRED_COLUMNS = {
    'job_type',
    'created_by_id',
    'attempts',
    'max_retries',
    'next_retry_at',
    'last_failure_kind',
}
TARGET_MIGRATION = ('boxcore', '0021_asyncjob_signal_mesh_fields')


def _list_asyncjob_columns():
    table_name = AsyncJob._meta.db_table
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table_name)
    return {column.name for column in description}


def _migration_is_applied():
    executor = MigrationExecutor(connection)
    applied = executor.loader.applied_migrations
    return TARGET_MIGRATION in applied


class Command(BaseCommand):
    help = 'Verifica se a migracao de AsyncJob da Signal Mesh foi aplicada e se as colunas existem.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--require-applied',
            action='store_true',
            help='Falha com exit code 1 se a migracao ainda nao estiver aplicada.',
        )

    def handle(self, *args, **options):
        migration_applied = _migration_is_applied()
        existing_columns = _list_asyncjob_columns()
        missing_columns = sorted(REQUIRED_COLUMNS - existing_columns)

        self.stdout.write(f'migration_applied={migration_applied}')
        self.stdout.write(f'asyncjob_table={AsyncJob._meta.db_table}')
        self.stdout.write(f'missing_columns={",".join(missing_columns) if missing_columns else "none"}')

        if not migration_applied or missing_columns:
            message = 'AsyncJob Signal Mesh migration ainda nao esta totalmente saneada.'
            if options.get('require_applied'):
                self.stderr.write(self.style.ERROR(message))
                raise SystemExit(1)
            self.stdout.write(self.style.WARNING(message))
            return

        self.stdout.write(self.style.SUCCESS('AsyncJob Signal Mesh migration aplicada e schema saneado.'))
