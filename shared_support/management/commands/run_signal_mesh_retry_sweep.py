"""
ARQUIVO: comando unico para sweep de retries da Signal Mesh.

POR QUE ELE EXISTE:
- oferece um ponto operacional simples para cron, Render ou systemd timer.
- reune jobs e webhooks sem exigir scheduler novo.

PONTOS CRITICOS:
- as tres pernas deste sweep tem tenancy DIFERENTE e por isso rodam em lugares
  diferentes:
  1. `AsyncJob` e TENANT (`app_label='boxcore'`) -> precisa de `sweep_active_tenants`;
     rodando no public a tabela nao existe e o retry morre em silencio.
  2. `WebhookEvent` (WhatsApp) e SHARED -> roda uma vez no public.
  3. `PaymentWebhookEvent` (Stripe) e SHARED e o roteador ja resolve o tenant
     internamente por evento -> roda uma vez no public.
- misturar as tres numa chamada unica no public era o bug: so a perna de jobs
  quebrava, e a mensagem de sucesso escondia isso.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from integrations.stripe.reprocessing import reprocess_due_stripe_webhook_events
from integrations.whatsapp.reprocessing import reprocess_due_webhook_events
from jobs.reprocessing import reprocess_due_async_jobs
from shared_support.tenant_sweep import (
    add_tenant_sweep_arguments,
    sweep_active_tenants,
    write_tenant_sweep_summary,
)


class Command(BaseCommand):
    help = 'Executa um sweep institucional de retries da Signal Mesh (jobs + webhooks + stripe).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--job-limit',
            type=int,
            default=0,
            help='Limita quantos jobs vencidos entram nesta execucao, por box.',
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
        add_tenant_sweep_arguments(parser)

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

        # Perna TENANT: AsyncJob so existe dentro do schema de cada box.
        jobs_sweep = sweep_active_tenants(
            lambda box: reprocess_due_async_jobs(limit=job_limit),
            only_schema=options.get('schema') or '',
        )
        jobs_dispatched = sum((r or {}).get('dispatched_count', 0) for _, r in jobs_sweep.results)
        jobs_skipped = sum((r or {}).get('skipped_count', 0) for _, r in jobs_sweep.results)

        # Pernas SHARED: rodam uma vez, no public.
        webhooks_result = reprocess_due_webhook_events(limit=webhook_limit)
        stripe_result = reprocess_due_stripe_webhook_events(limit=stripe_limit)

        self.stdout.write(
            self.style.SUCCESS(
                'Signal Mesh sweep concluido: '
                f'jobs={jobs_dispatched} disparados/{jobs_skipped} ignorados, '
                f"webhooks={webhooks_result['processed_count']} processados/{webhooks_result['skipped_count']} ignorados, "
                f"stripe={stripe_result['processed_count']} processados/{stripe_result['skipped_count']} ignorados."
            )
        )
        write_tenant_sweep_summary(self, jobs_sweep)
