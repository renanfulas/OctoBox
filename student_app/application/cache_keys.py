"""
ARQUIVO: chaves de cache do app do aluno.

POR QUE ELE EXISTE:
- Mantem snapshots quentes do app do aluno com nomes previsiveis e isolados por box.

O QUE ESTE ARQUIVO FAZ:
1. Normaliza o box slug usado nas chaves.
2. Constroi chaves versionadas para snapshots de WOD publicado.

PONTOS CRITICOS:
- As chaves nao carregam dados pessoais quando o snapshot e compartilhado por box.
- O prefixo global do Django ainda aplica o namespace do runtime atual.
"""

from __future__ import annotations

from shared_support.box_runtime import normalize_box_runtime_slug


STUDENT_APP_CACHE_NAMESPACE = 'student_app'


def normalize_student_cache_box_slug(box_root_slug: str | None) -> str:
    return normalize_box_runtime_slug(box_root_slug)


def build_student_wod_snapshot_cache_key(*, box_root_slug: str | None, session_id: int, workout_version: int) -> str:
    box_slug = normalize_student_cache_box_slug(box_root_slug)
    return f'{STUDENT_APP_CACHE_NAMESPACE}:wod:v1:{box_slug}:session:{session_id}:version:{workout_version}'


def build_student_agenda_snapshot_cache_key(
    *,
    box_root_slug: str | None,
    start_date,
    window_days: int | None,
    limit: int | None,
) -> str:
    box_slug = normalize_student_cache_box_slug(box_root_slug)
    scope = f'window:{window_days}' if window_days else f'radar:{limit or "all"}'
    return f'{STUDENT_APP_CACHE_NAMESPACE}:agenda:v1:{box_slug}:{start_date}:{scope}'


def build_student_home_snapshot_cache_key(
    *,
    box_root_slug: str | None,
    student_id: int,
    start_date,
    window_days: int | None,
    limit: int | None,
) -> str:
    box_slug = normalize_student_cache_box_slug(box_root_slug)
    scope = f'window:{window_days}' if window_days else f'radar:{limit or "all"}'
    return f'{STUDENT_APP_CACHE_NAMESPACE}:home:v1:{box_slug}:student:{student_id}:{start_date}:{scope}'


def build_student_home_rm_snapshot_cache_key(
    *,
    box_root_slug: str | None,
    student_id: int,
    session_id: int,
) -> str:
    box_slug = normalize_student_cache_box_slug(box_root_slug)
    return f'{STUDENT_APP_CACHE_NAMESPACE}:home-rm:v1:{box_slug}:student:{student_id}:session:{session_id}'


def build_student_rm_snapshot_cache_key(
    *,
    box_root_slug: str | None,
    student_id: int,
) -> str:
    box_slug = normalize_student_cache_box_slug(box_root_slug)
    return f'{STUDENT_APP_CACHE_NAMESPACE}:rm:v1:{box_slug}:student:{student_id}'


__all__ = [
    'build_student_agenda_snapshot_cache_key',
    'build_student_home_snapshot_cache_key',
    'build_student_home_rm_snapshot_cache_key',
    'build_student_rm_snapshot_cache_key',
    'build_student_wod_snapshot_cache_key',
    'normalize_student_cache_box_slug',
]
