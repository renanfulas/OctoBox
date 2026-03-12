"""
ARQUIVO: fachada legada da estrutura base de acesso dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a implementacao real vive em access.roles.base.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta a estrutura real de papeis.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from access.roles.base import RoleDefinition

__all__ = ['RoleDefinition']