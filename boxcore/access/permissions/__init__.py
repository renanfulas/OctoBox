"""
ARQUIVO: fachada legada das permissoes de acesso dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a implementacao real vive em access.permissions.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta os utilitarios reais de permissao.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from access.permissions import RoleRequiredMixin

__all__ = ['RoleRequiredMixin']