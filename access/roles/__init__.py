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
- Onda 1c (2026-08-25): get_user_role passou a resolver papel POR BOX via
  Membership, nao mais so por auth.Group global. Ver ordem de precedencia
  documentada dentro de get_user_role — a ordem importa e foi desenhada
  para nao quebrar honeypot nem superusuario sem Membership.
"""

from shared_support.platform_cache import platform_cache as cache
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

# Espelha control.models.Membership.Role.values -> slug de RoleDefinition.
# Nao importamos Membership aqui em top-level (control e SHARED_APP, access e
# TENANT_APP — mesma cautela de "import local para evitar circular no boot"
# documentada em control/middleware.py). test_control_services.py tem um
# teste que verifica os dois lados continuam em sincronia se algum dia
# divergirem (adicionar um Role novo sem adicionar aqui, ou vice-versa).
MEMBERSHIP_ROLE_TO_SLUG = {
    'owner': ROLE_OWNER,
    'manager': ROLE_MANAGER,
    'coach': ROLE_COACH,
    'reception': ROLE_RECEPTION,
    'dev': ROLE_DEV,
}

# Inverso do mapa acima — usado por access_profile_actions.py (Onda 1-pré)
# para criar/atualizar Membership.role a partir do slug escolhido no form de
# papel. Não cobre ROLE_HONEYPOT de propósito: não é um papel atribuível por
# formulário (OPERATIONAL_ROLE_CHOICES já filtra honeypot fora), e não tem
# Membership.Role equivalente — resolução de honeypot nunca passa por
# Membership (ver ordem de precedência em get_user_role).
SLUG_TO_MEMBERSHIP_ROLE = {slug: role for role, slug in MEMBERSHIP_ROLE_TO_SLUG.items()}

_ROLE_CACHE_ATTR = '_octobox_cached_role'
_SHADOW_ROLE_CACHE_PREFIX = 'octobox:user_role_slug:uid_'


def _build_fallback_role():
    return RoleDefinition(
        slug='SemPapel',
        label='Sem papel definido',
        summary='Usuário autenticado sem escopo formal ainda.',
        capabilities=('Acesso autenticado sem papel de negócio associado.',),
    )


def get_user_role(user):
    """Resolve o papel efetivo do usuário.

    ORDEM DE PRECEDÊNCIA (cada uma existe por um motivo específico — não
    reordenar sem reler os três comentários abaixo):

    1. Cache de instância (_ROLE_CACHE_ATTR) — evita reconsulta no mesmo
       request quando get_user_role é chamado várias vezes (é comum:
       context processor + mixin + template).

    2. Honeypot — shared_support/security/honeypot_service.py marca um
       usuário sobrescrevendo A MESMA chave de cache que o fallback de
       Group usa (`octobox:user_role_slug:uid_{id}`), de propósito, para
       o "cargo real" parar de ser lido por 24h. Isso PRECISA ser checado
       antes de qualquer resolução por Membership — senão um atacante
       marcado, mas com Membership legítima num box, escaparia do labirinto
       assim que Membership passasse a ganhar precedência.
       Onda 4, Passo 3 (2026-08-26): essa chave é indexada por user.id
       (auth_user só existe em public) — vive no alias 'platform' de
       CACHES, sem KEY_FUNCTION, de propósito. Nunca mover para o alias
       'default' (particionado por schema): um atacante marcado escaparia
       do labirinto trocando de box, e a invalidação por Group (Passo 3
       também move access/signals.py) pararia de alcançar a chave certa.

    3. Membership do box ativo (por box) — anexado em request.user por
       control.middleware.TenantBySessionMiddleware via
       OCTOBOX_MEMBERSHIP_REQUEST_ATTR. Ausente (cai para o próximo passo)
       quando: path sem tenant resolvido (PUBLIC_SCHEMA_PATHS), actor
       reconstruído fora de request (auditoria, scripts), ou staff ainda
       não migrado pelo backfill de Onda 1-pré.

    4. is_superuser → Owner — SÓ depois de checar Membership, não antes.
       Superdev (is_superuser=True) passou a ter Membership(role=DEV) em
       todo box (ADR-013 caminho least-privilege) — se este passo viesse
       antes do 3, o Membership dele nunca teria efeito e a promessa de
       "least-privilege" seria cosmética, exatamente como o ADR-013
       documentava como problema. Superusuário SEM Membership nenhuma
       (conta break-glass criada via createsuperuser) ainda cai aqui.

    5. Cache de Group (Shadow Role) e busca em auth.Group — fallback legado
       para quem ainda não tem Membership (staff pré-backfill).

    6. 'SemPapel' — nada resolveu.
    """
    if not user.is_authenticated:
        return None

    cached_role = getattr(user, _ROLE_CACHE_ATTR, None)
    if cached_role is not None:
        return cached_role

    cache_key = f'{_SHADOW_ROLE_CACHE_PREFIX}{user.id}'
    cached_slug = cache.get(cache_key)

    # Passo 2 — honeypot vence tudo. Único slug que este cache pode conter
    # sem ter vindo do fallback de Group abaixo (que só grava seu PRÓPRIO
    # resultado ali).
    if cached_slug == ROLE_HONEYPOT:
        role = ROLE_MAP[ROLE_HONEYPOT]
        setattr(user, _ROLE_CACHE_ATTR, role)
        return role

    # Passo 3 — Membership do box ativo, anexado pelo middleware.
    membership = _get_attached_membership(user)
    if membership is not None:
        role_slug = MEMBERSHIP_ROLE_TO_SLUG.get(membership.role)
        if role_slug and role_slug in ROLE_MAP:
            role = ROLE_MAP[role_slug]
            setattr(user, _ROLE_CACHE_ATTR, role)
            return role

    # Passo 4 — superusuário sem Membership resolvida (ou sem Membership
    # nenhuma): mantém o comportamento legado.
    if user.is_superuser:
        role = ROLE_MAP[ROLE_OWNER]
        setattr(user, _ROLE_CACHE_ATTR, role)
        return role

    # Passo 5 — Shadow Role (cache de Group) + fallback em auth.Group.
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


def _get_attached_membership(user):
    """Lê o Membership anexado por TenantBySessionMiddleware, se houver.

    Import tardio de control.middleware só pela constante (string), nunca do
    model — sem risco de circular no boot mesmo assim, mas mantém o padrão
    "import local" já usado no resto do projeto para tudo que cruza a
    fronteira SHARED_APP (control) -> TENANT_APP (access).
    """
    from control.middleware import OCTOBOX_MEMBERSHIP_REQUEST_ATTR

    return getattr(user, OCTOBOX_MEMBERSHIP_REQUEST_ATTR, None)


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
    'MEMBERSHIP_ROLE_TO_SLUG',
    'SLUG_TO_MEMBERSHIP_ROLE',
    'get_user_capabilities',
    'get_user_role',
]
