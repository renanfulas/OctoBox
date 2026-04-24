"""
ARQUIVO: corredor HTTP do editor operacional de WOD.

POR QUE ELE EXISTE:
- separa o editor e o preview de prescricao do arquivo geral de workspace.

O QUE ESTE ARQUIVO FAZ:
1. publica o redirect do editor-home para o planner.
2. publica o editor da aula do coach/owner.
3. expone o preview backend de prescricao.
"""

from django.http import JsonResponse
from django.shortcuts import redirect
from django.views import View

from access.roles import ROLE_COACH, ROLE_OWNER
from shared_support.page_payloads import attach_page_payload

from operations.models import AttendanceStatus
from operations.workout_editor_actions import CoachSessionWorkoutEditorActionsMixin
from operations.workout_editor_context import build_coach_workout_editor_context
from operations.workout_editor_dispatcher import dispatch_coach_workout_editor_intent
from operations.workout_editor_loader import load_coach_workout_editor_session
from operations.workout_editor_overview_context import build_workout_editor_overview_context
from operations.workout_prescription_preview import build_session_movement_prescription_preview
from student_app.models import SessionWorkout, SessionWorkoutStatus

from .base_views import OperationBaseView


class WorkoutEditorHomeView(OperationBaseView):
    allowed_roles = (ROLE_COACH, ROLE_OWNER)
    template_name = 'operations/workout_editor_home.html'
    page_title = 'Editor de WOD'
    page_subtitle = 'Escolha a aula e abra o editor sem labirinto.'

    def get(self, request, *args, **kwargs):
        return redirect('workout-planner')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        editor_context = build_workout_editor_overview_context(
            request=self.request,
            today=context['today'],
            current_role=context['current_role'],
            page_title=self.page_title,
            page_subtitle=self.page_subtitle,
        )
        attach_page_payload(
            context,
            payload_key='operation_page',
            payload=editor_context.pop('operation_page_payload'),
        )
        context.update(editor_context)
        return context


class CoachSessionWorkoutEditorView(CoachSessionWorkoutEditorActionsMixin, OperationBaseView):
    allowed_roles = (ROLE_COACH, ROLE_OWNER)
    template_name = 'operations/coach_session_workout_editor.html'
    page_title = 'Publicar WOD'
    page_subtitle = 'Monte o treino da aula com blocos e movimentos sem sair do fluxo do coach.'
    rm_preview_attendance_statuses = {
        AttendanceStatus.BOOKED,
        AttendanceStatus.CHECKED_IN,
        AttendanceStatus.CHECKED_OUT,
    }

    def dispatch(self, request, *args, **kwargs):
        self.session = load_coach_workout_editor_session(session_id=kwargs['session_id'])
        return super().dispatch(request, *args, **kwargs)

    def _get_workout(self):
        return getattr(self.session, 'workout', None)

    def _get_or_create_workout(self):
        workout = self._get_workout()
        if workout is not None:
            return workout
        workout, _ = SessionWorkout.objects.get_or_create(
            session=self.session,
            defaults={
                'title': self.session.title,
                'status': SessionWorkoutStatus.DRAFT,
                'created_by': self.request.user,
            },
        )
        self.session.workout = workout
        return workout

    def _build_context(self, *, workout_form=None, block_form=None, movement_form=None):
        return build_coach_workout_editor_context(
            self,
            workout_form=workout_form,
            block_form=block_form,
            movement_form=movement_form,
        )

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self._build_context())

    def post(self, request, *args, **kwargs):
        return dispatch_coach_workout_editor_intent(self, request)


class WorkoutPrescriptionPreviewView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_OWNER)

    def get(self, request, session_id, *args, **kwargs):
        session = load_coach_workout_editor_session(session_id=session_id)
        payload = build_session_movement_prescription_preview(
            session=session,
            movement_slug=(request.GET.get('movement_slug') or '').strip(),
            load_type=(request.GET.get('load_type') or '').strip(),
            load_value=(request.GET.get('load_value') or '').strip(),
        )
        return JsonResponse(payload)


__all__ = [
    'CoachSessionWorkoutEditorView',
    'WorkoutEditorHomeView',
    'WorkoutPrescriptionPreviewView',
]
