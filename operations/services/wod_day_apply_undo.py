"""
ARQUIVO: desfaz aplicação em lote de template por dia (janela de 60s).

POR QUE ELE EXISTE:
- o undo precisa ser atômico e dentro da janela de cache antes que o coach
  aja sobre os rascunhos gerados.

O QUE ESTE ARQUIVO FAZ:
1. lê o undo_token do cache (TTL 60s).
2. remove os SessionWorkoutBlock criados pelo apply, voltando o workout ao
   estado anterior (vazio se era novo, ou preserva o estado original se mode
   era overwrite — limitação conhecida: overwrite não restaura conteúdo anterior).
3. deleta SessionWorkout criados do zero (que não existiam antes do apply).
4. invalida o token após uso.
"""

from __future__ import annotations

from django.core.cache import cache
from django.db import transaction

from student_app.models import SessionWorkout, SessionWorkoutStatus


def execute_undo(*, undo_token: str) -> dict:
    key = f'wod_day_apply_undo:{undo_token}'
    payload = cache.get(key)
    if payload is None:
        return {'ok': False, 'reason': 'Token expirado ou já utilizado.'}

    session_ids = payload.get('session_ids', [])
    if not session_ids:
        cache.delete(key)
        return {'ok': True, 'undone_count': 0}

    undone = 0
    with transaction.atomic():
        workouts = SessionWorkout.objects.filter(
            session_id__in=session_ids,
            status=SessionWorkoutStatus.DRAFT,
        ).select_related('session')

        for workout in workouts:
            workout.blocks.all().delete()
            if workout.version == 1:
                workout.delete()
            else:
                workout.version -= 1
                workout.save(update_fields=['version', 'updated_at'])
            undone += 1

    cache.delete(key)
    return {'ok': True, 'undone_count': undone}


__all__ = ['execute_undo']
