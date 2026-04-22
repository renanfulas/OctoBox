"""
ARQUIVO: contexto e form factory do editor de WOD do coach.

POR QUE ELE EXISTE:
- remove da view a montagem detalhada de contexto e formularios sem criar uma camada teatral.

O QUE ESTE ARQUIVO FAZ:
1. monta o page payload do editor.
2. calcula o preview de RM da turma.
3. monta o contexto final com formularios e sessoes de duplicacao.

PONTOS CRITICOS:
- manter o contrato de contexto estavel para nao quebrar o template do editor.
- aqui mora montagem de tela, nao mutacao de estado.
"""

from django.urls import reverse

from shared_support.page_payloads import attach_page_payload, build_page_hero
from shared_support.page_payloads import build_page_assets, build_page_payload
from student_app.application.use_cases import build_student_prescription_label, build_student_recommendation_preview

from operations.forms import (
    CoachSessionWorkoutForm,
    CoachWorkoutBlockForm,
    CoachWorkoutMovementForm,
    WorkoutDuplicateForm,
)
from operations.models import ClassSession
from student_app.models import StudentExerciseMax, WorkoutLoadType

from .workout_corridor_navigation import build_workout_corridor_tabs


def build_coach_workout_editor_page_payload(view, context):
    payload = build_page_payload(
        context={
            'page_key': 'operations-coach-wod-editor',
            'title': view.page_title,
            'subtitle': view.page_subtitle,
            'mode': 'workspace',
            'role_slug': context['current_role'].slug,
        },
        data={
            'hero': build_page_hero(
                eyebrow='Coach',
                title=f'WOD da aula: {view.session.title}',
                copy='Aqui o coach monta o treino em blocos curtos. Pense como montar uma playlist: primeiro o tema, depois as faixas.',
                actions=[
                    {
                        'label': 'Voltar ao turno',
                        'href': reverse('coach-workspace'),
                        'kind': 'secondary',
                    },
                ],
                aria_label='Editor de WOD do coach',
                classes=['coach-hero'],
                data_panel='coach-hero',
                actions_slot='coach-hero-actions',
            ),
        },
        behavior={
            'surface_key': 'operations-coach-wod-editor',
            'scope': 'operations-coach',
        },
        assets=build_page_assets(css=['css/design-system/operations.css']),
    )
    attach_page_payload(context, payload_key='operation_page', payload=payload)
    return payload


def build_coach_workout_editor_rm_preview(view, *, workout):
    attendances = [
        attendance
        for attendance in view.session.attendances.all()
        if attendance.status in view.rm_preview_attendance_statuses and attendance.student_id
    ]
    students = [attendance.student for attendance in attendances]
    percentage_movements = []
    if workout is not None:
        for block in workout.blocks.all():
            for movement in block.movements.all():
                if movement.load_type == WorkoutLoadType.PERCENTAGE_OF_RM and movement.load_value is not None:
                    percentage_movements.append((block, movement))

    if not students:
        return {
            'reserved_students_count': 0,
            'cards': (),
            'empty_copy': 'Nenhum aluno reservado ou em check-in nesta aula ainda. Quando a turma aparecer, o radar de RM entra aqui.',
        }

    if not percentage_movements:
        return {
            'reserved_students_count': len(students),
            'cards': (),
            'empty_copy': 'Ainda nao existe movimento com % do RM neste WOD. Quando voce usar esse tipo de carga, mostramos aqui o impacto na turma.',
        }

    student_maxes = {
        (exercise_max.student_id, exercise_max.exercise_slug): exercise_max
        for exercise_max in StudentExerciseMax.objects.filter(
            student__in=students,
            exercise_slug__in=[movement.movement_slug for _, movement in percentage_movements],
        )
    }

    cards = []
    for block, movement in percentage_movements:
        tracked_students = []
        missing_students = []
        load_context_label = ''
        for student in students:
            exercise_max = student_maxes.get((student.id, movement.movement_slug))
            load_context_label, recommended_load, recommendation_copy = build_student_recommendation_preview(
                student=student,
                movement=movement,
            )
            if exercise_max is None or recommended_load is None:
                missing_students.append(student.full_name)
                continue
            tracked_students.append(
                {
                    'student_name': student.full_name,
                    'one_rep_max_label': f'{exercise_max.one_rep_max_kg} kg',
                    'recommended_load_label': f'{recommended_load} kg',
                    'recommendation_copy': recommendation_copy,
                    'recommended_load': recommended_load,
                }
            )
        tracked_students.sort(key=lambda item: item['student_name'])
        missing_students.sort()
        range_label = ''
        if tracked_students:
            recommended_loads = [item['recommended_load'] for item in tracked_students]
            range_label = f'{min(recommended_loads)} kg ate {max(recommended_loads)} kg'
        cards.append(
            {
                'block_title': block.title,
                'movement_label': movement.movement_label,
                'prescription_label': build_student_prescription_label(movement=movement),
                'load_context_label': load_context_label,
                'coverage_label': f'{len(tracked_students)}/{len(students)} alunos com RM registrado',
                'range_label': range_label,
                'tracked_students': tuple(tracked_students),
                'missing_students': tuple(missing_students),
                'missing_students_label': ', '.join(missing_students[:4]),
                'missing_students_remaining': max(len(missing_students) - 4, 0),
            }
        )

    return {
        'reserved_students_count': len(students),
        'cards': tuple(cards),
        'empty_copy': '',
    }


def build_coach_workout_editor_context(view, *, workout_form=None, block_form=None, movement_form=None):
    context = view.get_context_data()
    context.update(view.get_base_context())
    workout = view._get_workout()
    duplicate_sessions = (
        ClassSession.objects.filter(scheduled_at__gte=view.session.scheduled_at)
        .exclude(pk=view.session.id)
        .order_by('scheduled_at')[:12]
    )
    build_coach_workout_editor_page_payload(view, context)
    context.update(
        {
            'workout_corridor_tabs': build_workout_corridor_tabs(
                current_key='editor',
                current_role_slug=context['current_role'].slug,
                editor_href=reverse('coach-session-workout-editor', args=[view.session.id]),
            ),
            'session': view.session,
            'workout': workout,
            'workout_form': workout_form
            or CoachSessionWorkoutForm(
                initial={
                    'title': getattr(workout, 'title', view.session.title),
                    'coach_notes': getattr(workout, 'coach_notes', ''),
                }
            ),
            'block_form': block_form
            or CoachWorkoutBlockForm(
                initial={
                    'sort_order': (workout.blocks.count() + 1) if workout is not None else 1,
                }
            ),
            'movement_form': movement_form
            or CoachWorkoutMovementForm(
                initial={
                    'sort_order': 1,
                }
            ),
            'session_rm_preview': build_coach_workout_editor_rm_preview(view, workout=workout),
            'duplicate_sessions': duplicate_sessions,
            'duplicate_form': WorkoutDuplicateForm(),
        }
    )
    return context


__all__ = [
    'build_coach_workout_editor_context',
    'build_coach_workout_editor_page_payload',
    'build_coach_workout_editor_rm_preview',
]
