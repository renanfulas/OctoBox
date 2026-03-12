"""
ARQUIVO: fachada legada dos models de communications dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem o estado historico do Django em boxcore enquanto a implementacao real dos models de WhatsApp vive fora deste pacote.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta enums e models reais de WhatsApp.
2. Preserva imports antigos durante a transicao.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar implementacao real dos models.
- O app label continua sendo boxcore nesta etapa para evitar mudanca de schema e de migrations.
"""

from communications.model_definitions.whatsapp import (
    MessageDirection,
    MessageKind,
    WhatsAppContact,
    WhatsAppContactStatus,
    WhatsAppMessageLog,
)

__all__ = [
    'MessageDirection',
    'MessageKind',
    'WhatsAppContact',
    'WhatsAppContactStatus',
    'WhatsAppMessageLog',
]