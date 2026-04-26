"""
ARQUIVO: snapshots cacheaveis da agenda compartilhada do app do aluno.

POR QUE ELE EXISTE:
- Evita reconstruir a mesma grade, ocupacao e titulos de WOD para cada aluno.

O QUE ESTE ARQUIVO FAZ:
1. Monta a agenda compartilhada por box e janela de data.
2. Serializa apenas dados comuns a todos os alunos.
3. Mantem reserva, plano e progresso fora do cache compartilhado.

PONTOS CRITICOS:
- Nunca inserir status de presenca do aluno neste snapshot.
- A chave precisa carregar box, data e janela para evitar mistura de superficies.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
import time as perf_time

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, OuterRef, Q, Subquery
from django.utils import timezone

from operations.models import AttendanceStatus, ClassSession
from shared_support.performance import get_cache_ttl_with_jitter
from student_app.application.cache_telemetry import record_student_app_perf
from student_app.application.cache_keys import build_student_agenda_snapshot_cache_key
from student_app.models import SessionWorkout, SessionWorkoutMovement, SessionWorkoutStatus, WorkoutLoadType


AGENDA_OCCUPANCY_STATUSES = (
    AttendanceStatus.BOOKED,
    AttendanceStatus.CHECKED_IN,
    AttendanceStatus.CHECKED_OUT,
)


def _serialize_agenda_session(*, session, workout_titles_by_session_id: dict[int, list[str]]) -> dict:
    occupied_slots = getattr(session, 'occupied_slots', 0) or 0
    capacity = session.capacity or 0
    available_slots = max(capacity - occupied_slots, 0)
    return {
        'session_id': session.id,
        'title': session.title,
        'scheduled_at': session.scheduled_at.isoformat(),
        'duration_minutes': session.duration_minutes or 60,
        'capacity': capacity,
        'occupied_slots': occupied_slots,
        'available_slots': available_slots,
        'notes': session.notes,
        'status': session.status,
        'coach_name': session.coach.get_full_name() if session.coach else 'Equipe OctoBox',
        'workout_titles': tuple(workout_titles_by_session_id.get(session.id, ())),
        'rm_movement_slug': getattr(session, 'rm_movement_slug', '') or '',
        'rm_movement_label': getattr(session, 'rm_movement_label', '') or '',
        'rm_movement_load_value': getattr(session, 'rm_movement_load_value', None),
    }


def _normalize_agenda_snapshot(snapshot: dict) -> dict:
    normalized = dict(snapshot)
    normalized['sessions'] = tuple(
        {
            **session,
            'workout_titles': tuple(session.get('workout_titles', ())),
        }
        for session in snapshot.get('sessions', ())
    )
    return normalized


def get_student_agenda_snapshot(
    *,
    box_root_slug: str | None,
    start_date,
    box_timezone,
    window_days: int | None = None,
    limit: int | None = None,
    request_perf=None,
) -> dict:
    started_at = perf_time.perf_counter()
    cache_key = build_student_agenda_snapshot_cache_key(
        box_root_slug=box_root_slug,
        start_date=start_date,
        window_days=window_days,
        limit=limit,
    )
    cache_lookup_started_at = perf_time.perf_counter()
    cached_snapshot = cache.get(cache_key)
    cache_lookup_ms = (perf_time.perf_counter() - cache_lookup_started_at) * 1000
    if isinstance(cached_snapshot, dict):
        record_student_app_perf(
            request_perf,
            'agenda',
            total_ms=(perf_time.perf_counter() - started_at) * 1000,
            cache_lookup_ms=cache_lookup_ms,
            build_ms=0,
            cache_hit=True,
        )
        return _normalize_agenda_snapshot(cached_snapshot)

    build_started_at = perf_time.perf_counter()
    query_start = timezone.make_aware(datetime.combine(start_date, time.min), box_timezone)
    filters = {
        'status__in': ['scheduled', 'open'],
        'scheduled_at__gte': query_start,
    }
    if window_days and window_days > 0:
        query_end_date = start_date + timedelta(days=window_days - 1)
        filters['scheduled_at__lte'] = timezone.make_aware(datetime.combine(query_end_date, time.max), box_timezone)

    sessions_queryset = (
        ClassSession.objects
        .filter(**filters)
        .select_related('coach')
        .annotate(
            occupied_slots=Count(
                'attendances',
                filter=Q(attendances__status__in=AGENDA_OCCUPANCY_STATUSES),
            ),
            published_workout_title=Subquery(
                SessionWorkout.objects
                .filter(session_id=OuterRef('pk'), status=SessionWorkoutStatus.PUBLISHED)
                .values('title')[:1]
            ),
            rm_movement_slug=Subquery(
                SessionWorkoutMovement.objects
                .filter(
                    block__workout__session_id=OuterRef('pk'),
                    block__workout__status=SessionWorkoutStatus.PUBLISHED,
                    load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
                )
                .order_by('block__sort_order', 'sort_order', 'id')
                .values('movement_slug')[:1]
            ),
            rm_movement_label=Subquery(
                SessionWorkoutMovement.objects
                .filter(
                    block__workout__session_id=OuterRef('pk'),
                    block__workout__status=SessionWorkoutStatus.PUBLISHED,
                    load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
                )
                .order_by('block__sort_order', 'sort_order', 'id')
                .values('movement_label')[:1]
            ),
            rm_movement_load_value=Subquery(
                SessionWorkoutMovement.objects
                .filter(
                    block__workout__session_id=OuterRef('pk'),
                    block__workout__status=SessionWorkoutStatus.PUBLISHED,
                    load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
                )
                .order_by('block__sort_order', 'sort_order', 'id')
                .values('load_value')[:1]
            ),
        )
        .order_by('scheduled_at')
    )
    if limit:
        sessions = tuple(sessions_queryset[:limit])
    else:
        sessions = tuple(sessions_queryset)
    workout_titles_by_session_id: dict[int, list[str]] = {}
    for session in sessions:
        if getattr(session, 'published_workout_title', ''):
            workout_titles_by_session_id.setdefault(session.id, []).append(session.published_workout_title)

    snapshot = {
        'schema_version': 1,
        'box_root_slug': box_root_slug or '',
        'start_date': start_date.isoformat(),
        'window_days': window_days,
        'limit': limit,
        'sessions': tuple(
            _serialize_agenda_session(
                session=session,
                workout_titles_by_session_id=workout_titles_by_session_id,
            )
            for session in sessions
        ),
    }
    ttl = getattr(settings, 'STUDENT_AGENDA_CACHE_TTL_SECONDS', 120)
    cache.set(cache_key, snapshot, timeout=get_cache_ttl_with_jitter(ttl))
    record_student_app_perf(
        request_perf,
        'agenda',
        total_ms=(perf_time.perf_counter() - started_at) * 1000,
        cache_lookup_ms=cache_lookup_ms,
        build_ms=(perf_time.perf_counter() - build_started_at) * 1000,
        cache_hit=False,
    )
    return _normalize_agenda_snapshot(snapshot)


__all__ = [
    'get_student_agenda_snapshot',
]
