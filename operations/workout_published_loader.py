"""
ARQUIVO: loader de workouts publicados para actions pos-publicacao.

POR QUE ELE EXISTE:
- evita repetir o carregamento do workout publicado em actions views irmas.

O QUE ESTE ARQUIVO FAZ:
1. carrega workout publicado pelo id.

PONTOS CRITICOS:
- manter o filtro de `published` estavel para nao abrir mutacao fora do corredor correto.
"""

from django.shortcuts import get_object_or_404

from student_app.models import SessionWorkout, SessionWorkoutStatus


def load_published_workout(*, workout_id):
    return get_object_or_404(SessionWorkout, pk=workout_id, status=SessionWorkoutStatus.PUBLISHED)


__all__ = ['load_published_workout']
