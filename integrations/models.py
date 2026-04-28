"""
ARQUIVO: superficie publica dos modelos do app integrations.

POR QUE ELE EXISTE:
- garante que o app `integrations` exponha seus modelos ao ciclo de descoberta
  do Django, inclusive quando a suite roda com `--nomigrations`.
"""

from integrations.stripe.models import PaymentWebhookEvent, PaymentWebhookStatus
from integrations.whatsapp.models import WebhookDeliveryStatus, WebhookEvent

__all__ = [
    'PaymentWebhookEvent',
    'PaymentWebhookStatus',
    'WebhookDeliveryStatus',
    'WebhookEvent',
]
