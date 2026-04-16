"""
ARQUIVO: comando unico para sweep de retries da Signal Mesh.

POR QUE ELE EXISTE:
- oferece um ponto operacional simples para cron, Render ou systemd timer.
- reune jobs e webhooks sem exigir scheduler novo.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from integrations.whatsapp.reprocessing import reprocess_due_webhook_events
from jobs.reprocessing import reprocess_due_async_jobs


class Command(BaseCommand):
    help = 'Executa um sweep institucional de retries da Signal Mesh (jobs + webhooks).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--job-limit',
            type=int,
            default=0,
            help='Limita quantos jobs vencidos entram nesta execucao.',
        )
        parser.add_argument(
            '--webhook-limit',
            type=int,
            default=0,
            help='Limita quantos webhooks vencidos entram nesta execucao.',
        )

    def handle(self, *args, **options):
        job_limit = options.get('job_limit') or getattr(settings, 'JOB_RETRY_SWEEP_LIMIT', 25)
        webhook_limit = options.get('webhook_limit') or getattr(settings, 'WEBHOOK_RETRY_SWEEP_LIMIT', 25)
        if job_limit <= 0:
            job_limit = getattr(settings, 'JOB_RETRY_SWEEP_LIMIT', 25)
        if webhook_limit <= 0:
            webhook_limit = getattr(settings, 'WEBHOOK_RETRY_SWEEP_LIMIT', 25)

        jobs_result = reprocess_due_async_jobs(limit=job_limit)
        webhooks_result = reprocess_due_webhook_events(limit=webhook_limit)

        self.stdout.write(
            self.style.SUCCESS(
                'Signal Mesh sweep concluido: '
                f"jobs={jobs_result['dispatched_count']} disparados/{jobs_result['skipped_count']} ignorados, "
                f"webhooks={webhooks_result['processed_count']} processados/{webhooks_result['skipped_count']} ignorados."
            )
        )
