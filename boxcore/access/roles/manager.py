"""
ARQUIVO: fachada legada do papel Manager dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a implementacao real vive em access.roles.manager.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta a definicao real do papel Manager.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from access.roles.manager import MANAGER_PERMISSIONS, MANAGER_ROLE, ROLE_MANAGER

__all__ = ['MANAGER_PERMISSIONS', 'MANAGER_ROLE', 'ROLE_MANAGER']