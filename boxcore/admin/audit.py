"""
ARQUIVO: fachada legada do admin de auditoria dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a configuracao real vive em auditing.admin.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta a classe real de admin de auditoria.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from auditing.admin import AuditEventAdmin


__all__ = ['AuditEventAdmin']