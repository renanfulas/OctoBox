"""
ARQUIVO: servico tecnico de idempotencia inbound de WhatsApp.

POR QUE ELE EXISTE:
- Isola a deduplicacao por external_message_id do adapter principal do fluxo inbound.

O QUE ESTE ARQUIVO FAZ:
1. Busca mensagem inbound existente por id externo.
2. Tenta criar log inbound e traduz duplicidade para retorno idempotente.

PONTOS CRITICOS:
- Esta camada pode usar ORM e IntegrityError livremente, mas nao deve assumir regra de negocio fora da deduplicacao tecnica.
"""

import hashlib
import json
from django.db import IntegrityError, models
from prometheus_client import Counter

from communications.application.results import InboundWhatsAppMessageResult
from communications.models import WhatsAppMessageLog

WEBHOOK_DUPLICATES_COUNTER = Counter(
    'webhook_duplicates_total',
    'Total de webhooks detectados como duplicados (idempotencia)'
)


def calculate_webhook_fingerprint(payload: dict) -> str:
    """Gera um hash deterministico do payload para deduplicacao (Idempotencia)."""
    if not payload:
        return ''
    # Ordenamos as chaves para garantir que o mesmo JSON gere o mesmo hash
    dumped = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(dumped.encode('utf-8')).hexdigest()


def find_existing_inbound_message(*, external_message_id: str = '', webhook_fingerprint: str = ''):
    query = WhatsAppMessageLog.objects.all()
    
    if external_message_id and webhook_fingerprint:
        query = query.filter(
            models.Q(external_message_id=external_message_id) | 
            models.Q(webhook_fingerprint=webhook_fingerprint)
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
            webhook_fingerprint=webhook_fingerprint
        )
        if existing_message is not None:
            return None, build_duplicate_inbound_result(existing_message)
        raise


__all__ = [
    'build_duplicate_inbound_result',
    'create_inbound_message_with_idempotency',
    'find_existing_inbound_message',
]