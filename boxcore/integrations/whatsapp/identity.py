"""
ARQUIVO: fachada legada da identidade de canal do WhatsApp dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a implementacao real vive em integrations.whatsapp.identity.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta a identidade real do canal.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from integrations.whatsapp.identity import WhatsAppChannelIdentity, resolve_whatsapp_channel_identity

__all__ = ['WhatsAppChannelIdentity', 'resolve_whatsapp_channel_identity']