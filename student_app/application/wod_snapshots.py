"""
ARQUIVO: snapshots cacheaveis de WOD publicado para o app do aluno.

POR QUE ELE EXISTE:
- Entrega o treino publicado como payload JSON-safe antes da personalizacao por aluno.

O QUE ESTE ARQUIVO FAZ:
1. Busca o WOD publicado por sessao.
2. Usa cache versionado por `workout.version`.
3. Serializa blocos e movimentos sem ORM cru.

PONTOS CRITICOS:
- O snapshot compartilhado nao contem RM, reserva ou qualquer estado pessoal do aluno.
- A recomendacao de carga continua sendo calculada depois, fora do cache compartilhado.
"""

from __future__ import annotations

from decimal import Decimal
import time as perf_time

from django.conf import settings
from django.core.cache import cache
from django.db.models import prefetch_related_objects

from shared_support.performance import get_cache_ttl_with_jitter
from student_app.application.cache_telemetry import record_student_app_perf
from student_app.application.cache_keys import build_student_wod_snapshot_cache_key
from student_app.models import SessionWorkout, SessionWorkoutStatus


def _decimal_to_cache(value):
    return str(value) if value is not None else None


def _decimal_from_cache(value):
    if value in (None, ''):
        return None
    return Decimal(str(value))


def _serialize_student_workout_snapshot(*, workout, box_root_slug: str | None) -> dict:
    prefetch_related_objects([workout], 'blocks__movements')
    session = workout.session
    coach = session.coach
    coach_name = coach.get_full_name() if coach else ''
    return {
        'schema_version': 1,
        'box_root_slug': box_root_slug or '',
        'session_id': session.id,
        'session_title': session.title,
        'session_scheduled_at': session.scheduled_at.isoformat(),
        'coach_name': coach_name or 'Equipe OctoBox',
        'workout_id': workout.id,
        'workout_version': workout.version,
        'workout_title': workout.title or session.title,
        'coach_notes': workout.coach_notes,
        'blocks': [
            {
                'title': block.title,
                'kind': block.kind,
                'kind_label': block.get_kind_display(),
                'notes': block.notes,
                'sort_order': block.sort_order,
                'movements': [
                    {
                        'movement_slug': movement.movement_slug,
                        'movement_label': movement.movement_label,
                        'sets': movement.sets,
                        'reps': movement.reps,
                        'load_type': movement.load_type,
                        'load_value': _decimal_to_cache(movement.load_value),
                        'notes': movement.notes,
                        'sort_order': movement.sort_order,
                    }
                    for movement in block.movements.all()
                ],
            }
            for block in workout.blocks.all()
        ],
    }


def normalize_student_workout_snapshot(snapshot: dict) -> dict:
    normalized_blocks = []
    for block in snapshot.get('blocks', ()):
        normalized_movements = []
        for movement in block.get('movements', ()):
            normalized_movement = dict(movement)
            normalized_movement['load_value'] = _decimal_from_cache(movement.get('load_value'))
            normalized_movements.append(normalized_movement)
        normalized_block = dict(block)
        normalized_block['movements'] = tuple(normalized_movements)
        normalized_blocks.append(normalized_block)
    normalized = dict(snapshot)
    normalized['blocks'] = tuple(normalized_blocks)
    return normalized


def get_published_student_workout_snapshot(*, session_id: int, box_root_slug: str | None, request_perf=None) -> dict | None:
    started_at = perf_time.perf_counter()
    workout = (
        SessionWorkout.objects
        .select_related('session', 'session__coach')
        .only(
            'id',
            'session_id',
            'status',
            'title',
            'coach_notes',
            'version',
            'session__id',
            'session__title',
            'session__scheduled_at',
            'session__coach__id',
            'session__coach__first_name',
            'session__coach__last_name',
            'session__coach__username',
        )
        .filter(session_id=session_id, status=SessionWorkoutStatus.PUBLISHED)
        .first()
    )
    if workout is None:
        return None

    cache_key = build_student_wod_snapshot_cache_key(
        box_root_slug=box_root_slug,
        session_id=session_id,
        workout_version=workout.version,
    )
    cache_lookup_started_at = perf_time.perf_counter()
    cached_snapshot = cache.get(cache_key)
    cache_lookup_ms = (perf_time.perf_counter() - cache_lookup_started_at) * 1000
    if isinstance(cached_snapshot, dict):
        record_student_app_perf(
            request_perf,
            'wod-shared',
            total_ms=(perf_time.perf_counter() - started_at) * 1000,
            cache_lookup_ms=cache_lookup_ms,
            build_ms=0,
            cache_hit=True,
        )
        return normalize_student_workout_snapshot(cached_snapshot)

    build_started_at = perf_time.perf_counter()
    snapshot = _serialize_student_workout_snapshot(workout=workout, box_root_slug=box_root_slug)
    ttl = getattr(settings, 'STUDENT_WOD_CACHE_TTL_SECONDS', 21600)
    cache.set(cache_key, snapshot, timeout=get_cache_ttl_with_jitter(ttl))
    record_student_app_perf(
        request_perf,
        'wod-shared',
        total_ms=(perf_time.perf_counter() - started_at) * 1000,
        cache_lookup_ms=cache_lookup_ms,
        build_ms=(perf_time.perf_counter() - build_started_at) * 1000,
        cache_hit=False,
    )
    return normalize_student_workout_snapshot(snapshot)


__all__ = [
    'get_published_student_workout_snapshot',
    'normalize_student_workout_snapshot',
]
