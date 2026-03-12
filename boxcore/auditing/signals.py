"""
ARQUIVO: fachada legada dos sinais de auditoria dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a implementacao real vive em auditing.signals.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta os sinais reais de auditoria.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from auditing.signals import audit_user_logged_in, audit_user_logged_out

__all__ = ['audit_user_logged_in', 'audit_user_logged_out']