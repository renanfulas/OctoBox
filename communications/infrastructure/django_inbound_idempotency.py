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

from django.db import IntegrityError

from communications.application.results import InboundWhatsAppMessageResult
from communications.models import WhatsAppMessageLog


def find_existing_inbound_message(*, external_message_id: str):
    if not external_message_id:
        return None
    return WhatsAppMessageLog.objects.filter(
        external_message_id=external_message_id
    ).select_related('contact').first()


def build_duplicate_inbound_result(existing_message):
    return InboundWhatsAppMessageResult(
        accepted=True,
        reason='duplicate-message-id',
        contact_id=existing_message.contact_id,
        message_log_id=existing_message.id,
    )


def create_inbound_message_with_idempotency(*, external_message_id: str, create_message):
    try:
        return create_message(), None
    except IntegrityError:
        existing_message = find_existing_inbound_message(external_message_id=external_message_id)
        if existing_message is not None:
            return None, build_duplicate_inbound_result(existing_message)
        raise


__all__ = [
    'build_duplicate_inbound_result',
    'create_inbound_message_with_idempotency',
    'find_existing_inbound_message',
]