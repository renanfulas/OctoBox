"""
ARQUIVO: commands explicitos do dominio de communications.

POR QUE ELE EXISTE:
- Evita contratos implícitos e deixa claros os fluxos de entrada e saída do domínio.

O QUE ESTE ARQUIVO FAZ:
1. Define o command de registro inbound de WhatsApp.
2. Define o command do toque operacional outbound.

PONTOS CRITICOS:
- Estes commands precisam permanecer independentes de request, ORM e FormView.
"""

from dataclasses import dataclass
from typing import Any

from integrations.whatsapp.contracts import WhatsAppInboundMessage


@dataclass(frozen=True, slots=True)
class RegisterInboundWhatsAppMessageCommand:
    external_message_id: str
    phone: str
    display_name: str
    body: str
    external_contact_id: str = ''
    message_kind: str = 'text'
    raw_payload: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class RegisterOperationalMessageCommand:
    actor_id: int | None
    action_kind: str
    student_id: int
    payment_id: int | None = None
    enrollment_id: int | None = None


@dataclass(frozen=True, slots=True)
class FinanceCommunicationActionCommand:
    actor_id: int | None
    action_kind: str
    student_id: int
    payment_id: int | None = None
    enrollment_id: int | None = None


@dataclass(frozen=True, slots=True)
class BuildOperationalQueueSnapshotCommand:
    limit: int = 9


def build_register_inbound_whatsapp_message_command(
    *, inbound_message: WhatsAppInboundMessage,
) -> RegisterInboundWhatsAppMessageCommand:
    return RegisterInboundWhatsAppMessageCommand(
        external_message_id=inbound_message.external_message_id,
        phone=inbound_message.phone,
        display_name=inbound_message.display_name,
        body=inbound_message.body,
        external_contact_id=inbound_message.external_contact_id,
        message_kind=inbound_message.message_kind,
        raw_payload=inbound_message.raw_payload,
    )


__all__ = [
    'BuildOperationalQueueSnapshotCommand',
    'FinanceCommunicationActionCommand',
    'RegisterInboundWhatsAppMessageCommand',
    'RegisterOperationalMessageCommand',
    'build_register_inbound_whatsapp_message_command',
]
