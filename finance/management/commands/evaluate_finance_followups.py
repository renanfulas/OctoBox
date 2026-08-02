"""
ARQUIVO: comando institucional para avaliar outcome de follow-ups financeiros.

POR QUE ELE EXISTE:
- fecha o ciclo entre sugestao da fila e resultado real, alimentando o analytics
  historico da trilha de churn.

PONTOS CRITICOS:
- `FinanceFollowUp` e model TENANT; este comando roda a partir do `public` (cron),
  entao a varredura precisa entrar no schema de cada box via `sweep_active_tenants`.
"""

from django.core.management.base import BaseCommand

from finance.follow_up_tracker import evaluate_pending_finance_follow_ups
from shared_support.tenant_sweep import (
    add_tenant_sweep_arguments,
    sweep_active_tenants,
    write_tenant_sweep_summary,
)


class Command(BaseCommand):
    help = 'Avalia follow-ups financeiros realizados cujo outcome ja venceu a janela configurada.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--window',
            choices=['7d', '15d', '30d'],
            default='',
            help='Avalia apenas uma janela especifica de outcome.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limita a quantidade de follow-ups avaliados por box nesta execucao.',
        )
        add_tenant_sweep_arguments(parser)

    def handle(self, *args, **options):
        window = options.get('window') or None
        limit = options.get('limit') or None
        if limit is not None and limit <= 0:
            limit = None

        sweep = sweep_active_tenants(
            lambda box: evaluate_pending_finance_follow_ups(window=window, limit=limit),
            only_schema=options.get('schema') or '',
        )

        evaluated = sum(count or 0 for _, count in sweep.results)
        window_label = window or 'todas as janelas'
        self.stdout.write(
            self.style.SUCCESS(
                f'Follow-ups financeiros avaliados: {evaluated} ({window_label}).'
            )
        )
        write_tenant_sweep_summary(self, sweep)
