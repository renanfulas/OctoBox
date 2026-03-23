"""
ARQUIVO: contratos normalizados para integracao com WhatsApp.

POR QUE ELE EXISTE:
- Cria tipos de dados estaveis para integrar o canal sem espalhar payload bruto pelo sistema.

O QUE ESTE ARQUIVO FAZ:
1. Define mensagens de entrada normalizadas.
2. Define comandos de saida normalizados.
3. Define resultado resumido de processamento de webhook.

PONTOS CRITICOS:
- Tipos daqui devem permanecer independentes do payload cru de cada provedor.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class WhatsAppInboundMessage:
    external_message_id: str
    phone: str
    display_name: str
    body: str
    external_contact_id: str = ''
    message_kind: str = 'text'
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WhatsAppOutboundMessage:
    phone: str
    body: str
    message_kind: str = 'text'
    template_name: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WhatsAppWebhookProcessingResult:
    accepted: bool
    reason: str = ''
    contact_id: int | None = None
    message_log_id: int | None = None


@dataclass(slots=True)
class WhatsAppInboundPollVote:
    phone: str           # +55119...
    poll_title: str      # ex: "Check in - 23.MAR"
    option_voted: str    # ex: "18h" ou "19h"
    external_id: str = '' # id do voto ou da mensagem
    raw_payload: dict[str, Any] = field(default_factory=dict)
