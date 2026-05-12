"""
ARQUIVO: chaves de cache do app do aluno.

POR QUE ELE EXISTE:
- Mantem snapshots quentes do app do aluno com nomes previsiveis e isolados por tenant.

O QUE ESTE ARQUIVO FAZ:
1. Resolve o discriminador de tenant (schema_name) a partir do schema ativo.
2. Constroi chaves versionadas para snapshots de WOD, agenda, home e RM.

SPRINT 3 - MUDANCAS:
- Substituida dependencia de get_box_runtime_slug() / BOX_RUNTIME_SLUG env var.
- Tenant discriminator agora e connection.schema_name (ex: 'box_pilot', 'box_endorfina').
- box_root_slug mantido como parametro opcional de fallback para compat com codigo legado.
- Risco eliminado: duas instancias de tenants com student_id igual nao mais compartilham
  cache key. O schema_name e unico por tenant (garantido pelo django-tenants).
"""

from __future__ import annotations

from django.db import connection


STUDENT_APP_CACHE_NAMESPACE = 'student_app'


def get_active_tenant_slug(fallback: str | None = None) -> str:
    """Retorna o schema_name do tenant ativo como discriminador de cache.

    Sprint 3: usa connection.schema_name (django-tenants) em vez de
    get_box_runtime_slug() (BOX_RUNTIME_SLUG env var, que era single-box).

    Fallback order:
    1. connection.schema_name se em contexto de tenant (ex: 'box_pilot')
    2. fallback se fornecido (box_root_slug legado)
    3. 'public' (nao e tenant)
    """
    schema = getattr(connection, 'schema_name', None)
    if schema and schema != 'public':
        return schema
    if fallback and fallback.strip() and fallback.strip() not in ('control', 'public'):
        normalized = fallback.strip().lower().replace(' ', '-')
        if not normalized.startswith('box_') and not normalized.startswith('archived_box_'):
            normalized = f'box_{normalized}'
        return normalized
    return schema or 'public'


def normalize_student_cache_box_slug(box_root_slug: str | None) -> str:
    """DEPRECATED: usar get_active_tenant_slug() diretamente.
    Mantido para compat enquanto box_root_slug ainda circula pelo codigo legado.
    """
    return get_active_tenant_slug(fallback=box_root_slug)


def build_student_wod_snapshot_cache_key(*, box_root_slug: str | None, session_id: int, workout_version: int) -> str:
    tenant = get_active_tenant_slug(fallback=box_root_slug)
    return f'{STUDENT_APP_CACHE_NAMESPACE}:wod:v1:{tenant}:session:{session_id}:version:{workout_version}'


def build_student_agenda_snapshot_cache_key(
    *,
    box_root_slug: str | None,
    start_date,
    window_days: int | None,
    limit: int | None,
) -> str:
    tenant = get_active_tenant_slug(fallback=box_root_slug)
    scope = f'window:{window_days}' if window_days else f'radar:{limit or "all"}'
    return f'{STUDENT_APP_CACHE_NAMESPACE}:agenda:v1:{tenant}:{start_date}:{scope}'


def build_student_home_snapshot_cache_key(
    *,
    box_root_slug: str | None,
    student_id: int,
    start_date,
    window_days: int | None,
    limit: int | None,
) -> str:
    tenant = get_active_tenant_slug(fallback=box_root_slug)
    scope = f'window:{window_days}' if window_days else f'radar:{limit or "all"}'
    return f'{STUDENT_APP_CACHE_NAMESPACE}:home:v1:{tenant}:student:{student_id}:{start_date}:{scope}'


def build_student_home_rm_snapshot_cache_key(
    *,
    box_root_slug: str | None,
    student_id: int,
    session_id: int,
) -> str:
    tenant = get_active_tenant_slug(fallback=box_root_slug)
    return f'{STUDENT_APP_CACHE_NAMESPACE}:home-rm:v1:{tenant}:student:{student_id}:session:{session_id}'


def build_student_rm_snapshot_cache_key(
    *,
    box_root_slug: str | None,
    student_id: int,
) -> str:
    tenant = get_active_tenant_slug(fallback=box_root_slug)
    return f'{STUDENT_APP_CACHE_NAMESPACE}:rm:v1:{tenant}:student:{student_id}'


__all__ = [
    'build_student_agenda_snapshot_cache_key',
    'build_student_home_snapshot_cache_key',
    'build_student_home_rm_snapshot_cache_key',
    'build_student_rm_snapshot_cache_key',
    'build_student_wod_snapshot_cache_key',
    'get_active_tenant_slug',
    'normalize_student_cache_box_slug',
]
