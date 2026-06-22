"""
ARQUIVO: comando unico para sweep de retries da Signal Mesh.

POR QUE ELE EXISTE:
- oferece um ponto operacional simples para cron, Render ou systemd timer.
- reune jobs e webhooks sem exigir scheduler novo.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from integrations.stripe.reprocessing import reprocess_due_stripe_webhook_events
from integrations.whatsapp.reprocessing import reprocess_due_webhook_events
from jobs.reprocessing import reprocess_due_async_jobs


class Command(BaseCommand):
    help = 'Executa um sweep institucional de retries da Signal Mesh (jobs + webhooks + stripe).'

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
            help='Limita quantos webhooks (WhatsApp) vencidos entram nesta execucao.',
        )
        parser.add_argument(
            '--stripe-limit',
            type=int,
            default=0,
            help='Limita quantos eventos Stripe vencidos entram nesta execucao.',
        )

    def handle(self, *args, **options):
        job_limit = options.get('job_limit') or getattr(settings, 'JOB_RETRY_SWEEP_LIMIT', 25)
        webhook_limit = options.get('webhook_limit') or getattr(settings, 'WEBHOOK_RETRY_SWEEP_LIMIT', 25)
        stripe_limit = options.get('stripe_limit') or getattr(settings, 'STRIPE_RETRY_SWEEP_LIMIT', 25)
        if job_limit <= 0:
            job_limit = getattr(settings, 'JOB_RETRY_SWEEP_LIMIT', 25)
        if webhook_limit <= 0:
            webhook_limit = getattr(settings, 'WEBHOOK_RETRY_SWEEP_LIMIT', 25)
        if stripe_limit <= 0:
            stripe_limit = getattr(settings, 'STRIPE_RETRY_SWEEP_LIMIT', 25)

        jobs_result = reprocess_due_async_jobs(limit=job_limit)
        webhooks_result = reprocess_due_webhook_events(limit=webhook_limit)
        stripe_result = reprocess_due_stripe_webhook_events(limit=stripe_limit)

        self.stdout.write(
            self.style.SUCCESS(
                'Signal Mesh sweep concluido: '
                f"jobs={jobs_result['dispatched_count']} disparados/{jobs_result['skipped_count']} ignorados, "
                f"webhooks={webhooks_result['processed_count']} processados/{webhooks_result['skipped_count']} ignorados, "
                f"stripe={stripe_result['processed_count']} processados/{stripe_result['skipped_count']} ignorados."
            )
        )
