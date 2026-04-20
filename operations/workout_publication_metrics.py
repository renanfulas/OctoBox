"""
ARQUIVO: metricas e prontidao de RM da leitura pos-publicacao do WOD.

POR QUE ELE EXISTE:
- tira de `workout_published_history.py` a bancada de metricas e readiness.

O QUE ESTE ARQUIVO FAZ:
1. calcula consumo basico do WOD publicado.
2. calcula cobertura de RM para treinos com %RM.

PONTOS CRITICOS:
- preservar o mesmo shape de retorno usado pelo historico publicado.
- manter a leitura enxuta sem criar N+1 acidental.
"""

from operations.models import AttendanceStatus
from student_app.models import StudentExerciseMax, WorkoutLoadType

from .workout_board_builders import build_snapshot_blocks


def build_publication_runtime_metrics(*, session, workout):
    attendances = list(session.attendances.all())
    reserved_statuses = {
        AttendanceStatus.BOOKED,
        AttendanceStatus.CHECKED_IN,
        AttendanceStatus.CHECKED_OUT,
    }
    reserved_count = sum(1 for attendance in attendances if attendance.status in reserved_statuses)
    checked_in_count = sum(
        1 for attendance in attendances if attendance.status in {AttendanceStatus.CHECKED_IN, AttendanceStatus.CHECKED_OUT}
    )
    viewer_count = len(list(workout.student_views.all()))
    viewer_rate = round((viewer_count / reserved_count) * 100) if reserved_count else 0
    return {
        'reserved_count': reserved_count,
        'checked_in_count': checked_in_count,
        'viewer_count': viewer_count,
        'viewer_rate': viewer_rate,
    }


def build_publication_rm_readiness(*, snapshot, session, workout):
    reserved_statuses = {
        AttendanceStatus.BOOKED,
        AttendanceStatus.CHECKED_IN,
        AttendanceStatus.CHECKED_OUT,
    }
    reserved_students = [
        attendance.student
        for attendance in session.attendances.all()
        if attendance.status in reserved_statuses and attendance.student_id
    ]
    percentage_movements = []
    for block in build_snapshot_blocks(snapshot):
        for movement in block.get('movements', []):
            if movement.get('load_type') == WorkoutLoadType.PERCENTAGE_OF_RM and movement.get('load_value') not in {'', None}:
                movement_slug = (movement.get('movement_slug') or '').strip()
                if not movement_slug:
                    continue
                percentage_movements.append(
                    {
                        'movement_slug': movement_slug,
                        'movement_label': movement.get('movement_label') or movement_slug,
                    }
                )
    if not percentage_movements:
        return {
            'has_percentage_rm': False,
            'required_movements_label': '',
            'coverage_label': 'Sem %RM',
            'viewer_ready_label': 'Sem %RM',
            'readiness_summary': 'O treino publicado nao exigia base de RM para consumir a prescricao.',
            'alert_level': '',
            'fully_ready_count': 0,
            'viewer_ready_count': 0,
            'viewer_without_full_rm_count': 0,
            'missing_students_label': '',
            'missing_students_remaining': 0,
            'required_movements': (),
            'missing_students': (),
            'missing_student_entries': (),
        }

    unique_requirements = []
    seen_slugs = set()
    for movement in percentage_movements:
        if movement['movement_slug'] in seen_slugs:
            continue
        seen_slugs.add(movement['movement_slug'])
        unique_requirements.append(movement)

    student_maxes = {
        (exercise_max.student_id, exercise_max.exercise_slug)
        for exercise_max in StudentExerciseMax.objects.filter(
            student__in=reserved_students,
            exercise_slug__in=[movement['movement_slug'] for movement in unique_requirements],
        )
    }
    viewer_student_ids = {view.student_id for view in workout.student_views.all() if view.student_id}
    fully_ready_students = []
    missing_students = []
    missing_student_entries = []
    viewer_ready_count = 0
    viewer_without_full_rm_count = 0

    for student in reserved_students:
        student_slugs = {slug for student_id, slug in student_maxes if student_id == student.id}
        missing_requirements = [movement for movement in unique_requirements if movement['movement_slug'] not in student_slugs]
        is_fully_ready = not missing_requirements
        if is_fully_ready:
            fully_ready_students.append(student)
            if student.id in viewer_student_ids:
                viewer_ready_count += 1
        else:
            missing_students.append(student.full_name)
            missing_student_entries.append(
                {
                    'student_id': student.id,
                    'student_name': student.full_name,
                    'missing_exercises': tuple(
                        {'slug': movement['movement_slug'], 'label': movement['movement_label']}
                        for movement in missing_requirements
                    ),
                }
            )
            if student.id in viewer_student_ids:
                viewer_without_full_rm_count += 1

    reserved_count = len(reserved_students)
    fully_ready_count = len(fully_ready_students)
    coverage_rate = round((fully_ready_count / reserved_count) * 100) if reserved_count else 0
    viewer_rate = round((viewer_ready_count / len(viewer_student_ids)) * 100) if viewer_student_ids else 0
    missing_students.sort()

    if reserved_count and fully_ready_count == 0:
        alert_level = 'danger'
    elif reserved_count and coverage_rate < 50:
        alert_level = 'warning'
    elif viewer_without_full_rm_count:
        alert_level = 'warning'
    else:
        alert_level = 'success'

    required_movements_label = ', '.join(movement['movement_label'] for movement in unique_requirements[:3])
    if len(unique_requirements) > 3:
        required_movements_label = f'{required_movements_label} e mais {len(unique_requirements) - 3}'

    if reserved_count == 0:
        readiness_summary = 'O treino pede %RM, mas ainda nao existe turma reservada para comparar prontidao real.'
    else:
        readiness_summary = (
            f'{fully_ready_count}/{reserved_count} aluno(s) estavam prontos com RM completo para {len(unique_requirements)} movimento(s) dependente(s) de RM.'
        )

    return {
        'has_percentage_rm': True,
        'required_movements_label': required_movements_label,
        'coverage_label': f'RM pronto {fully_ready_count}/{reserved_count} ({coverage_rate}%)' if reserved_count else 'Sem turma reservada',
        'viewer_ready_label': (
            f'Aberturas prontas {viewer_ready_count}/{len(viewer_student_ids)} ({viewer_rate}%)'
            if viewer_student_ids
            else 'Sem abertura no app'
        ),
        'readiness_summary': readiness_summary,
        'alert_level': alert_level,
        'fully_ready_count': fully_ready_count,
        'viewer_ready_count': viewer_ready_count,
        'viewer_without_full_rm_count': viewer_without_full_rm_count,
        'missing_students_label': ', '.join(missing_students[:4]),
        'missing_students_remaining': max(len(missing_students) - 4, 0),
        'required_movements': tuple(movement['movement_label'] for movement in unique_requirements),
        'missing_students': tuple(missing_students),
        'missing_student_entries': tuple(missing_student_entries),
    }
