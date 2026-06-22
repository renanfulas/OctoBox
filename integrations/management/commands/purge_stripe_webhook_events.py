"""
ARQUIVO: comando de retencao de eventos Stripe processados (S5).

POR QUE ELE EXISTE:
- Liga integrations/stripe/retention.py a um cron diario para minimizar a
  retencao de PII nos payloads brutos do Stripe.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from integrations.stripe.retention import purge_processed_payment_webhook_events


class Command(BaseCommand):
    help = 'Purga PaymentWebhookEvent PROCESSED antigos (retencao/PII). FAILED e preservado.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=0,
            help='Janela de retencao em dias (default: STRIPE_WEBHOOK_RETENTION_DAYS ou 90).',
        )

    def handle(self, *args, **options):
        days = options.get('days') or getattr(settings, 'STRIPE_WEBHOOK_RETENTION_DAYS', 90)
        if days <= 0:
            days = getattr(settings, 'STRIPE_WEBHOOK_RETENTION_DAYS', 90)

        deleted = purge_processed_payment_webhook_events(days=days)
        self.stdout.write(
            self.style.SUCCESS(
                f'PaymentWebhookEvent PROCESSED purgados: {deleted} (mais antigos que {days}d).'
            )
        )
