"""
ARQUIVO: comando institucional para reprocessar jobs vencidos da Signal Mesh.

POR QUE ELE EXISTE:
- liga o corredor oficial de reprocessamento a um scheduler simples como cron.
- evita depender de infraestrutura nova antes da hora.

PONTOS CRITICOS:
- `AsyncJob` e model TENANT; este comando roda a partir do `public` (cron), entao
  a varredura precisa entrar no schema de cada box via `sweep_active_tenants`.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from jobs.reprocessing import reprocess_due_async_jobs
from shared_support.tenant_sweep import (
    add_tenant_sweep_arguments,
    sweep_active_tenants,
    write_tenant_sweep_summary,
)


class Command(BaseCommand):
    help = 'Reprocessa AsyncJobs pendentes cujo next_retry_at ja venceu.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limita quantos jobs vencidos entram nesta execucao por box.',
        )
        add_tenant_sweep_arguments(parser)

    def handle(self, *args, **options):
        limit = options.get('limit') or getattr(settings, 'JOB_RETRY_SWEEP_LIMIT', 25)
        if limit <= 0:
            limit = getattr(settings, 'JOB_RETRY_SWEEP_LIMIT', 25)

        sweep = sweep_active_tenants(
            lambda box: reprocess_due_async_jobs(limit=limit),
            only_schema=options.get('schema') or '',
        )

        dispatched = sum((result or {}).get('dispatched_count', 0) for _, result in sweep.results)
        skipped = sum((result or {}).get('skipped_count', 0) for _, result in sweep.results)
        self.stdout.write(
            self.style.SUCCESS(
                f'Jobs reprocessados: {dispatched} disparados, {skipped} ignorados.'
            )
        )
        write_tenant_sweep_summary(self, sweep)
