"""
ARQUIVO: fachada legada do saneamento de payloads do WhatsApp dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a implementacao real vive em integrations.whatsapp.payloads.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta o saneamento real do canal.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from integrations.whatsapp.payloads import sanitize_whatsapp_payload

__all__ = ['sanitize_whatsapp_payload']