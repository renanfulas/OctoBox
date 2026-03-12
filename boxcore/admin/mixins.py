"""
ARQUIVO: fachada legada dos mixins de auditoria do admin dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a implementacao real vive em auditing.admin_mixins.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta o mixin real de auditoria do admin.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from auditing.admin_mixins import AuditedAdminMixin

__all__ = ['AuditedAdminMixin']