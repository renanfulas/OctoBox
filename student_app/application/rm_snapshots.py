"""
ARQUIVO: snapshots pessoais de RM do app do aluno.

POR QUE ELE EXISTE:
- Centraliza os records maximos do aluno para reaproveitar Home, WOD, calculadora e tela de RM.

O QUE ESTE ARQUIVO FAZ:
1. Busca records e ultimo delta por exercicio.
2. Serializa o payload em formato JSON-safe.
3. Reidrata records leves para a camada de leitura.

PONTOS CRITICOS:
- O snapshot pertence ao aluno, nao ao box inteiro.
- A invalidacao precisa acontecer em create/update de RM e historico.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import time as perf_time

from django.conf import settings
from django.core.cache import cache

from shared_support.performance import get_cache_ttl_with_jitter
from student_app.application.cache_telemetry import record_student_app_perf
from student_app.application.cache_keys import build_student_rm_snapshot_cache_key
from student_app.application.results import StudentRmCard, StudentRmRecord
from student_app.models import StudentExerciseMax, StudentExerciseMaxHistory


def _decimal_to_cache(value):
    return str(value) if value is not None else None


def _decimal_from_cache(value):
    if value in (None, ''):
        return None
    return Decimal(str(value))


def _serialize_rm_card(card: StudentRmCard) -> dict:
    return {
        'record': {
            'id': card.record.id,
            'exercise_slug': card.record.exercise_slug,
            'exercise_label': card.record.exercise_label,
            'one_rep_max_kg': _decimal_to_cache(card.record.one_rep_max_kg),
            'updated_at': card.record.updated_at.isoformat(),
        },
        'delta_kg': _decimal_to_cache(card.delta_kg),
    }


def _deserialize_rm_card(payload: dict) -> StudentRmCard:
    record_payload = payload['record']
    return StudentRmCard(
        record=StudentRmRecord(
            id=record_payload['id'],
            exercise_slug=record_payload['exercise_slug'],
            exercise_label=record_payload['exercise_label'],
            one_rep_max_kg=_decimal_from_cache(record_payload['one_rep_max_kg']) or Decimal('0'),
            updated_at=datetime.fromisoformat(record_payload['updated_at']),
        ),
        delta_kg=_decimal_from_cache(payload.get('delta_kg')),
    )


def _build_student_rm_snapshot(*, student) -> dict:
    records = tuple(
        StudentExerciseMax.objects.filter(student=student).order_by('exercise_label')
    )
    latest_delta_by_slug = {}
    if records:
        for history in (
            StudentExerciseMaxHistory.objects
            .filter(student=student, exercise_slug__in=[record.exercise_slug for record in records])
            .order_by('exercise_slug', '-created_at', '-id')
        ):
            latest_delta_by_slug.setdefault(history.exercise_slug, history.delta_kg)
    cards = tuple(
        StudentRmCard(
            record=StudentRmRecord(
                id=record.id,
                exercise_slug=record.exercise_slug,
                exercise_label=record.exercise_label,
                one_rep_max_kg=record.one_rep_max_kg,
                updated_at=record.updated_at,
            ),
            delta_kg=latest_delta_by_slug.get(record.exercise_slug),
        )
        for record in records
    )
    return {
        'cards': tuple(_serialize_rm_card(card) for card in cards),
    }


def get_student_rm_snapshot(*, student, box_root_slug: str | None, request_perf=None):
    started_at = perf_time.perf_counter()
    cache_key = build_student_rm_snapshot_cache_key(
        box_root_slug=box_root_slug,
        student_id=student.id,
    )
    cache_lookup_started_at = perf_time.perf_counter()
    cached_snapshot = cache.get(cache_key)
    cache_lookup_ms = (perf_time.perf_counter() - cache_lookup_started_at) * 1000
    if isinstance(cached_snapshot, dict):
        record_student_app_perf(
            request_perf,
            'rm',
            total_ms=(perf_time.perf_counter() - started_at) * 1000,
            cache_lookup_ms=cache_lookup_ms,
            build_ms=0,
            cache_hit=True,
        )
        return {
            'cards': tuple(_deserialize_rm_card(card) for card in cached_snapshot.get('cards', ())),
        }

    build_started_at = perf_time.perf_counter()
    snapshot = _build_student_rm_snapshot(student=student)
    ttl = getattr(settings, 'STUDENT_RM_CACHE_TTL_SECONDS', 300)
    cache.set(cache_key, snapshot, timeout=get_cache_ttl_with_jitter(ttl))
    record_student_app_perf(
        request_perf,
        'rm',
        total_ms=(perf_time.perf_counter() - started_at) * 1000,
        cache_lookup_ms=cache_lookup_ms,
        build_ms=(perf_time.perf_counter() - build_started_at) * 1000,
        cache_hit=False,
    )
    return {
        'cards': tuple(_deserialize_rm_card(card) for card in snapshot.get('cards', ())),
    }


def build_student_rm_record_map(*, student, box_root_slug: str | None, request_perf=None):
    snapshot = get_student_rm_snapshot(student=student, box_root_slug=box_root_slug, request_perf=request_perf)
    return {
        card.record.exercise_slug: card
        for card in snapshot['cards']
    }


__all__ = [
    'build_student_rm_record_map',
    'get_student_rm_snapshot',
]
