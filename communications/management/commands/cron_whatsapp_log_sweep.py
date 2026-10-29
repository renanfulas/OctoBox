"""Manually prune old WhatsApp message logs within one tenant.

Retention remains seven days. The command is deliberately dry-run by default,
requires an explicit Box schema, and fences its opt-in deletion so restore
freezes can drain and reject it safely.
"""

from datetime import timedelta
import logging
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context

from communications.models import WhatsAppMessageLog
from control.models import Box
from control.tenant_write_fence import tenant_write_guarded_command
from shared_support.tenant_logging import tenant_log_ref


logger = logging.getLogger('octobox.security.gc')
_SCHEMA_RE = re.compile(r'^box_[a-z0-9_-]{1,59}$')
RETENTION_DAYS = 7


class Command(BaseCommand):
    help = 'Inspeciona ou remove logs de WhatsApp com mais de 7 dias de um Box explícito.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--schema',
            required=True,
            help='Schema de um Box ACTIVE (box_<slug>); nunca varre todos os Boxes.',
        )
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Aplica a exclusão. Sem esta opção, apenas mostra a quantidade elegível.',
        )

    @tenant_write_guarded_command(write_option='apply')
    def handle(self, *args, **options):
        schema_name = str(options.get('schema') or '').strip()
        if not _SCHEMA_RE.fullmatch(schema_name) or schema_name == get_public_schema_name():
            raise CommandError('Informe um schema válido no formato box_<slug>.')

        with schema_context(get_public_schema_name()):
            box = Box.objects.filter(
                schema_name=schema_name,
                status=Box.Status.ACTIVE,
            ).only('schema_name').first()
        if box is None:
            raise CommandError('Box ACTIVE não encontrado para o identificador informado.')

        cutoff = timezone.now() - timedelta(days=RETENTION_DAYS)
        with schema_context(schema_name):
            old_logs = WhatsAppMessageLog.objects.filter(created_at__lt=cutoff)
            eligible_count = old_logs.count()
            if not options.get('apply'):
                self.stdout.write(
                    f'Dry-run: {eligible_count} log(s) elegíveis em {tenant_log_ref(box)} com mais de '
                    f'{RETENTION_DAYS} dias; nenhum registro foi removido.'
                )
                return

            with transaction.atomic():
                deleted_count, _details = old_logs.delete()

        logger.info(
            'whatsapp_message_log_retention_applied',
            extra={
                'box_ref': tenant_log_ref(box),
                'eligible_count': eligible_count,
                'deleted_count': deleted_count,
                'retention_days': RETENTION_DAYS,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'Exclusão aplicada em {tenant_log_ref(box)}: {deleted_count} log(s) removido(s) '
                f'com retenção de {RETENTION_DAYS} dias.'
            )
        )
