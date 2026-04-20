"""
ARQUIVO: action views do corredor de aprovacao e follow-up do WOD.

POR QUE ELE EXISTE:
- separa as mutacoes reais do WOD da leitura monolitica de `workspace_views.py`.

O QUE ESTE ARQUIVO FAZ:
1. aprova ou rejeita WOD pendente.
2. registra follow-up pos-publicacao.
3. registra memoria operacional curta.
4. atualiza checkpoint semanal de gestao.

PONTOS CRITICOS:
- qualquer mudanca aqui altera estado real, auditoria e retorno visual da board.
- manter side effects, mensagens e permissoes identicos ao fluxo anterior.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from access.roles import ROLE_MANAGER, ROLE_OWNER
from auditing import log_audit_event
from operations.models import AttendanceStatus
from student_app.models import (
    SessionWorkout,
    SessionWorkoutFollowUpAction,
    SessionWorkoutOperationalMemory,
    SessionWorkoutStatus,
    WorkoutWeeklyManagementCheckpoint,
)

from .base_views import OperationBaseView
from .forms import (
    WorkoutApprovalDecisionForm,
    WorkoutFollowUpResolutionForm,
    WorkoutRmGapActionForm,
    WorkoutOperationalMemoryForm,
    WorkoutRejectionForm,
    WorkoutWeeklyCheckpointForm,
)
from .workout_approval_actions import approve_workout, reject_workout
from .workout_approval_loader import load_workout_for_approval
from .workout_approval_validation import (
    is_workout_pending_approval,
    requires_sensitive_confirmation,
    validate_rejection_form,
)
from .workout_follow_up_actions import save_workout_follow_up_action
from .workout_operational_memory_actions import create_workout_operational_memory
from .workout_published_loader import load_published_workout
from .workout_rm_gap_actions import save_workout_rm_gap_action
from .workout_rm_gap_loader import load_published_workout_for_rm_gap
from .workout_rm_gap_validation import validate_rm_gap_payload
from .workout_published_history import build_publication_runtime_metrics
from .workout_support import (
    build_workout_review_snapshot,
    create_workout_revision,
    record_workout_audit,
    week_start_for,
)


class WorkoutApprovalActionView(OperationBaseView, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def post(self, request, workout_id, action, *args, **kwargs):
        workout = load_workout_for_approval(workout_id=workout_id)
        if not is_workout_pending_approval(workout=workout):
            messages.warning(request, 'Esse WOD ja nao esta mais aguardando aprovacao.')
            return redirect('workout-approval-board')
        review_snapshot = build_workout_review_snapshot(workout)

        if action == 'approve':
            approval_form = WorkoutApprovalDecisionForm(request.POST)
            approval_form.is_valid()
            approval_reason = approval_form.build_reason_payload()
            if requires_sensitive_confirmation(review_snapshot=review_snapshot, request=request):
                messages.error(request, 'Confirme que revisou as mudancas sensiveis antes de publicar.')
                return redirect('workout-approval-board')
            approve_workout(
                actor=request.user,
                workout=workout,
                review_snapshot=review_snapshot,
                approval_reason=approval_reason,
            )
            messages.success(request, 'WOD aprovado e publicado para os alunos.')
            return redirect('workout-approval-board')

        if action == 'reject':
            form = WorkoutRejectionForm(request.POST)
            if not validate_rejection_form(form=form):
                messages.error(request, 'Escolha um motivo e detalhe quando necessario.')
                return redirect('workout-approval-board')
            rejection_reason = form.build_reason_text()
            reject_workout(
                actor=request.user,
                workout=workout,
                rejection_reason=rejection_reason,
                rejection_category=form.cleaned_data['rejection_category'],
            )
            messages.success(request, 'WOD devolvido ao coach para ajuste.')
            return redirect('workout-approval-board')

        messages.error(request, 'Acao de aprovacao nao reconhecida.')
        return redirect('workout-approval-board')


class WorkoutFollowUpActionView(OperationBaseView, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def post(self, request, workout_id, *args, **kwargs):
        workout = load_published_workout(workout_id=workout_id)
        form = WorkoutFollowUpResolutionForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Revise o resultado da acao sugerida antes de registrar.')
            return redirect('workout-approval-board')

        payload = form.build_result_payload()
        baseline_metrics = build_publication_runtime_metrics(session=workout.session, workout=workout)
        save_workout_follow_up_action(
            actor=request.user,
            workout=workout,
            payload=payload,
            baseline_metrics=baseline_metrics,
        )
        messages.success(request, 'Resultado da acao sugerida registrado no historico operacional.')
        return redirect('workout-approval-board')


class WorkoutOperationalMemoryCreateView(OperationBaseView, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def post(self, request, workout_id, *args, **kwargs):
        workout = load_published_workout(workout_id=workout_id)
        form = WorkoutOperationalMemoryForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Revise o marco operacional antes de registrar.')
            return redirect('workout-approval-board')

        payload = form.build_memory_payload()
        create_workout_operational_memory(
            actor=request.user,
            workout=workout,
            payload=payload,
        )
        messages.success(request, 'Marco curto registrado na memoria operacional do caso.')
        return redirect('workout-approval-board')


class WorkoutWeeklyCheckpointUpdateView(OperationBaseView, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def post(self, request, *args, **kwargs):
        form = WorkoutWeeklyCheckpointForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Revise o checkpoint semanal antes de registrar.')
            return redirect('workout-approval-board')

        payload = form.build_payload()
        week_start = week_start_for(timezone.localdate())
        checkpoint, _ = WorkoutWeeklyManagementCheckpoint.objects.get_or_create(
            week_start=week_start,
            defaults={
                'execution_status': payload['execution_status'],
                'responsible_role': payload['responsible_role'],
                'closure_status': payload['closure_status'],
                'governance_commitment_status': payload['governance_commitment_status'],
                'governance_commitment_note': payload['governance_commitment_note'],
                'summary_note': payload['summary_note'],
                'updated_by': request.user,
            },
        )
        checkpoint.execution_status = payload['execution_status']
        checkpoint.responsible_role = payload['responsible_role']
        checkpoint.closure_status = payload['closure_status']
        checkpoint.governance_commitment_status = payload['governance_commitment_status']
        checkpoint.governance_commitment_note = payload['governance_commitment_note']
        checkpoint.summary_note = payload['summary_note']
        checkpoint.updated_by = request.user
        checkpoint.save(
            update_fields=[
                'execution_status',
                'responsible_role',
                'closure_status',
                'governance_commitment_status',
                'governance_commitment_note',
                'summary_note',
                'updated_by',
                'updated_at',
            ]
        )
        log_audit_event(
            actor=request.user,
            action='session_workout_weekly_checkpoint_updated',
            target=checkpoint,
            description='Owner ou manager atualizou o checkpoint semanal da gestao do WOD.',
            metadata={
                'week_start': week_start.isoformat(),
                'execution_status': checkpoint.execution_status,
                'responsible_role': checkpoint.responsible_role,
                'closure_status': checkpoint.closure_status,
                'governance_commitment_status': checkpoint.governance_commitment_status,
                'governance_commitment_note': checkpoint.governance_commitment_note,
                'summary_note': checkpoint.summary_note,
            },
        )
        messages.success(request, 'Checkpoint semanal da gestao registrado.')
        return redirect('workout-approval-board')


class WorkoutRmGapActionView(OperationBaseView, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)
    reserved_statuses = {
        AttendanceStatus.BOOKED,
        AttendanceStatus.CHECKED_IN,
        AttendanceStatus.CHECKED_OUT,
    }

    def post(self, request, workout_id, *args, **kwargs):
        workout = load_published_workout_for_rm_gap(workout_id=workout_id)
        form = WorkoutRmGapActionForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Revise a acao curta do corredor de RM antes de salvar.')
            return redirect('workout-approval-board')

        payload = form.build_payload()
        validation_result = validate_rm_gap_payload(
            workout=workout,
            payload=payload,
            reserved_statuses=self.reserved_statuses,
        )
        if not validation_result['ok']:
            messages.error(request, validation_result['message'])
            return redirect('workout-approval-board')

        attendance = validation_result['attendance']
        action = save_workout_rm_gap_action(
            actor=request.user,
            workout=workout,
            attendance=attendance,
            payload=payload,
        )
        messages.success(request, f'{action.get_status_display()} registrado para {attendance.student.full_name}.')
        return redirect('workout-approval-board')
