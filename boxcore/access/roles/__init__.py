"""
ARQUIVO: agregador dos papéis de acesso.

POR QUE ELE EXISTE:
- Junta owner, dev, manager e coach em um único ponto de uso pelo restante do sistema.

O QUE ESTE ARQUIVO FAZ:
1. Reúne todas as definições de papel.
2. Monta prioridade e mapa de permissões.
3. Expõe funções para descobrir o papel e as capacidades de um usuário.

PONTOS CRITICOS:
- Se a prioridade de papéis mudar, o comportamento de usuários com múltiplos grupos pode mudar.
- As funções daqui são usadas pelo dashboard, layout e comando de bootstrap.
"""

from .base import RoleDefinition
from .coach import COACH_PERMISSIONS, COACH_ROLE, ROLE_COACH
from .dev import DEV_PERMISSIONS, DEV_ROLE, ROLE_DEV
from .manager import MANAGER_PERMISSIONS, MANAGER_ROLE, ROLE_MANAGER
from .owner import OWNER_PERMISSIONS, OWNER_ROLE, ROLE_OWNER

ROLE_DEFINITIONS = [OWNER_ROLE, DEV_ROLE, MANAGER_ROLE, COACH_ROLE]
ROLE_MAP = {role.slug: role for role in ROLE_DEFINITIONS}
# A prioridade resolve conflitos quando um usuário pertence a mais de um grupo.
ROLE_PRIORITY = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER, ROLE_COACH)
ROLE_PERMISSION_MAP = {
    ROLE_OWNER: OWNER_PERMISSIONS,
    ROLE_DEV: DEV_PERMISSIONS,
    ROLE_MANAGER: MANAGER_PERMISSIONS,
    ROLE_COACH: COACH_PERMISSIONS,
}


def get_user_role(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return ROLE_MAP[ROLE_OWNER]

    # O primeiro grupo encontrado na prioridade acima vence e define o papel efetivo.
    group_names = set(user.groups.values_list('name', flat=True))
    for role_name in ROLE_PRIORITY:
        if role_name in group_names:
            return ROLE_MAP[role_name]

    # Mantém o sistema estável mesmo se o usuário ainda não tiver grupo atribuído.
    return RoleDefinition(
        slug='SemPapel',
        label='Sem papel definido',
        summary='Usuário autenticado sem escopo formal ainda.',
        capabilities=('Acesso autenticado sem papel de negócio associado.',),
    )


def get_user_capabilities(user):
    role = get_user_role(user)
    if role is None:
        return ()
    return role.capabilities


__all__ = [
    'ROLE_COACH',
    'ROLE_DEV',
    'ROLE_DEFINITIONS',
    'ROLE_MANAGER',
    'ROLE_OWNER',
    'ROLE_PERMISSION_MAP',
    'get_user_capabilities',
    'get_user_role',
]