"""
ARQUIVO: fachada legada dos services de communications dentro do catalogo.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a implementacao real vive em communications.services.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta os services reais de communications.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from communications.services import (
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