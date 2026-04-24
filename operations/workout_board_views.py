"""
ARQUIVO: corredor HTTP de leitura e apoio operacional do WOD.

POR QUE ELE EXISTE:
- separa board, historico, resumo, smart paste e quick edit de RM do arquivo geral de workspace.
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import FormView

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER
from shared_support.page_payloads import attach_page_payload

from operations.operations_executive_summary_context import build_operations_executive_summary_context
from operations.workout_approval_board_context import build_workout_approval_board_context
from operations.workout_smart_paste_context import build_weekly_wod_smart_paste_context
from operations.workout_publication_history_context import build_workout_publication_history_context
from operations.workout_rm_quick_edit_actions import save_workout_student_rm_quick_edit
from operations.workout_rm_quick_edit_context import (
    build_workout_student_rm_quick_edit_context,
    build_workout_student_rm_quick_edit_form_kwargs,
)
from operations.workout_rm_quick_edit_loader import load_workout_student_rm_quick_edit_context
from operations.forms import (
    WeeklyWodProjectionForm,
    WeeklyWodReviewMovementForm,
    WeeklyWodSmartPasteForm,
    WeeklyWodUndoReplicationForm,
    WorkoutStudentRmQuickForm,
)
from operations.services.wod_paste_parser import parse_weekly_wod_text, resolve_movement_slug
from operations.services.wod_projection import build_projection_preview, project_plan_to_sessions
from operations.services.wod_replication_batches import undo_replication_batch
from student_app.models import WeeklyWodPlan, WeeklyWodPlanStatus

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


class WorkoutSmartPasteView(OperationBaseView):
    allowed_roles = (ROLE_COACH, ROLE_OWNER)
    template_name = 'operations/workout_smart_paste.html'
    page_title = 'Smart Paste semanal'
    page_subtitle = 'Cole a semana, confira a leitura e feche um rascunho organizado.'

    def _load_plan(self, plan_id):
        if not plan_id:
            return None
        return get_object_or_404(WeeklyWodPlan, pk=plan_id)

    def _is_hx_request(self):
        return self.request.headers.get('HX-Request') == 'true'

    def _render_partial(self, template_name, context):
        return render(self.request, template_name, context)

    def _build_context(self, *, plan=None, form=None, projection_form=None, review_form=None, undo_form=None, parsed_payload=None, projection_preview=None):
        base_context = self.get_base_context()
        context = build_weekly_wod_smart_paste_context(
            request=self.request,
            today=base_context['today'],
            current_role=base_context['current_role'],
            plan=plan,
            form=form,
            projection_form=projection_form,
            review_form=review_form,
            undo_form=undo_form,
            parsed_payload=parsed_payload,
            projection_preview=projection_preview,
        )
        base_context.update(context)
        return base_context

    def _update_review_item(self, *, plan, cleaned_data):
        payload = plan.parsed_payload or {}
        days = payload.get('days') or []
        day = days[cleaned_data['day_index']]
        block = day['blocks'][cleaned_data['block_index']]
        movement = block['movements'][cleaned_data['movement_index']]
        movement['movement_label_raw'] = cleaned_data['movement_label_raw']
        chosen_slug = (cleaned_data.get('movement_slug') or '').strip()
        movement['movement_slug'] = chosen_slug or resolve_movement_slug(cleaned_data['movement_label_raw'])
        movement['reps_spec'] = (cleaned_data.get('reps_spec') or '').strip() or None
        movement['load_spec'] = (cleaned_data.get('load_spec') or '').strip() or None
        movement['notes'] = (cleaned_data.get('notes') or '').strip() or None
        plan.parsed_payload = payload
        plan.save(update_fields=['parsed_payload', 'updated_at'])
        return plan

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._build_context())
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        plan = self._load_plan(request.POST.get('plan_id'))

        if action == 'update_review_item':
            review_form = WeeklyWodReviewMovementForm(request.POST)
            if not review_form.is_valid():
                messages.error(request, 'Revise o item antes de salvar a correção.')
                context = self._build_context(plan=plan, review_form=review_form)
                if self._is_hx_request():
                    return self._render_partial('operations/includes/wod_smart_paste_preview.html', context)
                return self.render_to_response(context)
            plan = self._load_plan(review_form.cleaned_data['plan_id'])
            plan = self._update_review_item(plan=plan, cleaned_data=review_form.cleaned_data)
            messages.success(request, 'Item revisado no preview semanal.')
            context = self._build_context(plan=plan, parsed_payload=plan.parsed_payload)
            if self._is_hx_request():
                return self._render_partial('operations/includes/wod_smart_paste_preview.html', context)
            return self.render_to_response(context)

        if action == 'undo_projection':
            undo_form = WeeklyWodUndoReplicationForm(request.POST)
            if not undo_form.is_valid():
                messages.error(request, 'Nao foi possivel identificar o lote para desfazer.')
                context = self._build_context(plan=plan, undo_form=undo_form)
                if self._is_hx_request():
                    return self._render_partial('operations/includes/wod_smart_paste_projection.html', context)
                return self.render_to_response(context)
            batch = get_object_or_404(plan.replication_batches, pk=undo_form.cleaned_data['batch_id'])
            try:
                deleted_count = undo_replication_batch(batch=batch)
            except ValidationError as exc:
                messages.error(request, exc.message)
            else:
                messages.success(request, f'{deleted_count} registro(s) relacionados ao lote foram desfeitos.')
            context = self._build_context(plan=plan)
            if self._is_hx_request():
                return self._render_partial('operations/includes/wod_smart_paste_projection.html', context)
            return self.render_to_response(context)

        if action in {'preview_projection', 'create_projection'}:
            projection_form = WeeklyWodProjectionForm(request.POST)
            if not projection_form.is_valid():
                messages.error(request, 'Revise a semana alvo e os tipos de aula antes de projetar.')
                context = self._build_context(plan=plan, projection_form=projection_form)
                if self._is_hx_request():
                    return self._render_partial('operations/includes/wod_smart_paste_projection.html', context)
                return self.render_to_response(context)
            cleaned_projection = projection_form.cleaned_data
            plan = self._load_plan(cleaned_projection['plan_id'])
            preview = build_projection_preview(
                weekly_plan=plan,
                target_week_start=cleaned_projection['target_week_start'],
                class_types=cleaned_projection['class_types'],
            )
            if action == 'create_projection':
                batch, preview = project_plan_to_sessions(
                    weekly_plan=plan,
                    target_week_start=cleaned_projection['target_week_start'],
                    class_types=cleaned_projection['class_types'],
                    actor=request.user,
                )
                messages.success(
                    request,
                    f"{batch.sessions_created} WOD(s) criado(s) em DRAFT. Politica de colisao: pular aulas com WOD existente.",
                )
            else:
                messages.success(request, 'Preview de replicacao montado sem criar WODs ainda.')
            context = self._build_context(plan=plan, projection_form=projection_form, parsed_payload=plan.parsed_payload, projection_preview=preview)
            if self._is_hx_request():
                return self._render_partial('operations/includes/wod_smart_paste_projection.html', context)
            return self.render_to_response(context)

        form = WeeklyWodSmartPasteForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Revise a semana e o texto antes de continuar.')
            context = self._build_context(plan=plan, form=form)
            if self._is_hx_request():
                return self._render_partial('operations/includes/wod_smart_paste_preview.html', context)
            return self.render_to_response(context)

        cleaned = form.cleaned_data
        plan = plan or WeeklyWodPlan(created_by=request.user)
        plan.week_start = cleaned['week_start']
        plan.label = cleaned['label']
        plan.source_text = cleaned['source_text']
        if action == 'confirm_plan':
            plan.status = WeeklyWodPlanStatus.CONFIRMED
        else:
            plan.status = WeeklyWodPlanStatus.DRAFT
            plan.parsed_payload = parse_weekly_wod_text(cleaned['source_text'])
        plan.created_by = plan.created_by or request.user
        plan.save()

        if action == 'confirm_plan':
            messages.success(request, 'Plano semanal confirmado. A replicacao entra na proxima onda.')
        else:
            messages.success(request, 'Texto organizado em rascunho semanal.')

        refreshed_form = WeeklyWodSmartPasteForm(
            initial={
                'plan_id': plan.id,
                'week_start': plan.week_start,
                'label': plan.label,
                'source_text': plan.source_text,
            }
        )
        context = self._build_context(plan=plan, form=refreshed_form, parsed_payload=plan.parsed_payload)
        if self._is_hx_request():
            return self._render_partial('operations/includes/wod_smart_paste_preview.html', context)
        return self.render_to_response(context)


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
    'WorkoutSmartPasteView',
    'WorkoutStudentRmQuickEditView',
]
