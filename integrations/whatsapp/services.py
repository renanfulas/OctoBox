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

from communications.facade import run_register_inbound_whatsapp_message

from .contracts import WhatsAppInboundMessage, WhatsAppInboundPollVote, WhatsAppWebhookProcessingResult
from .poll_processor import process_poll_vote_webhook as run_process_poll_vote_webhook


def register_inbound_whatsapp_message(*, inbound_message: WhatsAppInboundMessage):
    result = run_register_inbound_whatsapp_message(inbound_message=inbound_message)
    return WhatsAppWebhookProcessingResult(
        accepted=result.accepted,
        reason=result.reason,
        contact_id=result.contact_id,
        message_log_id=result.message_log_id,
    )


def process_poll_vote_webhook(*, poll_vote: WhatsAppInboundPollVote) -> WhatsAppWebhookProcessingResult:
    """
    Processa um voto de enquete do WhatsApp para registrar presenca.
    """
    # Encaminha para o processador dedicado
    return run_process_poll_vote_webhook(poll_vote=poll_vote)
