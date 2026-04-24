"""
ARQUIVO: corredor HTTP de leitura e apoio operacional do WOD.

POR QUE ELE EXISTE:
- separa board, historico, resumo e quick edit de RM do arquivo geral de workspace.

O QUE ESTE ARQUIVO FAZ:
1. publica a fila de aprovacao do WOD.
2. publica o historico e o resumo executivo do corredor.
3. expone o quick edit de RM sem misturar com o shell principal.
"""

from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import FormView

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER
from shared_support.page_payloads import attach_page_payload

from operations.operations_executive_summary_context import build_operations_executive_summary_context
from operations.workout_approval_board_context import build_workout_approval_board_context
from operations.workout_publication_history_context import build_workout_publication_history_context
from operations.workout_rm_quick_edit_actions import save_workout_student_rm_quick_edit
from operations.workout_rm_quick_edit_context import (
    build_workout_student_rm_quick_edit_context,
    build_workout_student_rm_quick_edit_form_kwargs,
)
from operations.workout_rm_quick_edit_loader import load_workout_student_rm_quick_edit_context
from operations.forms import WorkoutStudentRmQuickForm

from .base_views import OperationBaseView


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


class WorkoutPublicationHistoryView(OperationBaseView):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_COACH)
    template_name = 'operations/workout_publication_history.html'
    page_title = 'Historico do WOD'
    page_subtitle = 'Acompanhe o que foi ao ar e as pendencias reais do corredor.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        history_context = build_workout_publication_history_context(
            request=self.request,
            today=context['today'],
            current_role=context['current_role'],
            page_title=self.page_title,
            page_subtitle=self.page_subtitle,
        )
        attach_page_payload(
            context,
            payload_key='operation_page',
            payload=history_context.pop('operation_page_payload'),
        )
        context.update(history_context)
        return context


class OperationsExecutiveSummaryView(OperationBaseView):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_COACH)
    template_name = 'operations/operations_executive_summary.html'
    page_title = 'Resumo executivo'
    page_subtitle = 'Leia o corredor de WOD sem misturar decisao, historico e acompanhamento.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        summary_context = build_operations_executive_summary_context(
            current_role=context['current_role'],
            page_title=self.page_title,
            page_subtitle=self.page_subtitle,
        )
        attach_page_payload(
            context,
            payload_key='operation_page',
            payload=summary_context.pop('operation_page_payload'),
        )
        context.update(summary_context)
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


__all__ = [
    'OperationsExecutiveSummaryView',
    'WorkoutApprovalBoardView',
    'WorkoutPublicationHistoryView',
    'WorkoutStudentRmQuickEditView',
]
