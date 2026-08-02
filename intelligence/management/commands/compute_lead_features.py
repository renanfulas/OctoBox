"""
ARQUIVO: comando institucional para computar o feature layer de leads.

POR QUE ELE EXISTE:
- liga o job de calculo (intelligence/leads/jobs.py) a um scheduler simples
  (cron/systemd), reusando o corredor de varredura por tenant da Onda 1
  (shared_support/tenant_sweep.py) — LeadChannelDailyFact e StudentIntake
  sao ambos TENANT, entao o calculo precisa rodar dentro do schema de cada
  box, nunca no public.
"""

from django.core.management.base import BaseCommand

from intelligence.leads.jobs import (
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_MATURATION_DAYS,
    compute_and_persist_lead_channel_facts,
)
from shared_support.tenant_sweep import (
    add_tenant_sweep_arguments,
    sweep_active_tenants,
    write_tenant_sweep_summary,
)


def _parse_window_days(value):
    normalized = (value or '').strip().lower()
    if normalized.endswith('d'):
        normalized = normalized[:-1]
    try:
        return max(int(normalized), 1)
    except (TypeError, ValueError):
        return DEFAULT_LOOKBACK_DAYS


class Command(BaseCommand):
    help = 'Computa o feature layer de leads (contagem por canal/janela) para cada box ativo.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--window',
            default=f'{DEFAULT_LOOKBACK_DAYS}d',
            help=f'Janela de lookback do coorte, ex: 90d (default: {DEFAULT_LOOKBACK_DAYS}d).',
        )
        parser.add_argument(
            '--maturation-days',
            type=int,
            default=DEFAULT_MATURATION_DAYS,
            help='Dias de maturacao antes de um lead entrar no coorte (evita censura a direita).',
        )
        add_tenant_sweep_arguments(parser)

    def handle(self, *args, **options):
        lookback_days = _parse_window_days(options.get('window'))
        maturation_days = options.get('maturation_days') or DEFAULT_MATURATION_DAYS

        sweep = sweep_active_tenants(
            lambda box: compute_and_persist_lead_channel_facts(
                lookback_days=lookback_days,
                maturation_days=maturation_days,
            ),
            only_schema=options.get('schema') or '',
        )

        cells_total = sum((result or {}).get('cells_persisted', 0) for _, result in sweep.results)
        self.stdout.write(
            self.style.SUCCESS(
                f'Feature layer de leads computado: {cells_total} celula(s) persistida(s) no total.'
            )
        )
        write_tenant_sweep_summary(self, sweep)
