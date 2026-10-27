"""Dry-run, backfill, or verify PendingSignup email HMACs in public."""

from __future__ import annotations

import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django_tenants.utils import get_public_schema_name, schema_context

from shared_support.crypto_codec import decode
from shared_support.crypto_fields import generate_pending_signup_email_blind_index
from signup.models import PendingSignup


class Command(BaseCommand):
    help = 'Faz dry-run, backfill CAS ou verificação agregada do índice de email PendingSignup.'

    def add_arguments(self, parser):
        action = parser.add_mutually_exclusive_group()
        action.add_argument('--apply', action='store_true', help='Grava índices ausentes com compare-and-swap.')
        action.add_argument('--verify', action='store_true', help='Recalcula e compara sem gravar.')
        parser.add_argument('--batch-size', type=int, default=250)
        parser.add_argument('--limit', type=int, default=0, help='Limita a leitura; 0 percorre todos os registros.')

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            raise CommandError('O backfill shared exige PostgreSQL.')
        batch_size = options['batch_size']
        limit = options['limit']
        if not 1 <= batch_size <= 5000:
            raise CommandError('batch-size deve estar entre 1 e 5000.')
        if limit < 0:
            raise CommandError('limit não pode ser negativo.')
        if not getattr(settings, 'EMAIL_BLIND_INDEX_KEY', ''):
            raise CommandError('EMAIL_BLIND_INDEX_KEY ausente; nenhum dado foi alterado.')

        apply_changes = options['apply']
        verify = options['verify']
        counts = {
            'rows_scanned': 0,
            'nonempty_email': 0,
            'missing_index': 0,
            'written': 0,
            'drift': 0,
            'write_conflicts': 0,
        }
        cursor_id = 0
        table = connection.ops.quote_name(PendingSignup._meta.db_table)
        pk_column = connection.ops.quote_name(PendingSignup._meta.pk.column)
        email_column = connection.ops.quote_name(PendingSignup._meta.get_field('email').column)
        index_column = connection.ops.quote_name(
            PendingSignup._meta.get_field('email_lookup_index').column,
        )

        try:
            with schema_context(get_public_schema_name()):
                while True:
                    remaining = limit - counts['rows_scanned'] if limit else batch_size
                    if limit and remaining <= 0:
                        break
                    size = min(batch_size, remaining) if limit else batch_size
                    where_index = '' if verify else f'AND {index_column} = %s'
                    params = [cursor_id]
                    if not verify:
                        params.append('')
                    params.append(size)
                    lock = ' FOR UPDATE' if apply_changes else ''
                    query = (
                        f'SELECT {pk_column}, {email_column}, {index_column} FROM {table} '
                        f'WHERE {pk_column} > %s {where_index} '
                        f'ORDER BY {pk_column} LIMIT %s{lock}'
                    )
                    if apply_changes:
                        with transaction.atomic():
                            with connection.cursor() as db_cursor:
                                db_cursor.execute(query, params)
                                rows = db_cursor.fetchall()
                                self._process_rows(
                                    rows,
                                    counts,
                                    apply_changes=True,
                                    verify=False,
                                    table=table,
                                    pk_column=pk_column,
                                    email_column=email_column,
                                    index_column=index_column,
                                )
                    else:
                        with connection.cursor() as db_cursor:
                            db_cursor.execute(query, params)
                            rows = db_cursor.fetchall()
                        self._process_rows(
                            rows,
                            counts,
                            apply_changes=False,
                            verify=verify,
                            table=table,
                            pk_column=pk_column,
                            email_column=email_column,
                            index_column=index_column,
                        )
                    if not rows:
                        break
                    cursor_id = rows[-1][0]
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(
                'Operação interrompida ao ler ou gravar o lote; nenhum email foi exibido.'
            ) from exc

        mode = 'apply' if apply_changes else 'verify' if verify else 'dry-run'
        report = {
            'scope': 'shared',
            'schema': get_public_schema_name(),
            'mode': mode,
            **counts,
            'complete_target_scan': not bool(limit),
            'verification_clean': bool(
                verify
                and not counts['missing_index']
                and not counts['drift']
                and not counts['write_conflicts']
            ),
        }
        self.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True))
        if verify and not report['verification_clean']:
            raise CommandError('Verificação encontrou índice ausente ou divergente.')

    @staticmethod
    def _process_rows(
        rows,
        counts,
        *,
        apply_changes,
        verify,
        table,
        pk_column,
        email_column,
        index_column,
    ):
        for pk, raw_email, stored_index in rows:
            counts['rows_scanned'] += 1
            decoded = decode(raw_email) if raw_email else None
            if decoded and not decoded.is_readable:
                raise CommandError(
                    'Registro contém email ilegível para o leitor atual; nenhum valor foi exibido.'
                )
            email = decoded.plaintext if decoded and decoded.is_readable else ''
            expected = generate_pending_signup_email_blind_index(email)
            if expected:
                counts['nonempty_email'] += 1
            if not stored_index and expected:
                counts['missing_index'] += 1
                if apply_changes:
                    query = (
                        f'UPDATE {table} SET {index_column} = %s '
                        f'WHERE {pk_column} = %s AND {email_column} = %s AND {index_column} = %s'
                    )
                    with connection.cursor() as cursor:
                        cursor.execute(query, [expected, pk, raw_email, stored_index])
                        if cursor.rowcount:
                            counts['written'] += 1
                        else:
                            counts['write_conflicts'] += 1
            elif verify and stored_index != expected:
                counts['drift'] += 1


__all__ = ['Command']
