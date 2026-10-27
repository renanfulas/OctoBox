"""Dry-run, backfill, or verify the shared invitee-email HMAC index."""

from __future__ import annotations

import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django_tenants.utils import get_public_schema_name, schema_context

from shared_support.crypto_fields import generate_student_app_invitation_email_blind_index
from student_identity.models import StudentAppInvitation


class Command(BaseCommand):
    help = 'Faz dry-run, backfill ou verify agregado do índice de email de convites shared.'

    def add_arguments(self, parser):
        action = parser.add_mutually_exclusive_group()
        action.add_argument('--apply', action='store_true', help='Grava índices ausentes usando compare-and-swap.')
        action.add_argument('--verify', action='store_true', help='Recalcula e compara sem gravar.')
        parser.add_argument('--batch-size', type=int, default=250)
        parser.add_argument('--limit', type=int, default=0, help='Limita a leitura; 0 percorre todos os convites.')

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            raise CommandError('O backfill shared exige PostgreSQL.')
        batch_size, limit = options['batch_size'], options['limit']
        if not 1 <= batch_size <= 5000:
            raise CommandError('batch-size deve estar entre 1 e 5000.')
        if limit < 0:
            raise CommandError('limit não pode ser negativo.')
        if not getattr(settings, 'EMAIL_BLIND_INDEX_KEY', ''):
            raise CommandError('EMAIL_BLIND_INDEX_KEY ausente; nenhum dado foi alterado.')

        counts = {
            'rows_scanned': 0, 'nonempty_email': 0, 'missing_index': 0,
            'written': 0, 'drift': 0, 'write_conflicts': 0,
        }
        cursor_id = 0
        apply = options['apply']
        verify = options['verify']
        try:
            with schema_context(get_public_schema_name()):
                while True:
                    remaining = limit - counts['rows_scanned'] if limit else batch_size
                    if limit and remaining <= 0:
                        break
                    size = min(batch_size, remaining) if limit else batch_size
                    queryset = StudentAppInvitation.objects.filter(pk__gt=cursor_id).order_by('pk')
                    if not verify:
                        queryset = queryset.filter(email_lookup_index='')
                    queryset = queryset.only('pk', 'invited_email', 'email_lookup_index')
                    if apply:
                        with transaction.atomic():
                            rows = list(queryset.select_for_update()[:size])
                            self._process(rows, counts, apply=True, verify=False)
                    else:
                        rows = list(queryset[:size])
                        self._process(rows, counts, apply=False, verify=verify)
                    if not rows:
                        break
                    cursor_id = rows[-1].pk
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError('Operação interrompida; nenhum email ou digest foi exibido.') from exc

        clean = not counts['missing_index'] and not counts['drift']
        report = {
            'scope': 'shared',
            'schema': get_public_schema_name(),
            'mode': 'apply' if apply else 'verify' if verify else 'dry-run',
            'complete_target_scan': not bool(limit),
            **counts,
            'verification_clean': bool(verify and not limit and clean),
        }
        self.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True))
        if verify and not clean:
            raise CommandError('Verificação encontrou índice ausente ou divergente.')

    @staticmethod
    def _process(rows, counts, *, apply, verify):
        for invitation in rows:
            counts['rows_scanned'] += 1
            expected = generate_student_app_invitation_email_blind_index(invitation.invited_email)
            if expected:
                counts['nonempty_email'] += 1
            if not invitation.email_lookup_index and expected:
                counts['missing_index'] += 1
                if apply:
                    updated = StudentAppInvitation.objects.filter(
                        pk=invitation.pk,
                        invited_email=invitation.invited_email,
                        email_lookup_index='',
                    ).update(email_lookup_index=expected)
                    if updated:
                        counts['written'] += 1
                    else:
                        counts['write_conflicts'] += 1
            elif verify and invitation.email_lookup_index != expected:
                counts['drift'] += 1


__all__ = ['Command']
