"""
ARQUIVO: fachada legada do papel Coach dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a implementacao real vive em access.roles.coach.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta a definicao real do papel Coach.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from access.roles.coach import COACH_PERMISSIONS, COACH_ROLE, ROLE_COACH

__all__ = ['COACH_PERMISSIONS', 'COACH_ROLE', 'ROLE_COACH']