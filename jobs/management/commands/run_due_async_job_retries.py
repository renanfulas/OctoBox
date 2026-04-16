"""
ARQUIVO: comando institucional para reprocessar jobs vencidos da Signal Mesh.

POR QUE ELE EXISTE:
- liga o corredor oficial de reprocessamento a um scheduler simples como cron.
- evita depender de infraestrutura nova antes da hora.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from jobs.reprocessing import reprocess_due_async_jobs


class Command(BaseCommand):
    help = 'Reprocessa AsyncJobs pendentes cujo next_retry_at ja venceu.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limita quantos jobs vencidos entram nesta execucao.',
        )

    def handle(self, *args, **options):
        limit = options.get('limit') or getattr(settings, 'JOB_RETRY_SWEEP_LIMIT', 25)
        if limit <= 0:
            limit = getattr(settings, 'JOB_RETRY_SWEEP_LIMIT', 25)

        result = reprocess_due_async_jobs(limit=limit)
        self.stdout.write(
            self.style.SUCCESS(
                'Jobs reprocessados: '
                f"{result['dispatched_count']} disparados, {result['skipped_count']} ignorados."
            )
        )
