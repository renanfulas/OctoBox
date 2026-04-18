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
from django.utils import timezone
from django.views import View

from access.roles import ROLE_MANAGER, ROLE_OWNER
from auditing import log_audit_event
from student_app.models import (
    SessionWorkout,
    SessionWorkoutFollowUpAction,
    SessionWorkoutOperationalMemory,
    SessionWorkoutRevisionEvent,
    SessionWorkoutStatus,
    WorkoutWeeklyManagementCheckpoint,
)

from .base_views import OperationBaseView
from .forms import (
    WorkoutApprovalDecisionForm,
    WorkoutFollowUpResolutionForm,
    WorkoutOperationalMemoryForm,
    WorkoutRejectionForm,
    WorkoutWeeklyCheckpointForm,
)
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
        workout = get_object_or_404(SessionWorkout, pk=workout_id)
        if workout.status != SessionWorkoutStatus.PENDING_APPROVAL:
            messages.warning(request, 'Esse WOD ja nao esta mais aguardando aprovacao.')
            return redirect('workout-approval-board')
        review_snapshot = build_workout_review_snapshot(workout)

        if action == 'approve':
            approval_form = WorkoutApprovalDecisionForm(request.POST)
            approval_form.is_valid()
            approval_reason = approval_form.build_reason_payload()
            if review_snapshot['requires_confirmation'] and request.POST.get('confirm_sensitive_changes') != '1':
                messages.error(request, 'Confirme que revisou as mudancas sensiveis antes de publicar.')
                return redirect('workout-approval-board')
            workout.status = SessionWorkoutStatus.PUBLISHED
            workout.approved_by = request.user
            workout.approved_at = timezone.now()
            workout.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
            create_workout_revision(
                workout=workout,
                actor=request.user,
                event=SessionWorkoutRevisionEvent.PUBLISHED,
                extra_snapshot={
                    'approved_with_sensitive_confirmation': review_snapshot['requires_confirmation'],
                    'approval_reason_category': approval_reason['category'],
                    'approval_reason_label': approval_reason['label'],
                    'approval_reason_note': approval_reason['note'],
                    'approval_reason_summary': approval_reason['summary'],
                },
            )
            record_workout_audit(
                actor=request.user,
                workout=workout,
                action='session_workout_published',
                description='Owner ou manager aprovou e publicou o WOD.',
                metadata={
                    'session_id': workout.session_id,
                    'version': workout.version,
                    'approved_with_sensitive_confirmation': review_snapshot['requires_confirmation'],
                    'approval_reason_category': approval_reason['category'],
                    'approval_reason_label': approval_reason['label'],
                    'approval_reason_note': approval_reason['note'],
                },
            )
            messages.success(request, 'WOD aprovado e publicado para os alunos.')
            return redirect('workout-approval-board')

        if action == 'reject':
            form = WorkoutRejectionForm(request.POST)
            if not form.is_valid():
                messages.error(request, 'Escolha um motivo e detalhe quando necessario.')
                return redirect('workout-approval-board')
            rejection_reason = form.build_reason_text()
            workout.status = SessionWorkoutStatus.REJECTED
            workout.rejected_by = request.user
            workout.rejected_at = timezone.now()
            workout.rejection_reason = rejection_reason
            workout.save(update_fields=['status', 'rejected_by', 'rejected_at', 'rejection_reason', 'updated_at'])
            create_workout_revision(
                workout=workout,
                actor=request.user,
                event=SessionWorkoutRevisionEvent.REJECTED,
                extra_snapshot={
                    'rejection_reason': rejection_reason,
                    'rejection_category': form.cleaned_data['rejection_category'],
                },
            )
            record_workout_audit(
                actor=request.user,
                workout=workout,
                action='session_workout_rejected',
                description='Owner ou manager rejeitou o WOD para ajuste.',
                metadata={
                    'session_id': workout.session_id,
                    'version': workout.version,
                    'rejection_reason': rejection_reason,
                    'rejection_category': form.cleaned_data['rejection_category'],
                },
            )
            messages.success(request, 'WOD devolvido ao coach para ajuste.')
            return redirect('workout-approval-board')

        messages.error(request, 'Acao de aprovacao nao reconhecida.')
        return redirect('workout-approval-board')


class WorkoutFollowUpActionView(OperationBaseView, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def post(self, request, workout_id, *args, **kwargs):
        workout = get_object_or_404(SessionWorkout, pk=workout_id, status=SessionWorkoutStatus.PUBLISHED)
        form = WorkoutFollowUpResolutionForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Revise o resultado da acao sugerida antes de registrar.')
            return redirect('workout-approval-board')

        payload = form.build_result_payload()
        baseline_metrics = build_publication_runtime_metrics(session=workout.session, workout=workout)
        follow_up_action, created = SessionWorkoutFollowUpAction.objects.get_or_create(
            workout=workout,
            action_key=payload['action_key'],
            defaults={
                'action_label': payload['action_label'],
                'status': payload['status'],
                'outcome_note': payload['outcome_note'],
                'baseline_metrics': baseline_metrics,
                'resolved_by': request.user,
                'resolved_at': timezone.now(),
            },
        )
        if not created:
            follow_up_action.action_label = payload['action_label']
            follow_up_action.status = payload['status']
            follow_up_action.outcome_note = payload['outcome_note']
            if not follow_up_action.baseline_metrics:
                follow_up_action.baseline_metrics = baseline_metrics
            follow_up_action.resolved_by = request.user
            follow_up_action.resolved_at = timezone.now()
            follow_up_action.save(
                update_fields=[
                    'action_label',
                    'status',
                    'outcome_note',
                    'baseline_metrics',
                    'resolved_by',
                    'resolved_at',
                    'updated_at',
                ]
            )
        record_workout_audit(
            actor=request.user,
            workout=workout,
            action='session_workout_follow_up_registered',
            description='Owner ou manager registrou o resultado de uma acao sugerida apos a publicacao.',
            metadata={
                'session_id': workout.session_id,
                'version': workout.version,
                'action_key': follow_up_action.action_key,
                'action_label': follow_up_action.action_label,
                'result_status': follow_up_action.status,
                'result_status_label': follow_up_action.get_status_display(),
                'outcome_note': follow_up_action.outcome_note,
                'baseline_metrics': follow_up_action.baseline_metrics,
            },
        )
        messages.success(request, 'Resultado da acao sugerida registrado no historico operacional.')
        return redirect('workout-approval-board')


class WorkoutOperationalMemoryCreateView(OperationBaseView, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def post(self, request, workout_id, *args, **kwargs):
        workout = get_object_or_404(SessionWorkout, pk=workout_id, status=SessionWorkoutStatus.PUBLISHED)
        form = WorkoutOperationalMemoryForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Revise o marco operacional antes de registrar.')
            return redirect('workout-approval-board')

        payload = form.build_memory_payload()
        memory = SessionWorkoutOperationalMemory.objects.create(
            workout=workout,
            kind=payload['kind'],
            note=payload['note'],
            created_by=request.user,
        )
        record_workout_audit(
            actor=request.user,
            workout=workout,
            action='session_workout_operational_memory_created',
            description='Owner ou manager registrou um marco curto da memoria operacional do caso.',
            metadata={
                'session_id': workout.session_id,
                'version': workout.version,
                'memory_kind': memory.kind,
                'memory_kind_label': memory.get_kind_display(),
                'note': memory.note,
            },
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
