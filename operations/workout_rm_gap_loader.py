"""
ARQUIVO: loader do corredor operacional de gap de RM.

POR QUE ELE EXISTE:
- separa da action view o carregamento do workout publicado alvo do fluxo de RM.

O QUE ESTE ARQUIVO FAZ:
1. carrega o workout publicado pelo id.

PONTOS CRITICOS:
- manter o filtro de `published` identico ao fluxo anterior.
"""

from django.shortcuts import get_object_or_404

from student_app.models import SessionWorkout, SessionWorkoutStatus


def load_published_workout_for_rm_gap(*, workout_id):
    return get_object_or_404(SessionWorkout, pk=workout_id, status=SessionWorkoutStatus.PUBLISHED)


__all__ = ['load_published_workout_for_rm_gap']
