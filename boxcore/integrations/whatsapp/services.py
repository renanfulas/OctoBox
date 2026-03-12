"""
ARQUIVO: fachada legada dos servicos de WhatsApp dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a implementacao real vive em integrations.whatsapp.services.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta os servicos reais do canal.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from integrations.whatsapp.services import register_inbound_whatsapp_message

__all__ = ['register_inbound_whatsapp_message']