"""Restaura a aplicação diária sem apagar edições posteriores de um WOD."""

from django.core.cache import cache
from django.db import transaction

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, get_user_role
from operations.models import ClassSession
from operations.workout_support import record_workout_audit
from student_app.models import SessionWorkout, SessionWorkoutStatus

from .wod_day_apply_state import restore_workout, undo_cache_key, workout_state


@transaction.atomic
def execute_undo(*, actor, undo_token: str) -> dict:
    role = get_user_role(actor)
    key = undo_cache_key(actor, undo_token)
    payload = cache.get(key)
    if payload is None or role is None or role.slug not in {ROLE_COACH, ROLE_MANAGER, ROLE_OWNER}:
        return {'ok': False, 'reason': 'Token expirado, já utilizado ou indisponível para este usuário.'}
    changes = payload['changes']
    sessions = list(ClassSession.objects.select_for_update().filter(
        id__in=[change['session_id'] for change in changes],
    ).order_by('id'))
    if role.slug == ROLE_COACH and any(session.coach_id != actor.pk for session in sessions):
        return {'ok': False, 'reason': 'Uma aula mudou de responsável. Nenhum WOD foi desfeito.'}
    workouts = {
        workout.session_id: workout for workout in SessionWorkout.objects.select_for_update().filter(
            session_id__in=[change['session_id'] for change in changes],
        )
    }
    # Validar o lote inteiro antes de alterar qualquer aula.
    for change in changes:
        workout = workouts.get(change['session_id'])
        if workout is None or workout.status != SessionWorkoutStatus.DRAFT or workout_state(workout) != change['after']:
            return {'ok': False, 'reason': 'Um WOD foi editado ou enviado para aprovação depois da aplicação. Nenhuma alteração foi desfeita.'}
    for change in changes:
        workout = workouts[change['session_id']]
        if change['before'] is None:
            record_workout_audit(actor=actor, workout=workout, action='session_workout_day_apply_undone', description='Aplicação diária desfeita; rascunho novo removido.')
            workout.delete()
        else:
            restore_workout(workout, change['before'])
            record_workout_audit(actor=actor, workout=workout, action='session_workout_day_apply_undone', description='Conteúdo anterior do rascunho restaurado.')
    cache.delete(key)
    return {'ok': True, 'undone_count': len(changes)}


__all__ = ['execute_undo']
