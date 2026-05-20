"""
ARQUIVO: invalidacao de cache do app do aluno.

POR QUE ELE EXISTE:
- Mantem snapshots compartilhados coerentes quando aula, presenca ou WOD mudam.

O QUE ESTE ARQUIVO FAZ:
1. Remove snapshots de agenda por box e data.
2. Usa delete pattern quando o backend suporta Redis.
3. Mantem fallback explicito para cache local em desenvolvimento e testes.

PONTOS CRITICOS:
- Invalidacao deve ser ampla o suficiente para proteger consistencia visual.
- Escritas continuam sendo a fonte de verdade; cache e apenas acelerador.
"""

from __future__ import annotations

from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone

# Sprint 3: get_box_runtime_slug substituido por get_active_tenant_slug (connection.schema_name)
from student_app.application.cache_keys import (
    build_student_agenda_snapshot_cache_key,
    build_student_home_rm_snapshot_cache_key,
    build_student_home_snapshot_cache_key,
    build_student_rm_snapshot_cache_key,
    get_active_tenant_slug,
    normalize_student_cache_box_slug,
)
from student_app.application.timezone import localize_box_datetime


def resolve_student_box_slug(student=None, fallback: str | None = None) -> str:
    # Sprint 3: prioridade: (1) connection.schema_name, (2) identity.box_root_slug, (3) fallback
    # get_active_tenant_slug ja resolve connection.schema_name com fallback para box_root_slug
    identity = getattr(student, 'app_identity', None) if student is not None else None
    identity_slug = getattr(identity, 'box_root_slug', '') if identity is not None else ''
    return get_active_tenant_slug(fallback=identity_slug or fallback)


def invalidate_student_agenda_snapshots(*, box_root_slug: str | None, session_scheduled_at=None):
    box_slug = normalize_student_cache_box_slug(box_root_slug)
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern(f'*student_app:agenda:v1:{box_slug}:*')
        return

    if session_scheduled_at is not None:
        center_date = localize_box_datetime(session_scheduled_at, box_root_slug=box_slug).date()
        dates = [center_date + timedelta(days=offset) for offset in range(-7, 8)]
    else:
        dates = []

    keys = []
    for date_value in dates:
        keys.append(
            build_student_agenda_snapshot_cache_key(
                box_root_slug=box_slug,
                start_date=date_value,
                window_days=None,
                limit=12,
            )
        )
        for window_days in (1, 2, 7):
            keys.append(
                build_student_agenda_snapshot_cache_key(
                    box_root_slug=box_slug,
                    start_date=date_value,
                    window_days=window_days,
                    limit=None,
                )
            )
    if keys:
        cache.delete_many(keys)


def invalidate_student_home_snapshots(*, box_root_slug: str | None, student_id: int | None = None):
    box_slug = normalize_student_cache_box_slug(box_root_slug)
    if hasattr(cache, 'delete_pattern'):
        if student_id is None:
            cache.delete_pattern(f'*student_app:home:v1:{box_slug}:student:*')
            cache.delete_pattern(f'*student_app:home-rm:v1:{box_slug}:student:*')
        else:
            cache.delete_pattern(f'*student_app:home:v1:{box_slug}:student:{student_id}:*')
            cache.delete_pattern(f'*student_app:home-rm:v1:{box_slug}:student:{student_id}:*')
        return

    if student_id is None:
        # Em backends simples sem delete_pattern, limpar o cache inteiro derruba
        # tambem as sessoes do Django, o que invalida corredores operacionais
        # nao relacionados. Nesses ambientes aceitamos o TTL curto do home-rm.
        return

    keys = []
    today = localize_box_datetime(timezone.now(), box_root_slug=box_slug).date()
    date_window = [today + timedelta(days=offset) for offset in range(-7, 8)]
    for date_value in date_window:
        keys.append(
            build_student_home_snapshot_cache_key(
                box_root_slug=box_slug,
                student_id=student_id,
                start_date=date_value,
                window_days=None,
                limit=12,
            )
        )
        for window_days in (1, 2, 7):
            keys.append(
                build_student_home_snapshot_cache_key(
                    box_root_slug=box_slug,
                    student_id=student_id,
                    start_date=date_value,
                    window_days=window_days,
                    limit=None,
                )
            )

    # Sprint 4 fix: queriar session_ids reais da janela em vez de iterar
    # range(1, 65). Em DEV/test o auto-increment de ClassSession acumula
    # entre runs e ja passa de 64 cedo — testes de invalidacao de RM
    # snapshot falhavam porque o session_id real estava fora da range
    # hardcoded, e a chave do cache nunca era apagada.
    try:
        from operations.models import ClassSession
        from datetime import datetime, time
        from django.utils.timezone import make_aware, get_current_timezone
        tz = get_current_timezone()
        window_start = make_aware(datetime.combine(date_window[0], time.min), tz)
        window_end = make_aware(datetime.combine(date_window[-1], time.max), tz)
        session_ids = list(
            ClassSession.objects
            .filter(scheduled_at__gte=window_start, scheduled_at__lte=window_end)
            .values_list('id', flat=True)
        )
    except Exception:
        session_ids = []
    for session_id in session_ids:
        keys.append(
            build_student_home_rm_snapshot_cache_key(
                box_root_slug=box_slug,
                student_id=student_id,
                session_id=session_id,
            )
        )
    if keys:
        cache.delete_many(keys)


def invalidate_student_rm_snapshots(*, box_root_slug: str | None, student_id: int | None = None):
    box_slug = normalize_student_cache_box_slug(box_root_slug)
    if hasattr(cache, 'delete_pattern'):
        if student_id is None:
            cache.delete_pattern(f'*student_app:rm:v1:{box_slug}:student:*')
        else:
            cache.delete_pattern(f'*student_app:rm:v1:{box_slug}:student:{student_id}')
        return

    if student_id is None:
        return
        return

    cache.delete(
        build_student_rm_snapshot_cache_key(
            box_root_slug=box_slug,
            student_id=student_id,
        )
    )


__all__ = [
    'invalidate_student_agenda_snapshots',
    'invalidate_student_home_snapshots',
    'invalidate_student_rm_snapshots',
    'resolve_student_box_slug',
]
