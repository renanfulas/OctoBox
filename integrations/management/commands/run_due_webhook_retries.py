"""
ARQUIVO: comando institucional para reprocessar webhooks vencidos.

POR QUE ELE EXISTE:
- liga `WebhookEvent.next_retry_at` ao scheduler atual.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from integrations.whatsapp.reprocessing import reprocess_due_webhook_events


class Command(BaseCommand):
    help = 'Reprocessa WebhookEvents pendentes cujo next_retry_at ja venceu.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limita quantos webhooks vencidos entram nesta execucao.',
        )

    def handle(self, *args, **options):
        limit = options.get('limit') or getattr(settings, 'WEBHOOK_RETRY_SWEEP_LIMIT', 25)
        if limit <= 0:
            limit = getattr(settings, 'WEBHOOK_RETRY_SWEEP_LIMIT', 25)

        result = reprocess_due_webhook_events(limit=limit)
        self.stdout.write(
            self.style.SUCCESS(
                'Webhooks reprocessados: '
                f"{result['processed_count']} processados, {result['skipped_count']} ignorados."
            )
        )
