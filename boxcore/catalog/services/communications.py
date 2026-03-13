"""
ARQUIVO: fachada legada dos services de communications dentro do catalogo.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a superficie canonica vive em catalog.services.communications.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta a entrada publica atual do catalogo.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from catalog.services.communications import (
    build_message_body,
    ensure_whatsapp_contact,
    normalize_payment_status,
    register_operational_message,
)

__all__ = [
    'build_message_body',
    'ensure_whatsapp_contact',
    'normalize_payment_status',
    'register_operational_message',
]