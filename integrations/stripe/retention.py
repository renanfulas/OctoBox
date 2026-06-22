"""
ARQUIVO: retencao de eventos Stripe processados (data minimization / S5).

POR QUE ELE EXISTE:
- PaymentWebhookEvent.payload guarda o evento Stripe cru, que inclui PII do
  cliente (email, nome, endereco). Depois de PROCESSED e antigo, esse payload nao
  tem mais valor de idempotencia (a Stripe nao reenvia eventos de meses atras),
  entao manter para sempre so aumenta a superficie de PII retida.

O QUE ELE FAZ:
- Apaga PaymentWebhookEvent PROCESSED mais antigos que a janela de retencao.
- Preserva FAILED (dead-letter precisa de investigacao) e nao toca StripePaymentRef
  (mapa de tenant usado por eventos charge.* futuros).
"""

from datetime import timedelta

from django.utils import timezone

from .models import PaymentWebhookEvent, PaymentWebhookStatus


def purge_processed_payment_webhook_events(*, days: int = 90, now=None) -> int:
    """Apaga PaymentWebhookEvent PROCESSED com updated_at anterior a `days`.

    Retorna a quantidade de registros removidos.
    """
    current = now or timezone.now()
    cutoff = current - timedelta(days=days)
    deleted, _ = (
        PaymentWebhookEvent.objects
        .filter(status=PaymentWebhookStatus.PROCESSED, updated_at__lt=cutoff)
        .delete()
    )
    return deleted


__all__ = ['purge_processed_payment_webhook_events']
