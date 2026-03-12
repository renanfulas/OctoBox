"""
ARQUIVO: fachada legada dos mixins de permissao de acesso dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a implementacao real vive em access.permissions.mixins.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta os mixins reais de permissao.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from access.permissions.mixins import RoleRequiredMixin

__all__ = ['RoleRequiredMixin']