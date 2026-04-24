"""
ARQUIVO: action de aprovacao em lote do corredor WOD.

POR QUE ELE EXISTE:
- isola a mutacao de batch approve fora da view HTTP.

O QUE ESTE ARQUIVO FAZ:
1. aprova WODs pendentes nao sensiveis.
2. pula WODs sensiveis ou que ja sairam da fila.
3. devolve contadores explicitos para mensagem e telemetria.

PONTOS CRITICOS:
- item sensivel nunca pode ser aprovado por lote.
- cada aprovacao usa o mesmo caminho de side effects da aprovacao individual.
"""

from django.db import transaction

from student_app.models import SessionWorkout, SessionWorkoutStatus

from .workout_approval_actions import approve_workout
from .workout_support import build_workout_review_snapshot


def approve_non_sensitive_workouts_in_batch(*, actor, workout_ids, approval_reason):
    unique_ids = list(dict.fromkeys(int(workout_id) for workout_id in workout_ids if str(workout_id).isdigit()))
    if not unique_ids:
        return {
            'approved_count': 0,
            'skipped_sensitive_count': 0,
            'skipped_not_pending_count': 0,
        }

    workouts = (
        SessionWorkout.objects.select_related('session', 'session__coach', 'submitted_by')
        .prefetch_related('blocks__movements')
        .filter(id__in=unique_ids)
        .order_by('submitted_at', 'session__scheduled_at', 'id')
    )

    approved_count = 0
    skipped_sensitive_count = 0
    skipped_not_pending_count = 0

    with transaction.atomic():
        for workout in workouts:
            if workout.status != SessionWorkoutStatus.PENDING_APPROVAL:
                skipped_not_pending_count += 1
                continue

            review_snapshot = build_workout_review_snapshot(workout)
            if review_snapshot['diff_snapshot']['is_sensitive']:
                skipped_sensitive_count += 1
                continue

            approve_workout(
                actor=actor,
                workout=workout,
                review_snapshot=review_snapshot,
                approval_reason=approval_reason,
            )
            approved_count += 1

    return {
        'approved_count': approved_count,
        'skipped_sensitive_count': skipped_sensitive_count,
        'skipped_not_pending_count': skipped_not_pending_count,
    }


__all__ = ['approve_non_sensitive_workouts_in_batch']
