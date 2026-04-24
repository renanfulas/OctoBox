"""
ARQUIVO: preview backend de prescricao para o editor WOD.

POR QUE ELE EXISTE:
- centraliza a leitura rica por aluno para o editor sem depender do browser como unica fonte.

O QUE ESTE ARQUIVO FAZ:
1. calcula recomendacao por aluno para um movimento.
2. reaproveita a regra oficial de prescricao do backend.
3. devolve payload pequeno para o editor.

PONTOS CRITICOS:
- leitura apenas; nao muta estado.
- sempre filtrar alunos da aula atual.
"""

from decimal import Decimal, InvalidOperation

from operations.models import AttendanceStatus
from student_app.domain.workout_prescription import build_workout_prescription
from student_app.models import StudentExerciseMax, WorkoutLoadType


def build_session_movement_prescription_preview(*, session, movement_slug, load_type, load_value):
    attendance_student_ids = [
        attendance.student_id
        for attendance in session.attendances.all()
        if attendance.student_id
        and attendance.status in {
            AttendanceStatus.BOOKED,
            AttendanceStatus.CHECKED_IN,
            AttendanceStatus.CHECKED_OUT,
        }
    ]

    if not movement_slug:
        return {
            'students': [],
            'missing_students': [],
            'summary': 'Escolha um movimento para ver o impacto por aluno.',
        }

    if load_type != WorkoutLoadType.PERCENTAGE_OF_RM:
        return {
            'students': [],
            'missing_students': [],
            'summary': 'Preview detalhado por aluno fica ativo quando a carga usa percentual do RM.',
        }

    try:
        percentage = Decimal(str(load_value))
    except (InvalidOperation, TypeError):
        return {
            'students': [],
            'missing_students': [],
            'summary': 'Defina um percentual valido para calcular a prescricao por aluno.',
        }

    exercise_maxes = (
        StudentExerciseMax.objects.filter(student_id__in=attendance_student_ids, exercise_slug=movement_slug)
        .select_related('student')
        .order_by('student__full_name')
    )
    max_by_student_id = {exercise_max.student_id: exercise_max for exercise_max in exercise_maxes}

    students = []
    missing_students = []
    for attendance in session.attendances.all():
        if attendance.student_id not in attendance_student_ids:
            continue
        exercise_max = max_by_student_id.get(attendance.student_id)
        if exercise_max is None:
            missing_students.append(attendance.student.full_name)
            continue
        prescription = build_workout_prescription(
            one_rep_max_kg=exercise_max.one_rep_max_kg,
            percentage=percentage,
        )
        students.append(
            {
                'name': attendance.student.full_name,
                'one_rep_max_label': f'{exercise_max.one_rep_max_kg} kg',
                'raw_load_label': f'{prescription.raw_load_kg} kg',
                'rounded_load_label': f'{prescription.rounded_load_kg} kg',
                'observation': prescription.observation,
            }
        )

    summary = f'{len(students)}/{len(attendance_student_ids)} alunos com RM pronto para este movimento.'
    return {
        'students': students[:6],
        'missing_students': missing_students[:6],
        'missing_students_remaining': max(len(missing_students) - 6, 0),
        'summary': summary,
    }


__all__ = ['build_session_movement_prescription_preview']
