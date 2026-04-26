"""
ARQUIVO: envelope personalizado curto da Home do app do aluno.

POR QUE ELE EXISTE:
- Evita refazer a mesma leitura pessoal da Home a cada request quente.

O QUE ESTE ARQUIVO FAZ:
1. Monta o estado pessoal do aluno para a Home em payload JSON-safe.
2. Mantem o snapshot curto, com TTL baixo e invalidacao por eventos.
3. Separa o que e compartilhado por box do que pertence ao aluno.

PONTOS CRITICOS:
- Este cache nao decide reservas; ele apenas acelera leitura.
- O payload deve continuar pequeno e dependente da janela da agenda.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
import time as perf_time

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q

from finance.models import Enrollment, EnrollmentStatus
from operations.models import Attendance, AttendanceStatus
from student_app.application.cache_telemetry import record_student_app_perf
from student_app.application.cache_keys import (
    build_student_home_rm_snapshot_cache_key,
    build_student_home_snapshot_cache_key,
)
from shared_support.performance import get_cache_ttl_with_jitter
from student_app.application.results import StudentProgressDay, StudentRmOfTheDay
from student_app.application.rm_snapshots import build_student_rm_record_map
from student_app.domain.workout_prescription import build_workout_prescription
from student_app.models import SessionWorkoutMovement, SessionWorkoutStatus, StudentAppActivity, WorkoutLoadType


ACTIVE_ATTENDANCE_CODES = (
    AttendanceStatus.BOOKED,
    AttendanceStatus.CHECKED_IN,
    AttendanceStatus.CHECKED_OUT,
)


def _decimal_to_cache(value):
    return str(value) if value is not None else None


def _decimal_from_cache(value):
    if value in (None, ''):
        return None
    return Decimal(str(value))


def _serialize_progress_days(progress_days) -> tuple[dict, ...]:
    return tuple(
        {
            'date': item.date.isoformat(),
            'is_complete': item.is_complete,
            'kind': item.kind,
            'day_label': item.day_label,
            'date_label': item.date_label,
            'is_today': item.is_today,
        }
        for item in progress_days
    )


def _deserialize_progress_days(payload) -> tuple[StudentProgressDay, ...]:
    from datetime import date

    return tuple(
        StudentProgressDay(
            date=date.fromisoformat(item['date']),
            is_complete=item['is_complete'],
            kind=item['kind'],
            day_label=item['day_label'],
            date_label=item['date_label'],
            is_today=item['is_today'],
        )
        for item in payload
    )


def build_student_progress_days(*, student, now) -> tuple[StudentProgressDay, ...]:
    today = now.date()
    days = [today + timedelta(days=offset) for offset in range(7)]
    activity_rows = (
        StudentAppActivity.objects
        .filter(student=student, activity_date__in=days)
        .order_by('activity_date', 'created_at')
        .values_list('activity_date', 'kind')
    )
    activity_by_day = {}
    for activity_date, kind in activity_rows:
        activity_by_day.setdefault(activity_date, kind)
    return tuple(
        StudentProgressDay(
            date=day,
            is_complete=day in activity_by_day,
            kind=activity_by_day.get(day, ''),
            day_label='Hoje' if day == today else ('Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom')[day.weekday()],
            date_label=day.strftime('%d/%m'),
            is_today=day == today,
        )
        for day in days
    )


def _serialize_rm_of_the_day(rm_of_the_day: StudentRmOfTheDay | None) -> dict | None:
    if rm_of_the_day is None:
        return None
    return {
        'exercise_slug': rm_of_the_day.exercise_slug,
        'exercise_label': rm_of_the_day.exercise_label,
        'one_rep_max_kg': _decimal_to_cache(rm_of_the_day.one_rep_max_kg),
        'recommended_load_kg': _decimal_to_cache(rm_of_the_day.recommended_load_kg),
        'percentage': _decimal_to_cache(rm_of_the_day.percentage),
        'delta_kg': _decimal_to_cache(rm_of_the_day.delta_kg),
    }


def _deserialize_rm_of_the_day(payload: dict | None) -> StudentRmOfTheDay | None:
    if not payload:
        return None
    return StudentRmOfTheDay(
        exercise_slug=payload['exercise_slug'],
        exercise_label=payload['exercise_label'],
        one_rep_max_kg=_decimal_from_cache(payload['one_rep_max_kg']),
        recommended_load_kg=_decimal_from_cache(payload['recommended_load_kg']),
        percentage=_decimal_from_cache(payload['percentage']),
        delta_kg=_decimal_from_cache(payload['delta_kg']),
    )


def _build_rm_of_the_day_payload(*, student, session_id: int | None, box_root_slug: str | None, movement_hint=None):
    if session_id is None:
        return None
    movement = movement_hint
    if movement is None:
        movement = (
            SessionWorkoutMovement.objects
            .filter(
                block__workout__session_id=session_id,
                block__workout__status=SessionWorkoutStatus.PUBLISHED,
                load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            )
            .order_by('block__sort_order', 'sort_order', 'id')
            .values('movement_slug', 'movement_label', 'load_value')
            .first()
        )
    if movement is None or movement['load_value'] is None:
        return None
    rm_record_map = build_student_rm_record_map(student=student, box_root_slug=box_root_slug)
    rm_card = rm_record_map.get(movement['movement_slug'])
    exercise_max = rm_card.record if rm_card is not None else None
    recommended_load = None
    delta_kg = None
    if exercise_max is not None:
        prescription = build_workout_prescription(
            one_rep_max_kg=exercise_max.one_rep_max_kg,
            percentage=movement['load_value'],
        )
        recommended_load = prescription.rounded_load_kg
        delta_kg = rm_card.delta_kg
    return _serialize_rm_of_the_day(
        StudentRmOfTheDay(
            exercise_slug=movement['movement_slug'],
            exercise_label=movement['movement_label'],
            one_rep_max_kg=exercise_max.one_rep_max_kg if exercise_max is not None else None,
            recommended_load_kg=recommended_load,
            percentage=movement['load_value'],
            delta_kg=delta_kg,
        )
    )


def get_student_home_snapshot(
    *,
    identity,
    start_date,
    session_ids,
    window_days: int | None,
    limit: int | None,
    now,
    progress_days_builder,
    request_perf=None,
) -> dict:
    started_at = perf_time.perf_counter()
    cache_key = build_student_home_snapshot_cache_key(
        box_root_slug=identity.box_root_slug,
        student_id=identity.student_id,
        start_date=start_date,
        window_days=window_days,
        limit=limit,
    )
    cache_lookup_started_at = perf_time.perf_counter()
    cached_snapshot = cache.get(cache_key)
    cache_lookup_ms = (perf_time.perf_counter() - cache_lookup_started_at) * 1000
    if isinstance(cached_snapshot, dict):
        snapshot = dict(cached_snapshot)
        snapshot['progress_days'] = _deserialize_progress_days(snapshot.get('progress_days', ()))
        snapshot['rm_of_the_day'] = _deserialize_rm_of_the_day(snapshot.get('rm_of_the_day'))
        record_student_app_perf(
            request_perf,
            'home-personal',
            total_ms=(perf_time.perf_counter() - started_at) * 1000,
            cache_lookup_ms=cache_lookup_ms,
            build_ms=0,
            cache_hit=True,
        )
        return snapshot

    build_started_at = perf_time.perf_counter()
    attendance_rows = tuple(
        Attendance.objects
        .filter(
            student=identity.student,
        )
        .filter(
            Q(session_id__in=session_ids) | Q(status__in=ACTIVE_ATTENDANCE_CODES)
        )
        .values('session_id', 'status', 'session__scheduled_at', 'session__duration_minutes')
    )
    attendance_by_session = {
        row['session_id']: row['status']
        for row in attendance_rows
        if row['session_id'] in session_ids
    }
    active_reserved_session_id = None
    reserved_sessions = []
    for attendance in attendance_rows:
        if attendance['status'] not in ACTIVE_ATTENDANCE_CODES:
            continue
        scheduled_at = attendance['session__scheduled_at'].astimezone(now.tzinfo)
        ends_at = scheduled_at + timedelta(minutes=attendance['session__duration_minutes'] or 60)
        if ends_at <= now:
            continue
        reserved_sessions.append((scheduled_at, attendance['session_id']))
    if reserved_sessions:
        reserved_sessions.sort(key=lambda item: item[0])
        active_reserved_session_id = reserved_sessions[0][1]

    enrollments = tuple(
        Enrollment.objects.select_related('plan')
        .filter(student=identity.student)
        .order_by('-created_at')
    )
    latest_enrollment = enrollments[0] if enrollments else None
    active_enrollment = next((item for item in enrollments if item.status == EnrollmentStatus.ACTIVE), None)
    has_active_plan = active_enrollment is not None or latest_enrollment is None
    membership_label = active_enrollment.plan.name if active_enrollment and active_enrollment.plan_id else 'Sem plano ativo'

    snapshot = {
        'attendance_by_session': attendance_by_session,
        'active_reserved_session_id': active_reserved_session_id,
        'membership_label': membership_label,
        'has_active_plan': has_active_plan,
        'progress_days': progress_days_builder(student=identity.student, now=now),
    }

    cache_payload = {
        'attendance_by_session': snapshot['attendance_by_session'],
        'active_reserved_session_id': snapshot['active_reserved_session_id'],
        'membership_label': snapshot['membership_label'],
        'has_active_plan': snapshot['has_active_plan'],
        'progress_days': _serialize_progress_days(snapshot['progress_days']),
    }
    ttl = getattr(settings, 'STUDENT_HOME_CACHE_TTL_SECONDS', 30)
    cache.set(cache_key, cache_payload, timeout=get_cache_ttl_with_jitter(ttl))
    record_student_app_perf(
        request_perf,
        'home-personal',
        total_ms=(perf_time.perf_counter() - started_at) * 1000,
        cache_lookup_ms=cache_lookup_ms,
        build_ms=(perf_time.perf_counter() - build_started_at) * 1000,
        cache_hit=False,
    )
    return snapshot


def get_student_home_rm_snapshot(*, identity, session_id: int | None, movement_hint=None, request_perf=None) -> StudentRmOfTheDay | None:
    if session_id is None:
        return None
    started_at = perf_time.perf_counter()
    cache_key = build_student_home_rm_snapshot_cache_key(
        box_root_slug=identity.box_root_slug,
        student_id=identity.student_id,
        session_id=session_id,
    )
    cache_lookup_started_at = perf_time.perf_counter()
    cached_snapshot = cache.get(cache_key)
    cache_lookup_ms = (perf_time.perf_counter() - cache_lookup_started_at) * 1000
    if isinstance(cached_snapshot, dict):
        record_student_app_perf(
            request_perf,
            'home-rm',
            total_ms=(perf_time.perf_counter() - started_at) * 1000,
            cache_lookup_ms=cache_lookup_ms,
            build_ms=0,
            cache_hit=True,
        )
        return _deserialize_rm_of_the_day(cached_snapshot)

    build_started_at = perf_time.perf_counter()
    rm_payload = _build_rm_of_the_day_payload(
        student=identity.student,
        session_id=session_id,
        box_root_slug=identity.box_root_slug,
        movement_hint=movement_hint,
    )
    ttl = getattr(settings, 'STUDENT_HOME_CACHE_TTL_SECONDS', 30)
    cache.set(cache_key, rm_payload, timeout=get_cache_ttl_with_jitter(ttl))
    record_student_app_perf(
        request_perf,
        'home-rm',
        total_ms=(perf_time.perf_counter() - started_at) * 1000,
        cache_lookup_ms=cache_lookup_ms,
        build_ms=(perf_time.perf_counter() - build_started_at) * 1000,
        cache_hit=False,
    )
    return _deserialize_rm_of_the_day(rm_payload)


__all__ = [
    'build_student_progress_days',
    'get_student_home_rm_snapshot',
    'get_student_home_snapshot',
]
