"""
ARQUIVO: comando de reconciliacao Stripe<->DB (rede de seguranca de fidelidade).

POR QUE ELE EXISTE:
- Liga finance/reconciliation.py a um cron/operacao. Roda do schema public e
  itera os boxes ativos internamente.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from finance.reconciliation import reconcile_stripe_payments


class Command(BaseCommand):
    help = 'Reconcilia pagamentos Stripe<->DB e reporta divergencias (read-only).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=0,
            help='Janela (em dias) de Payments recentes a verificar por box.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limite de Payments verificados por box.',
        )

    def handle(self, *args, **options):
        days = options.get('days') or getattr(settings, 'STRIPE_RECONCILE_WINDOW_DAYS', 7)
        limit = options.get('limit') or getattr(settings, 'STRIPE_RECONCILE_LIMIT', 100)

        report = reconcile_stripe_payments(days=days, limit=limit)

        self.stdout.write(
            self.style.SUCCESS(
                f"Reconciliacao Stripe<->DB: {report['checked']} verificados, "
                f"{report['drift_count']} divergencias."
            )
        )
        for entry in report['drift']:
            self.stdout.write(
                self.style.WARNING(
                    f"  drift box={entry['box']} payment={entry['payment_id']} "
                    f"motivo={entry['reason']} local={entry['local_status']} "
                    f"pi={entry['pi_status']} refunded={entry['refunded']}"
                )
            )
