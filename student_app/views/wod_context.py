"""
ARQUIVO: contexto do corredor autenticado de WOD do aluno.

POR QUE ELE EXISTE:
- remove da view a montagem detalhada do contexto do WOD sem criar uma camada teatral.

O QUE ESTE ARQUIVO FAZ:
1. resolve dashboard e sessao alvo do WOD.
2. monta o contexto do treino do dia.
3. devolve o workout publicado associado quando existir.

PONTOS CRITICOS:
- manter o contrato de contexto da tela do WOD estavel.
- aqui mora leitura e montagem, nao mutacao.
"""

from django.shortcuts import get_object_or_404

from operations.models import ClassSession
from student_app.application.use_cases import GetStudentDashboard, GetStudentWorkoutDay
from student_app.models import SessionWorkout, SessionWorkoutStatus, StudentExerciseMax


def build_student_wod_context(view, **kwargs):
    context = super(type(view), view).get_context_data(**kwargs)
    dashboard = GetStudentDashboard().execute(identity=view.request.student_identity)
    student = view.request.student_identity.student
    context['dashboard'] = dashboard
    context['student_shell_nav'] = 'wod'
    context['student_shell_title'] = 'WOD'
    context['student_next_session'] = dashboard.next_sessions[0] if dashboard.next_sessions else None
    session_id = (view.request.GET.get('session_id') or '').strip()
    target_session = dashboard.active_wod_session or dashboard.focal_session
    if session_id:
        session = get_object_or_404(ClassSession, pk=session_id)
        target_session = type('StudentTargetSession', (), {'session_id': session.id})()
    workout_day = (
        GetStudentWorkoutDay().execute(
            student=student,
            session_id=target_session.session_id,
        )
        if target_session is not None
        else None
    )
    workout = None
    if target_session is not None and workout_day is not None:
        workout = (
            SessionWorkout.objects.filter(session_id=target_session.session_id, status=SessionWorkoutStatus.PUBLISHED)
            .only('id')
            .first()
        )
    context['student_workout_day'] = workout_day
    context['student_rm_preview'] = StudentExerciseMax.objects.filter(student=student).order_by('exercise_label').first()
    return {
        'context': context,
        'dashboard': dashboard,
        'target_session': target_session,
        'workout_day': workout_day,
        'workout': workout,
    }


__all__ = ['build_student_wod_context']
