"""Tenant-aware scanner for due payment notification outbox rows."""

from django.conf import settings
from django.core.management.base import BaseCommand

from finance.notification_outbox import run_due_payment_notification_deliveries
from shared_support.tenant_sweep import (
    add_tenant_sweep_arguments,
    sweep_active_tenants,
    write_tenant_sweep_summary,
)


class Command(BaseCommand):
    help = 'Processa um lote das notificações financeiras vencidas em cada box ativo.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='Máximo por box nesta execução.')
        add_tenant_sweep_arguments(parser)

    def handle(self, *args, **options):
        limit = options.get('limit') or getattr(settings, 'PAYMENT_NOTIFICATION_SWEEP_LIMIT', 25)
        if limit <= 0:
            limit = 25

        sweep = sweep_active_tenants(
            lambda box: run_due_payment_notification_deliveries(limit=limit),
            only_schema=options.get('schema') or '',
        )
        totals = {
            key: sum((result or {}).get(key, 0) for _, result in sweep.results)
            for key in ('claimed', 'provider_accepted', 'retry_wait', 'unknown', 'skipped', 'failed')
        }
        self.stdout.write(self.style.SUCCESS(
            'Notificações financeiras: '
            f"{totals['claimed']} reservadas, {totals['provider_accepted']} aceitas, "
            f"{totals['retry_wait']} aguardando retry, {totals['unknown']} desconhecidas, "
            f"{totals['skipped']} ignoradas, {totals['failed']} falhas."
        ))
        write_tenant_sweep_summary(self, sweep)
