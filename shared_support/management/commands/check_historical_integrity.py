"""
ARQUIVO: verificador institucional de integridade historica do banco.

POR QUE ELE EXISTE:
- detecta chaves estrangeiras orfas antes de uma rodada de migrate ou deploy.
- transforma o caso de `AuditEvent.actor_id` em procedimento explicito, nao memoria tribal.
"""

from django.core.management.base import BaseCommand
from django.db import connection, transaction


SAFE_REPAIRS = {
    ('boxcore_auditevent', 'actor_id'): {
        'sql': (
            'UPDATE {table} '
            'SET {column} = NULL '
            'WHERE {column} IS NOT NULL '
            'AND {column} NOT IN (SELECT {remote_column} FROM {remote_table})'
        ),
        'label': 'audit_event_actor_set_null',
    },
}


def _quote(name: str) -> str:
    return connection.ops.quote_name(name)


def _find_orphaned_foreign_keys() -> list[dict]:
    introspection = connection.introspection
    findings = []
    with connection.cursor() as cursor:
        for table_name in introspection.table_names(cursor):
            constraints = introspection.get_constraints(cursor, table_name)
            for constraint_name, constraint in constraints.items():
                foreign_key = constraint.get('foreign_key')
                columns = constraint.get('columns') or []
                if not foreign_key or len(columns) != 1:
                    continue

                local_column = columns[0]
                remote_table, remote_column = foreign_key
                query = (  # nosec B608
                    f'SELECT COUNT(*) FROM {_quote(table_name)} '  # nosec B608
                    f'WHERE {_quote(local_column)} IS NOT NULL '
                    f'AND {_quote(local_column)} NOT IN ('
                    f'SELECT {_quote(remote_column)} FROM {_quote(remote_table)}'
                    f')'
                )
                cursor.execute(query)
                orphan_count = cursor.fetchone()[0]
                if orphan_count:
                    findings.append(
                        {
                            'table': table_name,
                            'column': local_column,
                            'remote_table': remote_table,
                            'remote_column': remote_column,
                            'constraint_name': constraint_name,
                            'orphan_count': orphan_count,
                            'repairable': (table_name, local_column) in SAFE_REPAIRS,
                        }
                    )
    return findings


def _repair_safe_orphans(findings: list[dict]) -> list[dict]:
    repairs = []
    with transaction.atomic():
        with connection.cursor() as cursor:
            for finding in findings:
                repair = SAFE_REPAIRS.get((finding['table'], finding['column']))
                if repair is None:
                    continue
                cursor.execute(
                    repair['sql'].format(
                        table=_quote(finding['table']),
                        column=_quote(finding['column']),
                        remote_table=_quote(finding['remote_table']),
                        remote_column=_quote(finding['remote_column']),
                    )
                )
                repairs.append(
                    {
                        'table': finding['table'],
                        'column': finding['column'],
                        'label': repair['label'],
                        'updated_rows': cursor.rowcount,
                    }
                )
    return repairs


class Command(BaseCommand):
    help = 'Verifica FKs orfas historicas e pode reparar os casos explicitamente seguros.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--repair-safe',
            action='store_true',
            help='Aplica apenas reparos explicitamente seguros, como AuditEvent.actor_id -> NULL.',
        )
        parser.add_argument(
            '--fail-on-orphans',
            action='store_true',
            help='Retorna exit code 1 se houver qualquer FK orfa.',
        )

    def handle(self, *args, **options):
        findings = _find_orphaned_foreign_keys()
        self.stdout.write(f'orphaned_foreign_keys={len(findings)}')
        for finding in findings:
            self.stdout.write(
                (
                    f"{finding['table']}.{finding['column']} -> "
                    f"{finding['remote_table']}.{finding['remote_column']} "
                    f"count={finding['orphan_count']} repairable={finding['repairable']}"
                )
            )

        if options.get('repair_safe') and findings:
            repairs = _repair_safe_orphans(findings)
            for repair in repairs:
                self.stdout.write(
                    self.style.WARNING(
                        f"repair={repair['label']} table={repair['table']} column={repair['column']} updated_rows={repair['updated_rows']}"
                    )
                )
            findings = _find_orphaned_foreign_keys()
            self.stdout.write(f'orphaned_foreign_keys_after_repair={len(findings)}')

        if findings and options.get('fail_on_orphans'):
            self.stderr.write(self.style.ERROR('Foram encontradas FKs orfas no banco.'))
            raise SystemExit(1)

        if not findings:
            self.stdout.write(self.style.SUCCESS('Nenhuma FK orfa encontrada.'))


__all__ = [
    'SAFE_REPAIRS',
    '_find_orphaned_foreign_keys',
    '_repair_safe_orphans',
]
