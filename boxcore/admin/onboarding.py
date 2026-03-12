"""
ARQUIVO: fachada legada do admin de communications dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto o admin real vive em communications.admin.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta as classes reais do admin de communications.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar registros novos do admin.
"""

from communications.admin import StudentIntakeAdmin, WhatsAppContactAdmin, WhatsAppMessageLogAdmin

__all__ = ['StudentIntakeAdmin', 'WhatsAppContactAdmin', 'WhatsAppMessageLogAdmin']