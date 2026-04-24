"""
ARQUIVO: actions seguras do planner semanal de WOD.

POR QUE ELE EXISTE:
- concentra mutacoes pequenas do planner fora da view HTTP.

O QUE ESTE ARQUIVO FAZ:
1. encontra WOD do slot anterior.
2. duplica o slot anterior para a celula atual quando seguro.

PONTOS CRITICOS:
- nao sobrescrever celula que ja tem WOD.
- coach so pode duplicar para a propria aula.
"""

from datetime import timedelta

from operations.models import ClassSession

from .workout_support import route_workout_submission
from .workout_templates import apply_persisted_workout_template
from .workout_duplication import clone_workout_to_session


def find_previous_slot_workout(*, session):
    previous_session = (
        ClassSession.objects.select_related('coach', 'workout')
        .filter(
            title=session.title,
            coach_id=session.coach_id,
            scheduled_at=session.scheduled_at - timedelta(days=7),
        )
        .first()
    )
    if previous_session is None:
        return None
    return getattr(previous_session, 'workout', None)


def duplicate_previous_slot_workout(*, actor, target_session):
    if hasattr(target_session, 'workout'):
        return {'ok': False, 'reason': 'target_has_workout'}

    source_workout = find_previous_slot_workout(session=target_session)
    if source_workout is None:
        return {'ok': False, 'reason': 'missing_previous_slot'}

    duplicated_workout = clone_workout_to_session(
        actor=actor,
        source_workout=source_workout,
        target_session=target_session,
    )
    return {
        'ok': True,
        'reason': 'duplicated',
        'source_workout': source_workout,
        'duplicated_workout': duplicated_workout,
    }


__all__ = ['apply_trusted_template_to_session', 'duplicate_previous_slot_workout', 'find_previous_slot_workout']


def apply_trusted_template_to_session(*, actor, template, target_session):
    if not getattr(template, 'is_active', False):
        return {'ok': False, 'reason': 'template_inactive'}
    if not getattr(template, 'is_trusted', False):
        return {'ok': False, 'reason': 'template_not_trusted'}

    result = apply_persisted_workout_template(
        actor=actor,
        template=template,
        target_session=target_session,
    )
    if not result.get('ok'):
        return result

    submission_result = route_workout_submission(
        actor=actor,
        workout=result['workout'],
        source='template',
        source_template=template,
    )
    return {
        'ok': True,
        'reason': 'applied',
        'workout': result['workout'],
        'submission_result': submission_result,
    }
