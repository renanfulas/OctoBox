"""
ARQUIVO: tracking de visualizacao do WOD do aluno.

POR QUE ELE EXISTE:
- separa da view a atualizacao de leitura do treino publicado.

O QUE ESTE ARQUIVO FAZ:
1. cria a primeira visualizacao do workout.
2. incrementa visualizacoes subsequentes.

PONTOS CRITICOS:
- manter a semantica atual de contagem e timestamps.
- aqui mora efeito colateral curto e isolado.
"""

from django.db.models import F
from django.utils import timezone

from student_app.models import StudentWorkoutView


def track_student_workout_view(*, student, workout):
    view, created = StudentWorkoutView.objects.get_or_create(
        student=student,
        workout=workout,
        defaults={
            'first_viewed_at': timezone.now(),
            'last_viewed_at': timezone.now(),
            'view_count': 1,
        },
    )
    if created:
        return
    StudentWorkoutView.objects.filter(pk=view.pk).update(
        last_viewed_at=timezone.now(),
        view_count=F('view_count') + 1,
        updated_at=timezone.now(),
    )


__all__ = ['track_student_workout_view']
