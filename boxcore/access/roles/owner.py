"""
ARQUIVO: fachada legada do papel Owner dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a implementacao real vive em access.roles.owner.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta a definicao real do papel Owner.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from access.roles.owner import OWNER_PERMISSIONS, OWNER_ROLE, ROLE_OWNER

__all__ = ['OWNER_PERMISSIONS', 'OWNER_ROLE', 'ROLE_OWNER']