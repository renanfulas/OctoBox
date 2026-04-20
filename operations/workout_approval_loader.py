"""
ARQUIVO: loader do corredor de aprovacao do WOD.

POR QUE ELE EXISTE:
- separa da action view o carregamento do workout alvo da aprovacao.

O QUE ESTE ARQUIVO FAZ:
1. carrega o workout pelo id.

PONTOS CRITICOS:
- manter o carregamento simples e previsivel para o fluxo de aprovacao.
"""

from django.shortcuts import get_object_or_404

from student_app.models import SessionWorkout


def load_workout_for_approval(*, workout_id):
    return get_object_or_404(SessionWorkout, pk=workout_id)


__all__ = ['load_workout_for_approval']
