"""
ARQUIVO: management command de migração de dados legacy para box_pilot.

POR QUE ELE EXISTE:
- Em produção, todos os dados boxcore_* estavam em public (1 instância = 1 box).
- Após o deploy de schema-per-tenant, esses dados precisam ser movidos para
  o schema do tenant correto (ex.: box_pilot) antes de o box ser ativado.

O QUE ESTE ARQUIVO FAZ:
1. Lista todas as tabelas boxcore_* no schema public.
2. Para cada tabela, copia as linhas para box_<slug>.boxcore_*.
3. Atualiza sequences para evitar colisão de PKs.
4. Valida contagens antes/depois.
5. Em --dry-run, mostra o plano sem executar.

USO:
    # Preview — veja o que seria migrado
    python manage.py migrate_existing_data_to_pilot --dry-run

    # Execução real (pilot = default)
    python manage.py migrate_existing_data_to_pilot --slug=pilot

    # Outro tenant
    python manage.py migrate_existing_data_to_pilot --slug=endorfina

    # Após validação, apaga linhas do public (CUIDADO — irreversível sem backup)
    python manage.py migrate_existing_data_to_pilot --slug=pilot --truncate-source

PONTOS CRITICOS:
- Execute APENAS após provision_box --slug=<pilot> ter criado o schema.
- Faça pg_dump ANTES de rodar (sem --dry-run).
- O comando é idempotente via ON CONFLICT DO NOTHING — pode ser executado 2x
  sem duplicar dados, MAS a segunda execução não migra linhas adicionadas após
  a primeira. Usar para replay só se os dados source ainda estão intactos.
- Sequences são ajustadas automaticamente após o copy para evitar colisão de PKs.
- --truncate-source APAGA as linhas do public PERMANENTEMENTE. Não usa DROP TABLE —
  as migrations do public ainda precisam das tabelas (SHARED_APPS ainda tem boxcore
  para migrações futuras). Apenas trunca o conteúdo.
"""

from __future__ import annotations

import time
import logging

from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger('control.migrate_pilot')


# Tabelas que NÃO devem ser copiadas (pertencem a SHARED_APPS, já estão em public correto)
_SKIP_TABLES = frozenset({
    # student_identity já é SHARED — não mover
    'student_identity_studentidentity',
    'student_identity_studentboxmembership',
    'student_identity_studentappinvitation',
    'student_identity_studentboxinvitelink',
    'student_identity_studenttransfer',
    'student_identity_studentinvitationdelivery',
    'student_identity_studentpushsubscription',
    # control plane
    'control_box',
    'control_membership',
    'control_boxprovisioningevent',
    'control_platformauditevent',
    'control_domain',
    # auth / django internals
    'auth_user',
    'auth_group',
    'auth_permission',
    'auth_user_groups',
    'auth_user_user_permissions',
    'auth_group_permissions',
    'django_content_type',
    'django_migrations',
    'django_session',
    # signup
    'signup_pendingsignup',
})


class Command(BaseCommand):
    help = (
        'Migra dados boxcore_* do schema public para o schema do tenant box_<slug>. '
        'Execute APENAS após provision_box criar o schema alvo. Faça backup antes.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--slug',
            default='pilot',
            help='Slug do Box alvo (ex.: pilot). O schema alvo sera box_<slug>. Padrao: pilot.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra o plano de migracao sem executar nenhuma query de escrita.',
        )
        parser.add_argument(
            '--truncate-source',
            action='store_true',
            help=(
                'Apos copiar com sucesso, APAGA as linhas das tabelas de origem em public. '
                'IRREVERSIVEL sem backup. Usar somente apos validar contagens.'
            ),
        )
        parser.add_argument(
            '--skip-counts',
            action='store_true',
            help='Pula validacao de contagens (mais rapido, menos seguro).',
        )

    def handle(self, *args, **options):
        from django.db import connection

        slug = (options['slug'] or 'pilot').strip()
        target_schema = f'box_{slug}'
        dry_run = options['dry_run']
        truncate_source = options['truncate_source']
        skip_counts = options['skip_counts']

        # Validações iniciais
        self.stdout.write(f'OctoBox — migrate_existing_data_to_pilot')
        self.stdout.write(f'  origem  : public')
        self.stdout.write(f'  destino : {target_schema}')
        self.stdout.write(f'  dry_run : {dry_run}')
        self.stdout.write(f'  truncate: {truncate_source}')
        self.stdout.write('')

        if truncate_source and dry_run:
            raise CommandError('--truncate-source e --dry-run sao incompativeis.')

        # Verificar que o schema alvo existe
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                [target_schema],
            )
            if not cursor.fetchone():
                raise CommandError(
                    f'Schema {target_schema!r} nao existe. '
                    f'Execute primeiro: python manage.py provision_box --slug={slug} ...'
                )

        # Listar tabelas elegíveis
        tables = self._list_eligible_tables(connection)
        if not tables:
            self.stdout.write(self.style.WARNING('Nenhuma tabela boxcore_* encontrada em public.'))
            return

        self.stdout.write(f'{len(tables)} tabelas elegíveis para migração:')
        for t in tables:
            self.stdout.write(f'  - {t}')
        self.stdout.write('')

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN] Nenhuma escrita será executada.'))
            self._show_dry_run_plan(connection, tables, target_schema)
            return

        # Executar migração tabela a tabela
        report = []
        errors = []

        for table in tables:
            result = self._migrate_table(
                connection,
                source_table=table,
                target_schema=target_schema,
                skip_counts=skip_counts,
            )
            report.append(result)
            if result.get('error'):
                errors.append(result)
                self.stdout.write(self.style.ERROR(
                    f'  ERRO {table}: {result["error"]}'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'  OK {table}: {result["rows_copied"]} linhas copiadas em {result["elapsed"]:.2f}s'
                ))

        # Ajustar sequences
        self.stdout.write('')
        self.stdout.write('Atualizando sequences...')
        self._reset_sequences(connection, tables, target_schema)

        # Resumo
        self.stdout.write('')
        self.stdout.write('=== RESUMO ===')
        total_rows = sum(r.get('rows_copied', 0) for r in report)
        self.stdout.write(f'  Tabelas migradas  : {len(report) - len(errors)}/{len(tables)}')
        self.stdout.write(f'  Total de linhas   : {total_rows}')
        self.stdout.write(f'  Erros             : {len(errors)}')

        if errors:
            self.stdout.write(self.style.ERROR(
                f'\n{len(errors)} tabela(s) com erro — verifique antes de --truncate-source.'
            ))
            for e in errors:
                self.stdout.write(f'  {e["table"]}: {e["error"]}')
            raise CommandError('Migracao concluida com erros. Veja log acima.')

        if not skip_counts:
            self._validate_counts(connection, tables, target_schema)

        # Truncate source (opcional, destrutivo)
        if truncate_source:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('Apagando linhas de origem em public...'))
            self._truncate_source(connection, tables)
            self.stdout.write(self.style.SUCCESS('Linhas de origem apagadas.'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'migrate_existing_data_to_pilot concluido. {total_rows} linhas em {target_schema}.'
        ))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _list_eligible_tables(self, connection) -> list[str]:
        """Lista tabelas boxcore_* em public que NÃO estão na lista de skip."""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name LIKE 'boxcore\\_%%' ESCAPE '\\'
                ORDER BY table_name
            """)
            all_tables = [row[0] for row in cursor.fetchall()]

        return [t for t in all_tables if t not in _SKIP_TABLES]

    def _show_dry_run_plan(self, connection, tables: list[str], target_schema: str) -> None:
        """Exibe contagens sem executar nenhuma escrita."""
        self.stdout.write('')
        self.stdout.write(f'{"Tabela":<50} {"Linhas em public":>18}')
        self.stdout.write('-' * 70)
        total = 0
        for table in tables:
            with connection.cursor() as cursor:
                try:
                    cursor.execute(f'SELECT COUNT(*) FROM public."{table}"')
                    count = cursor.fetchone()[0]
                except Exception as exc:
                    count = f'ERRO: {exc}'
            self.stdout.write(f'{table:<50} {str(count):>18}')
            if isinstance(count, int):
                total += count
        self.stdout.write('-' * 70)
        self.stdout.write(f'{"TOTAL":<50} {total:>18}')

    def _migrate_table(
        self,
        connection,
        *,
        source_table: str,
        target_schema: str,
        skip_counts: bool,
    ) -> dict:
        """Copia linhas de public.<table> para <target_schema>.<table> via INSERT ... SELECT.

        Usa ON CONFLICT DO NOTHING para idempotência (assume PK em todas as tabelas boxcore_*).
        """
        t0 = time.monotonic()
        result = {'table': source_table, 'rows_copied': 0, 'elapsed': 0.0, 'error': None}

        try:
            with connection.cursor() as cursor:
                # Verificar que a tabela existe no schema alvo
                cursor.execute(
                    """
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = %s AND table_name = %s
                    """,
                    [target_schema, source_table],
                )
                if not cursor.fetchone():
                    result['error'] = (
                        f'Tabela {source_table!r} nao existe em {target_schema!r}. '
                        'Schema foi provisionado corretamente?'
                    )
                    return result

                # Obter colunas disponíveis em ambos os schemas para evitar divergências
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    [source_table],
                )
                source_cols = [row[0] for row in cursor.fetchall()]

                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    [target_schema, source_table],
                )
                target_cols = set(row[0] for row in cursor.fetchall())

                # Interseção — evita copiar colunas que foram removidas no schema alvo
                cols = [c for c in source_cols if c in target_cols]
                if not cols:
                    result['error'] = 'Nenhuma coluna em comum entre public e schema alvo.'
                    return result

                cols_sql = ', '.join(f'"{c}"' for c in cols)

                # Contar linhas na origem
                cursor.execute(f'SELECT COUNT(*) FROM public."{source_table}"')
                source_count = cursor.fetchone()[0]

                if source_count == 0:
                    result['rows_copied'] = 0
                    result['elapsed'] = time.monotonic() - t0
                    return result

                # INSERT ... SELECT com ON CONFLICT DO NOTHING (idempotente)
                # Assume que todas as tabelas boxcore_* têm PK 'id'
                cursor.execute(f"""
                    INSERT INTO "{target_schema}"."{source_table}" ({cols_sql})
                    SELECT {cols_sql}
                    FROM public."{source_table}"
                    ON CONFLICT DO NOTHING
                """)
                rows_copied = cursor.rowcount

                result['rows_copied'] = rows_copied

        except Exception as exc:
            logger.exception('_migrate_table: falha em %s', source_table)
            result['error'] = str(exc)

        result['elapsed'] = time.monotonic() - t0
        return result

    def _reset_sequences(self, connection, tables: list[str], target_schema: str) -> None:
        """Ajusta sequences de auto-increment no schema alvo após o copy.

        Sem este ajuste, INSERT novo no tenant colide com IDs migrados.
        """
        with connection.cursor() as cursor:
            for table in tables:
                try:
                    # Estratégia: busca o sequence associado à coluna 'id'
                    cursor.execute(
                        """
                        SELECT pg_get_serial_sequence(%s, 'id')
                        """,
                        [f'{target_schema}.{table}'],
                    )
                    row = cursor.fetchone()
                    if not row or not row[0]:
                        continue  # sem sequence (PK não é serial/bigserial)
                    seq_name = row[0]

                    # Atualiza sequence para max(id) + 1
                    cursor.execute(
                        f'SELECT setval(%s, COALESCE((SELECT MAX(id) FROM "{target_schema}"."{table}"), 0) + 1, false)',
                        [seq_name],
                    )
                    self.stdout.write(f'  sequence {seq_name} atualizado.')

                except Exception as exc:
                    self.stdout.write(self.style.WARNING(
                        f'  sequence de {table} nao atualizado: {exc}'
                    ))

    def _validate_counts(self, connection, tables: list[str], target_schema: str) -> None:
        """Compara contagens source vs target e alerta sobre discrepâncias."""
        self.stdout.write('')
        self.stdout.write('Validando contagens...')
        mismatches = []

        with connection.cursor() as cursor:
            for table in tables:
                try:
                    cursor.execute(f'SELECT COUNT(*) FROM public."{table}"')
                    source_count = cursor.fetchone()[0]

                    cursor.execute(f'SELECT COUNT(*) FROM "{target_schema}"."{table}"')
                    target_count = cursor.fetchone()[0]

                    if source_count != target_count:
                        mismatches.append({
                            'table': table,
                            'source': source_count,
                            'target': target_count,
                        })
                    else:
                        self.stdout.write(f'  {table}: {source_count} == {target_count} OK')
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(f'  {table}: nao validado — {exc}'))

        if mismatches:
            self.stdout.write(self.style.WARNING('\nDiscrepancias de contagem:'))
            for m in mismatches:
                self.stdout.write(self.style.WARNING(
                    f'  {m["table"]}: public={m["source"]} vs {target_schema}={m["target"]}'
                ))
            self.stdout.write(
                'Discrepancias podem ocorrer se rows foram criadas apos o inicio da migracao. '
                'Avalie se sao aceitaveis ou re-execute o comando.'
            )
        else:
            self.stdout.write(self.style.SUCCESS('Todas as contagens conferem.'))

    def _truncate_source(self, connection, tables: list[str]) -> None:
        """Remove linhas das tabelas de origem em public (IRREVERSÍVEL sem backup)."""
        with connection.cursor() as cursor:
            for table in tables:
                try:
                    cursor.execute(f'DELETE FROM public."{table}"')
                    self.stdout.write(f'  DELETE FROM public.{table}: {cursor.rowcount} linhas removidas')
                except Exception as exc:
                    self.stdout.write(self.style.ERROR(f'  DELETE {table}: FALHOU — {exc}'))
