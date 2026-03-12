"""
ARQUIVO: fachada do registro inbound de WhatsApp.

POR QUE ELE EXISTE:
- Mantem o contrato publico atual enquanto o fluxo real foi extraido para command, use case e adapter Django.

O QUE ESTE ARQUIVO FAZ:
1. Traduz o DTO inbound para um command explicito.
2. Chama o use case concreto de communications.
3. Devolve o contrato publico historico da integracao.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar ORM, transacao ou regra de reconciliacao.
"""

from communications.application.commands import build_register_inbound_whatsapp_message_command
from communications.infrastructure import execute_register_inbound_whatsapp_message_command

from .contracts import WhatsAppInboundMessage, WhatsAppWebhookProcessingResult


def register_inbound_whatsapp_message(*, inbound_message: WhatsAppInboundMessage):
    command = build_register_inbound_whatsapp_message_command(inbound_message=inbound_message)
    result = execute_register_inbound_whatsapp_message_command(command)
    return WhatsAppWebhookProcessingResult(
        accepted=result.accepted,
        reason=result.reason,
        contact_id=result.contact_id,
        message_log_id=result.message_log_id,
    )
