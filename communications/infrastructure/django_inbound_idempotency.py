"""
ARQUIVO: servico tecnico de idempotencia inbound de WhatsApp.

POR QUE ELE EXISTE:
- isola a deduplicacao inbound do adapter principal do fluxo de communications.
- alinha a precedencia de `idempotency_key` com a lingua comum da Signal Mesh.
"""

from django.db import IntegrityError, models
from prometheus_client import Counter

from communications.application.results import InboundWhatsAppMessageResult
from communications.models import WhatsAppMessageLog
from integrations.mesh import calculate_signal_fingerprint, resolve_idempotency_key

WEBHOOK_DUPLICATES_COUNTER = Counter(
    'webhook_duplicates_total',
    'Total de webhooks detectados como duplicados (idempotencia)',
)


def calculate_webhook_fingerprint(payload: dict) -> str:
    """Compatibilidade fina sobre o fingerprint canonico da Signal Mesh."""
    return calculate_signal_fingerprint(payload)


def resolve_inbound_message_idempotency_key(*, external_message_id: str = '', webhook_fingerprint: str = '') -> str:
    return resolve_idempotency_key(
        explicit_key=external_message_id,
        fingerprint=webhook_fingerprint,
    )


def find_existing_inbound_message(*, external_message_id: str = '', webhook_fingerprint: str = ''):
    query = WhatsAppMessageLog.objects.all()

    if external_message_id and webhook_fingerprint:
        query = query.filter(
            models.Q(external_message_id=external_message_id)
            | models.Q(webhook_fingerprint=webhook_fingerprint)
        )
    elif external_message_id:
        query = query.filter(external_message_id=external_message_id)
    elif webhook_fingerprint:
        query = query.filter(webhook_fingerprint=webhook_fingerprint)
    else:
        return None

    return query.select_related('contact').first()


def build_duplicate_inbound_result(existing_message):
    WEBHOOK_DUPLICATES_COUNTER.inc()
    return InboundWhatsAppMessageResult(
        accepted=True,
        reason='duplicate-message-id',
        contact_id=existing_message.contact_id,
        message_log_id=existing_message.id,
    )


def create_inbound_message_with_idempotency(*, external_message_id: str, webhook_fingerprint: str, create_message):
    try:
        return create_message(), None
    except IntegrityError:
        existing_message = find_existing_inbound_message(
            external_message_id=external_message_id,
            webhook_fingerprint=webhook_fingerprint,
        )
        if existing_message is not None:
            return None, build_duplicate_inbound_result(existing_message)
        raise


__all__ = [
    'build_duplicate_inbound_result',
    'calculate_webhook_fingerprint',
    'create_inbound_message_with_idempotency',
    'find_existing_inbound_message',
    'resolve_inbound_message_idempotency_key',
]
