"""
ARQUIVO: fachada legada dos papeis de acesso dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a implementacao real vive em access.roles.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta os papeis e utilitarios reais de acesso.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from access.roles import (
    ROLE_COACH,
    ROLE_DEV,
    ROLE_DEFINITIONS,
    ROLE_MANAGER,
    ROLE_OWNER,
    ROLE_RECEPTION,
    ROLE_PERMISSION_MAP,
    get_user_capabilities,
    get_user_role,
)
from access.roles.base import RoleDefinition
from access.roles.coach import COACH_PERMISSIONS, COACH_ROLE
from access.roles.dev import DEV_PERMISSIONS, DEV_ROLE
from access.roles.manager import MANAGER_PERMISSIONS, MANAGER_ROLE
from access.roles.owner import OWNER_PERMISSIONS, OWNER_ROLE
from access.roles.reception import RECEPTION_PERMISSIONS, RECEPTION_ROLE

__all__ = [
    'COACH_PERMISSIONS',
    'COACH_ROLE',
    'DEV_PERMISSIONS',
    'DEV_ROLE',
    'MANAGER_PERMISSIONS',
    'MANAGER_ROLE',
    'OWNER_PERMISSIONS',
    'OWNER_ROLE',
    'RECEPTION_PERMISSIONS',
    'RECEPTION_ROLE',
    'ROLE_COACH',
    'ROLE_DEV',
    'ROLE_DEFINITIONS',
    'ROLE_MANAGER',
    'ROLE_OWNER',
    'ROLE_RECEPTION',
    'ROLE_PERMISSION_MAP',
    'RoleDefinition',
    'get_user_capabilities',
    'get_user_role',
]