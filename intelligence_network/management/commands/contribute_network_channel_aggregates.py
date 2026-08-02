"""
ARQUIVO: comando institucional para contribuir agregados de canal ao hub de rede.

POR QUE ELE EXISTE:
- liga a contribuicao por box (intelligence_network/contribution.py) a um
  scheduler simples, reusando a varredura por tenant da Onda 1 —
  LeadChannelDailyFact e StudentIntake sao TENANT, entao a leitura precisa
  rodar dentro do schema de cada box.
"""

from django.core.management.base import BaseCommand

from intelligence_network.contribution import (
    DEFAULT_MIN_CAPTURED_TO_CONTRIBUTE,
    contribute_box_channel_aggregates,
)
from shared_support.tenant_sweep import (
    add_tenant_sweep_arguments,
    sweep_active_tenants,
    write_tenant_sweep_summary,
)


class Command(BaseCommand):
    help = 'Contribui agregados de canal (leads) de cada box ativo para o hub de rede.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-captured',
            type=int,
            default=DEFAULT_MIN_CAPTURED_TO_CONTRIBUTE,
            help=f'Piso de captured_total por celula para contribuir (default: {DEFAULT_MIN_CAPTURED_TO_CONTRIBUTE}).',
        )
        add_tenant_sweep_arguments(parser)

    def handle(self, *args, **options):
        min_captured = options.get('min_captured') or DEFAULT_MIN_CAPTURED_TO_CONTRIBUTE

        sweep = sweep_active_tenants(
            lambda box: contribute_box_channel_aggregates(box=box, min_captured_to_contribute=min_captured),
            only_schema=options.get('schema') or '',
        )

        cells_total = sum((result or 0) for _, result in sweep.results)
        self.stdout.write(
            self.style.SUCCESS(f'Hub de rede: {cells_total} celula(s) contribuida(s) no total.')
        )
        write_tenant_sweep_summary(self, sweep)
