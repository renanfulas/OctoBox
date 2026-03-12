"""
ARQUIVO: fachada legada do papel DEV dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a implementacao real vive em access.roles.dev.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta a definicao real do papel DEV.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from access.roles.dev import DEV_PERMISSIONS, DEV_ROLE, ROLE_DEV

__all__ = ['DEV_PERMISSIONS', 'DEV_ROLE', 'ROLE_DEV']