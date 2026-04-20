"""
ARQUIVO: loader do atalho rapido de RM na board do WOD.

POR QUE ELE EXISTE:
- separa o carregamento e a validacao inicial da tela de RM rapido da view HTTP.

O QUE ESTE ARQUIVO FAZ:
1. carrega workout publicado.
2. carrega aluno alvo.
3. valida presenca do aluno na turma do workout.
4. resolve label e registro atual de RM.

PONTOS CRITICOS:
- manter a validacao de presenca identica ao fluxo anterior.
- qualquer regressao aqui quebra a entrada do corredor operacional de RM.
"""

from django.shortcuts import get_object_or_404

from operations.models import AttendanceStatus
from student_app.models import SessionWorkout, StudentExerciseMax
from students.models import Student


def load_workout_student_rm_quick_edit_context(*, workout_id, student_id, exercise_slug, label=''):
    workout = get_object_or_404(
        SessionWorkout.objects.select_related('session'),
        pk=workout_id,
        status='published',
    )
    student = get_object_or_404(Student, pk=student_id)
    attendance_exists = workout.session.attendances.filter(
        student=student,
        status__in=[AttendanceStatus.BOOKED, AttendanceStatus.CHECKED_IN, AttendanceStatus.CHECKED_OUT],
    ).exists()
    exercise_label = label.strip() or exercise_slug.replace('-', ' ').title()
    rm_record = StudentExerciseMax.objects.filter(
        student=student,
        exercise_slug=exercise_slug,
    ).first()
    return {
        'workout': workout,
        'student': student,
        'exercise_slug': exercise_slug,
        'exercise_label': exercise_label,
        'rm_record': rm_record,
        'attendance_exists': attendance_exists,
    }


__all__ = ['load_workout_student_rm_quick_edit_context']
