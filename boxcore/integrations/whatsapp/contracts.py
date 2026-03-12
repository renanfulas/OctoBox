"""
ARQUIVO: fachada legada dos contratos de WhatsApp dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto os contratos reais vivem em integrations.whatsapp.contracts.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta os contratos reais do canal.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from integrations.whatsapp.contracts import (
    WhatsAppInboundMessage,
    WhatsAppOutboundMessage,
    WhatsAppWebhookProcessingResult,
)

__all__ = [
    'WhatsAppInboundMessage',
    'WhatsAppOutboundMessage',
    'WhatsAppWebhookProcessingResult',
]