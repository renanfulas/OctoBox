"""
ARQUIVO: agregador dos papeis de acesso.

POR QUE ELE EXISTE:
- Junta owner, dev, manager e coach em um unico ponto de uso pelo restante do sistema.

O QUE ESTE ARQUIVO FAZ:
1. Reune todas as definicoes de papel.
2. Monta prioridade e mapa de permissoes.
3. Expoe funcoes para descobrir o papel e as capacidades de um usuario.

PONTOS CRITICOS:
- Se a prioridade de papeis mudar, o comportamento de usuarios com multiplos grupos pode mudar.
- As funcoes daqui sao usadas pelo dashboard, layout e comando de bootstrap.
"""

from django.core.cache import cache
from .base import RoleDefinition
from .coach import COACH_PERMISSIONS, COACH_ROLE, ROLE_COACH
from .dev import DEV_PERMISSIONS, DEV_ROLE, ROLE_DEV
from .manager import MANAGER_PERMISSIONS, MANAGER_ROLE, ROLE_MANAGER
from .owner import OWNER_PERMISSIONS, OWNER_ROLE, ROLE_OWNER
from .reception import RECEPTION_PERMISSIONS, RECEPTION_ROLE, ROLE_RECEPTION
from .honeypot import HONEYPOT_PERMISSIONS, HONEYPOT_ROLE, ROLE_HONEYPOT

ROLE_DEFINITIONS = [OWNER_ROLE, DEV_ROLE, MANAGER_ROLE, RECEPTION_ROLE, COACH_ROLE, HONEYPOT_ROLE]
ROLE_MAP = {role.slug: role for role in ROLE_DEFINITIONS}
ROLE_PRIORITY = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER, ROLE_RECEPTION, ROLE_COACH, ROLE_HONEYPOT)
ROLE_PERMISSION_MAP = {
    ROLE_OWNER: OWNER_PERMISSIONS,
    ROLE_DEV: DEV_PERMISSIONS,
    ROLE_MANAGER: MANAGER_PERMISSIONS,
    ROLE_RECEPTION: RECEPTION_PERMISSIONS,
    ROLE_COACH: COACH_PERMISSIONS,
    # Honeypot usa capacidades narrativas de isolamento, nao permissoes reais de modelo.
    ROLE_HONEYPOT: {},
}

_ROLE_CACHE_ATTR = '_octobox_cached_role'


def _build_fallback_role():
    return RoleDefinition(
        slug='SemPapel',
        label='Sem papel definido',
        summary='Usuário autenticado sem escopo formal ainda.',
        capabilities=('Acesso autenticado sem papel de negócio associado.',),
    )


def get_user_role(user):
    if not user.is_authenticated:
        return None

    cached_role = getattr(user, _ROLE_CACHE_ATTR, None)
    if cached_role is not None:
        return cached_role

    if user.is_superuser:
        role = ROLE_MAP[ROLE_OWNER]
        setattr(user, _ROLE_CACHE_ATTR, role)
        return role

    # 🚀 Performance AAA (Shadow Role): Ler do Redis em vez do Banco
    cache_key = f"octobox:user_role_slug:uid_{user.id}"
    cached_slug = cache.get(cache_key)
    
    if cached_slug and cached_slug in ROLE_MAP:
        role = ROLE_MAP[cached_slug]
        setattr(user, _ROLE_CACHE_ATTR, role)
        return role

    group_names = set(user.groups.values_list('name', flat=True))
    for role_name in ROLE_PRIORITY:
        if role_name in group_names:
            role = ROLE_MAP[role_name]
            cache.set(cache_key, role.slug, timeout=86400)
            setattr(user, _ROLE_CACHE_ATTR, role)
            return role

    role = _build_fallback_role()
    setattr(user, _ROLE_CACHE_ATTR, role)
    return role


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
    'ROLE_RECEPTION',
    'ROLE_HONEYPOT',
    'ROLE_PERMISSION_MAP',
    'get_user_capabilities',
    'get_user_role',
]
