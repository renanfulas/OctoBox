"""
ARQUIVO: validacoes do corredor operacional de gap de RM.

POR QUE ELE EXISTE:
- separa da action view as regras de elegibilidade antes da mutacao do gap de RM.

O QUE ESTE ARQUIVO FAZ:
1. resolve a presenca valida do aluno na turma.
2. verifica se o movimento ainda exige %RM.
3. impede marcar RM coletado sem RM registrado.

PONTOS CRITICOS:
- preservar mensagens, criterios e guardrails do fluxo anterior.
"""

from student_app.models import StudentExerciseMax, WorkoutRmGapActionStatus


def resolve_rm_gap_attendance(*, workout, payload, reserved_statuses):
    return (
        workout.session.attendances.filter(student_id=payload['student_id'], status__in=reserved_statuses)
        .select_related('student')
        .first()
    )


def workout_requires_percentage_rm(*, workout, exercise_slug):
    return workout.blocks.filter(
        movements__movement_slug=exercise_slug,
        movements__load_type='percentage_of_rm',
    ).exists()


def can_mark_rm_gap_as_collected(*, student, exercise_slug):
    return StudentExerciseMax.objects.filter(
        student=student,
        exercise_slug=exercise_slug,
    ).exists()


def validate_rm_gap_payload(*, workout, payload, reserved_statuses):
    attendance = resolve_rm_gap_attendance(
        workout=workout,
        payload=payload,
        reserved_statuses=reserved_statuses,
    )
    if attendance is None:
        return {
            'ok': False,
            'message': 'Esse aluno nao esta mais na turma reservada para este WOD.',
            'attendance': None,
        }

    if not workout_requires_percentage_rm(workout=workout, exercise_slug=payload['exercise_slug']):
        return {
            'ok': False,
            'message': 'Esse movimento nao esta mais exigindo %RM neste WOD publicado.',
            'attendance': attendance,
        }

    if payload['status'] == WorkoutRmGapActionStatus.COLLECTED and not can_mark_rm_gap_as_collected(
        student=attendance.student,
        exercise_slug=payload['exercise_slug'],
    ):
        return {
            'ok': False,
            'message': 'Nao marque RM coletado sem registrar o RM real do aluno primeiro.',
            'attendance': attendance,
        }

    return {
        'ok': True,
        'message': '',
        'attendance': attendance,
    }


__all__ = [
    'can_mark_rm_gap_as_collected',
    'resolve_rm_gap_attendance',
    'validate_rm_gap_payload',
    'workout_requires_percentage_rm',
]
