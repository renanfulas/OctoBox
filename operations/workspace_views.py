"""
ARQUIVO: views de workspace operacional por papel.

POR QUE ELE EXISTE:
- publica as telas de owner, dev, manager e coach no app operations.

O QUE ESTE ARQUIVO FAZ:
1. renderiza workspaces por papel.
2. consome snapshots prontos da camada de queries.

PONTOS CRITICOS:
- qualquer regressao aqui afeta a experiencia operacional por papel.
"""

from datetime import timedelta

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import FormView

from access.navigation_contracts import get_shell_route_url
from access.roles import ROLE_COACH, ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from shared_support.page_payloads import attach_page_payload, build_page_hero
from shared_support.page_payloads import build_page_assets, build_page_payload
from shared_support.manager_event_stream import build_manager_event_stream

from operations.facade import (
    build_coach_workspace_snapshot,
    build_dev_workspace_snapshot,
    build_manager_workspace_snapshot,
    build_owner_workspace_snapshot,
    build_reception_workspace_snapshot,
)
from operations.presentation import build_operation_workspace_page
from operations.workout_approval_board_context import build_workout_approval_board_context
from operations.workout_published_history import (
    build_publication_runtime_metrics as _build_publication_runtime_metrics,
)
from operations.workout_editor_actions import CoachSessionWorkoutEditorActionsMixin
from operations.workout_editor_context import build_coach_workout_editor_context
from operations.workout_editor_dispatcher import dispatch_coach_workout_editor_intent
from operations.workout_editor_loader import load_coach_workout_editor_session
from operations.workout_rm_quick_edit_actions import save_workout_student_rm_quick_edit
from operations.workout_rm_quick_edit_context import (
    build_workout_student_rm_quick_edit_context,
    build_workout_student_rm_quick_edit_form_kwargs,
)
from operations.workout_rm_quick_edit_loader import load_workout_student_rm_quick_edit_context
from operations.forms import (
    WorkoutStudentRmQuickForm,
)
from operations.models import AttendanceStatus, ClassSession
from student_app.models import (
    SessionWorkout,
    SessionWorkoutStatus,
)

from .base_views import ManagerWorkspaceAvailabilityMixin, OperationBaseView


def _attach_operation_workspace_payload(
    context,
    *,
    page_key,
    title,
    subtitle,
    scope,
    snapshot,
    focus_key,
    capabilities=None,
):
    payload = build_operation_workspace_page(
        page_key=page_key,
        title=title,
        subtitle=subtitle,
        scope=scope,
        snapshot=snapshot,
        current_role_slug=context['current_role'].slug,
        focus_key=focus_key,
        capabilities=capabilities or {},
    )
    attach_page_payload(context, payload_key='operation_page', payload=payload)
    return payload


def _build_reception_workspace_payload(context):
    snapshot = build_reception_workspace_snapshot(today=context['today'])
    return _attach_operation_workspace_payload(
        context,
        page_key='operations-reception',
        title='Minha operacao',
        subtitle='Chegada, caixa curto e orientação do turno no balcão.',
        scope='operations-reception',
        snapshot=snapshot,
        focus_key='reception_focus',
        capabilities={'can_manage_reception_payments': context['current_role'].slug in (ROLE_OWNER, ROLE_RECEPTION)},
    )


def _build_manager_workspace_payload(context):
    request = context.get('request')
    snapshot = build_manager_workspace_snapshot(actor=getattr(request, 'user', None) or context.get('user'))
    return _attach_operation_workspace_payload(
        context,
        page_key='operations-manager',
        title='Minha operacao',
        subtitle='Triagem, vínculos e cobrança na ordem certa.',
        scope='operations-manager',
        snapshot=snapshot,
        focus_key='manager_operational_focus',
    )




class OwnerWorkspaceView(OperationBaseView):
    allowed_roles = (ROLE_OWNER,)
    template_name = 'operations/owner.html'
    page_title = 'Minha operacao'
    page_subtitle = 'Crescimento, caixa e estrutura em leitura executiva.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        snapshot = build_owner_workspace_snapshot(today=context['today'])
        _attach_operation_workspace_payload(
            context,
            page_key='operations-owner',
            title=self.page_title,
            subtitle=self.page_subtitle,
            scope='operations-owner',
            snapshot=snapshot,
            focus_key='owner_operational_focus',
        )
        return context


class OwnerWorkspacePartialView(OperationBaseView):
    allowed_roles = (ROLE_OWNER,)
    template_name = 'operations/includes/owner/owner_workspace_shell.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        snapshot = build_owner_workspace_snapshot(today=context['today'])
        _attach_operation_workspace_payload(
            context,
            page_key='operations-owner',
            title='Minha operacao',
            subtitle='Crescimento, caixa e estrutura sem leitura longa.',
            scope='operations-owner',
            snapshot=snapshot,
            focus_key='owner_operational_focus',
        )
        context['page'] = context['operation_page']
        return context


class DevWorkspaceView(OperationBaseView):
    allowed_roles = (ROLE_DEV,)
    template_name = 'operations/dev.html'
    page_title = 'Minha operacao'
    page_subtitle = 'Rastros, fronteiras e manutenção sem invadir a operação.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        snapshot = build_dev_workspace_snapshot()
        _attach_operation_workspace_payload(
            context,
            page_key='operations-dev',
            title=self.page_title,
            subtitle=self.page_subtitle,
            scope='operations-dev',
            snapshot=snapshot,
            focus_key='dev_operational_focus',
        )
        return context


class ManagerWorkspaceView(ManagerWorkspaceAvailabilityMixin, OperationBaseView):
    allowed_roles = (ROLE_MANAGER,)
    template_name = 'operations/manager.html'
    page_title = 'Minha operacao'
    page_subtitle = 'Triagem, vínculos e cobrança na ordem certa.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        _build_manager_workspace_payload(context)
        return context


class ManagerBoardsPartialView(ManagerWorkspaceAvailabilityMixin, OperationBaseView):
    allowed_roles = (ROLE_MANAGER,)
    template_name = 'operations/includes/manager/manager_boards_section.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        _build_manager_workspace_payload(context)
        context['page'] = context['operation_page']
        return context


class ManagerEventStreamView(ManagerWorkspaceAvailabilityMixin, OperationBaseView, View):
    allowed_roles = (ROLE_MANAGER,)

    def get(self, request, *args, **kwargs):
        return build_manager_event_stream()


class OperationEventStreamView(OperationBaseView, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)

    def get(self, request, *args, **kwargs):
        return build_manager_event_stream()


class CoachWorkspaceView(OperationBaseView):
    allowed_roles = (ROLE_COACH,)
    template_name = 'operations/coach.html'
    page_title = 'Minha operacao'
    page_subtitle = 'Aula, presença e ocorrência com leitura curta.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        snapshot = build_coach_workspace_snapshot(today=context['today'])
        _attach_operation_workspace_payload(
            context,
            page_key='operations-coach',
            title=self.page_title,
            subtitle=self.page_subtitle,
            scope='operations-coach',
            snapshot=snapshot,
            focus_key='coach_operational_focus',
        )
        return context


class CoachSessionWorkoutEditorView(CoachSessionWorkoutEditorActionsMixin, OperationBaseView):
    allowed_roles = (ROLE_COACH,)
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


class WorkoutApprovalBoardView(OperationBaseView):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)
    template_name = 'operations/workout_approval_board.html'
    page_title = 'Aprovacao de WOD'
    page_subtitle = 'Revise os treinos pendentes antes de liberar para os alunos.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        board_context = build_workout_approval_board_context(
            request=self.request,
            today=context['today'],
            current_role=context['current_role'],
            page_title=self.page_title,
            page_subtitle=self.page_subtitle,
        )
        attach_page_payload(
            context,
            payload_key='operation_page',
            payload=board_context.pop('operation_page_payload'),
        )
        context.update(board_context)
        return context


class ReceptionWorkspaceView(OperationBaseView):
    allowed_roles = (ROLE_OWNER, ROLE_RECEPTION)
    template_name = 'operations/reception.html'
    page_title = 'Minha operacao'
    page_subtitle = 'Chegada, agenda e cobrança curta no balcão.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        _build_reception_workspace_payload(context)
        return context


class ReceptionPaymentBoardPartialView(OperationBaseView):
    allowed_roles = (ROLE_OWNER, ROLE_RECEPTION)
    template_name = 'operations/includes/reception/reception_payment_board.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        _build_reception_workspace_payload(context)
        context['page'] = context['operation_page']
        return context


class WhatsAppWorkspaceView(OperationBaseView):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_DEV, ROLE_COACH, ROLE_RECEPTION)
    template_name = 'operations/whatsapp_placeholder.html'
    page_title = 'Mensagens'
    page_subtitle = 'Central de comunicação e relacionamento com seus alunos.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        context['whatsapp_placeholder_hero'] = build_page_hero(
            eyebrow='Mensagens',
            title='Central em preparo.',
            copy='Veja o que já está definido, o que ainda chega e para onde seguir sem ruído.',
            actions=[
                {
                    'label': 'Abrir dashboard',
                    'href': get_shell_route_url('dashboard'),
                    'kind': 'secondary',
                },
            ],
            aria_label='Panorama da central de mensagens',
            classes=['whatsapp-placeholder-hero'],
            heading_level='h1',
            data_panel='whatsapp-placeholder-hero',
            actions_slot='whatsapp-placeholder-hero-actions',
        )
        return context


class WorkoutStudentRmQuickEditView(OperationBaseView, FormView):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)
    template_name = 'operations/workout_student_rm_quick_edit.html'
    form_class = WorkoutStudentRmQuickForm
    page_title = 'Cadastro rapido de RM'
    page_subtitle = 'Registre o RM do aluno sem sair do corredor operacional do WOD.'

    def dispatch(self, request, *args, **kwargs):
        payload = load_workout_student_rm_quick_edit_context(
            workout_id=kwargs['workout_id'],
            student_id=kwargs['student_id'],
            exercise_slug=kwargs['exercise_slug'],
            label=request.GET.get('label', ''),
        )
        self.workout = payload['workout']
        self.student = payload['student']
        self.exercise_slug = payload['exercise_slug']
        self.exercise_label = payload['exercise_label']
        self.rm_record = payload['rm_record']
        if not payload['attendance_exists']:
            messages.error(request, 'Esse aluno nao esta mais na turma reservada deste WOD.')
            return redirect('workout-approval-board')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return build_workout_student_rm_quick_edit_form_kwargs(self)

    def get_context_data(self, **kwargs):
        return build_workout_student_rm_quick_edit_context(self, **kwargs)

    def form_valid(self, form):
        return save_workout_student_rm_quick_edit(self, form)
