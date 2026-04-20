"""
ARQUIVO: actions do editor de WOD do coach.

POR QUE ELE EXISTE:
- separa as mutacoes reais do editor de WOD da casca HTTP de `workspace_views.py`.

O QUE ESTE ARQUIVO FAZ:
1. salva rascunho do workout.
2. gerencia blocos do workout.
3. gerencia movimentos dos blocos.
4. envia workout para aprovacao e duplica para outra aula.

PONTOS CRITICOS:
- qualquer mudanca aqui altera estado real do WOD, auditoria e feedback visual do coach.
- manter mensagens, redirects e side effects identicos ao fluxo anterior.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from operations.forms import (
    CoachSessionWorkoutForm,
    CoachWorkoutBlockForm,
    CoachWorkoutMovementForm,
    WorkoutDuplicateForm,
)
from operations.models import ClassSession
from student_app.models import (
    SessionWorkout,
    SessionWorkoutBlock,
    SessionWorkoutMovement,
    SessionWorkoutRevisionEvent,
    SessionWorkoutStatus,
)

from .workout_support import (
    create_workout_revision as _create_workout_revision,
    record_workout_audit as _record_workout_audit,
)


class CoachSessionWorkoutEditorActionsMixin:
    def _handle_save_workout(self, request):
        form = CoachSessionWorkoutForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Revise titulo e observacoes do WOD.')
            return self.render_to_response(self._build_context(workout_form=form))
        workout = self._get_or_create_workout()
        workout.title = form.cleaned_data['title']
        workout.coach_notes = form.cleaned_data['coach_notes']
        if workout.status == SessionWorkoutStatus.PUBLISHED:
            workout.status = SessionWorkoutStatus.DRAFT
            workout.approved_by = None
            workout.approved_at = None
        elif workout.status == SessionWorkoutStatus.REJECTED:
            workout.status = SessionWorkoutStatus.DRAFT
        workout.version += 1
        workout.save(
            update_fields=['title', 'coach_notes', 'status', 'approved_by', 'approved_at', 'version', 'updated_at']
        )
        _record_workout_audit(
            actor=request.user,
            workout=workout,
            action='session_workout_draft_saved',
            description='Coach salvou rascunho do WOD.',
            metadata={'session_id': workout.session_id, 'version': workout.version, 'status': workout.status},
        )
        messages.success(request, 'Cabecalho do WOD salvo como rascunho.')
        return redirect('coach-session-workout-editor', session_id=self.session.id)

    def _handle_add_block(self, request):
        form = CoachWorkoutBlockForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Revise os dados do bloco antes de adicionar.')
            return self.render_to_response(self._build_context(block_form=form))
        workout = self._get_or_create_workout()
        SessionWorkoutBlock.objects.create(
            workout=workout,
            title=form.cleaned_data['title'],
            kind=form.cleaned_data['kind'],
            notes=form.cleaned_data['notes'],
            sort_order=form.cleaned_data['sort_order'],
        )
        if workout.status in {SessionWorkoutStatus.PUBLISHED, SessionWorkoutStatus.REJECTED}:
            workout.status = SessionWorkoutStatus.DRAFT
            workout.approved_by = None
            workout.approved_at = None
            workout.version += 1
            workout.save(update_fields=['status', 'approved_by', 'approved_at', 'version', 'updated_at'])
        _record_workout_audit(
            actor=request.user,
            workout=workout,
            action='session_workout_block_added',
            description='Coach adicionou bloco ao WOD.',
            metadata={'session_id': workout.session_id, 'version': workout.version, 'block_title': form.cleaned_data['title']},
        )
        messages.success(request, 'Bloco adicionado ao WOD.')
        return redirect('coach-session-workout-editor', session_id=self.session.id)

    def _handle_delete_block(self, request):
        workout = self._get_workout()
        block = get_object_or_404(SessionWorkoutBlock, pk=request.POST.get('block_id'), workout=workout)
        block.delete()
        if workout.status in {SessionWorkoutStatus.PUBLISHED, SessionWorkoutStatus.REJECTED}:
            workout.status = SessionWorkoutStatus.DRAFT
            workout.approved_by = None
            workout.approved_at = None
        workout.version += 1
        workout.save(update_fields=['status', 'approved_by', 'approved_at', 'version', 'updated_at'])
        _record_workout_audit(
            actor=request.user,
            workout=workout,
            action='session_workout_block_deleted',
            description='Coach removeu bloco do WOD.',
            metadata={'session_id': workout.session_id, 'version': workout.version, 'block_id': request.POST.get('block_id')},
        )
        messages.success(request, 'Bloco removido do WOD.')
        return redirect('coach-session-workout-editor', session_id=self.session.id)

    def _handle_update_block(self, request):
        workout = self._get_workout()
        form = CoachWorkoutBlockForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Revise os dados do bloco antes de salvar a edicao.')
            return self.render_to_response(self._build_context(block_form=form))
        block = get_object_or_404(SessionWorkoutBlock, pk=form.cleaned_data['block_id'], workout=workout)
        block.title = form.cleaned_data['title']
        block.kind = form.cleaned_data['kind']
        block.notes = form.cleaned_data['notes']
        block.sort_order = form.cleaned_data['sort_order']
        block.save(update_fields=['title', 'kind', 'notes', 'sort_order', 'updated_at'])
        if workout.status in {SessionWorkoutStatus.PUBLISHED, SessionWorkoutStatus.REJECTED, SessionWorkoutStatus.PENDING_APPROVAL}:
            workout.status = SessionWorkoutStatus.DRAFT
            workout.approved_by = None
            workout.approved_at = None
        workout.version += 1
        workout.save(update_fields=['status', 'approved_by', 'approved_at', 'version', 'updated_at'])
        _record_workout_audit(
            actor=request.user,
            workout=workout,
            action='session_workout_block_updated',
            description='Coach atualizou bloco do WOD.',
            metadata={'session_id': workout.session_id, 'version': workout.version, 'block_id': block.id},
        )
        messages.success(request, 'Bloco atualizado.')
        return redirect('coach-session-workout-editor', session_id=self.session.id)

    def _handle_add_movement(self, request):
        form = CoachWorkoutMovementForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Revise os campos do movimento antes de salvar.')
            return self.render_to_response(self._build_context(movement_form=form))
        workout = self._get_or_create_workout()
        block = get_object_or_404(SessionWorkoutBlock, pk=form.cleaned_data['block_id'], workout=workout)
        SessionWorkoutMovement.objects.create(
            block=block,
            movement_slug=form.cleaned_data['movement_slug'],
            movement_label=form.cleaned_data['movement_label'],
            sets=form.cleaned_data['sets'],
            reps=form.cleaned_data['reps'],
            load_type=form.cleaned_data['load_type'],
            load_value=form.cleaned_data['load_value'],
            notes=form.cleaned_data['notes'],
            sort_order=form.cleaned_data['sort_order'],
        )
        if workout.status in {SessionWorkoutStatus.PUBLISHED, SessionWorkoutStatus.REJECTED}:
            workout.status = SessionWorkoutStatus.DRAFT
            workout.approved_by = None
            workout.approved_at = None
        workout.version += 1
        workout.save(update_fields=['status', 'approved_by', 'approved_at', 'version', 'updated_at'])
        _record_workout_audit(
            actor=request.user,
            workout=workout,
            action='session_workout_movement_added',
            description='Coach adicionou movimento ao WOD.',
            metadata={'session_id': workout.session_id, 'version': workout.version, 'movement_label': form.cleaned_data['movement_label']},
        )
        messages.success(request, 'Movimento adicionado ao bloco.')
        return redirect('coach-session-workout-editor', session_id=self.session.id)

    def _handle_delete_movement(self, request):
        workout = self._get_workout()
        movement = get_object_or_404(
            SessionWorkoutMovement.objects.select_related('block', 'block__workout'),
            pk=request.POST.get('movement_id'),
            block__workout=workout,
        )
        movement.delete()
        if workout.status in {SessionWorkoutStatus.PUBLISHED, SessionWorkoutStatus.REJECTED}:
            workout.status = SessionWorkoutStatus.DRAFT
            workout.approved_by = None
            workout.approved_at = None
        workout.version += 1
        workout.save(update_fields=['status', 'approved_by', 'approved_at', 'version', 'updated_at'])
        _record_workout_audit(
            actor=request.user,
            workout=workout,
            action='session_workout_movement_deleted',
            description='Coach removeu movimento do WOD.',
            metadata={'session_id': workout.session_id, 'version': workout.version, 'movement_id': request.POST.get('movement_id')},
        )
        messages.success(request, 'Movimento removido do WOD.')
        return redirect('coach-session-workout-editor', session_id=self.session.id)

    def _handle_update_movement(self, request):
        workout = self._get_workout()
        form = CoachWorkoutMovementForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Revise os campos do movimento antes de salvar a edicao.')
            return self.render_to_response(self._build_context(movement_form=form))
        movement = get_object_or_404(
            SessionWorkoutMovement.objects.select_related('block', 'block__workout'),
            pk=form.cleaned_data['movement_id'],
            block__workout=workout,
        )
        target_block = get_object_or_404(SessionWorkoutBlock, pk=form.cleaned_data['block_id'], workout=workout)
        movement.block = target_block
        movement.movement_slug = form.cleaned_data['movement_slug']
        movement.movement_label = form.cleaned_data['movement_label']
        movement.sets = form.cleaned_data['sets']
        movement.reps = form.cleaned_data['reps']
        movement.load_type = form.cleaned_data['load_type']
        movement.load_value = form.cleaned_data['load_value']
        movement.notes = form.cleaned_data['notes']
        movement.sort_order = form.cleaned_data['sort_order']
        movement.save(
            update_fields=[
                'block',
                'movement_slug',
                'movement_label',
                'sets',
                'reps',
                'load_type',
                'load_value',
                'notes',
                'sort_order',
                'updated_at',
            ]
        )
        if workout.status in {SessionWorkoutStatus.PUBLISHED, SessionWorkoutStatus.REJECTED, SessionWorkoutStatus.PENDING_APPROVAL}:
            workout.status = SessionWorkoutStatus.DRAFT
            workout.approved_by = None
            workout.approved_at = None
        workout.version += 1
        workout.save(update_fields=['status', 'approved_by', 'approved_at', 'version', 'updated_at'])
        _record_workout_audit(
            actor=request.user,
            workout=workout,
            action='session_workout_movement_updated',
            description='Coach atualizou movimento do WOD.',
            metadata={'session_id': workout.session_id, 'version': workout.version, 'movement_id': movement.id},
        )
        messages.success(request, 'Movimento atualizado.')
        return redirect('coach-session-workout-editor', session_id=self.session.id)

    def _handle_submit_for_approval(self, request):
        workout = self._get_workout()
        if workout is None:
            messages.error(request, 'Salve um rascunho antes de enviar para aprovacao.')
            return redirect('coach-session-workout-editor', session_id=self.session.id)
        if not workout.blocks.exists():
            messages.error(request, 'Crie pelo menos um bloco antes de enviar o WOD para aprovacao.')
            return redirect('coach-session-workout-editor', session_id=self.session.id)
        workout.status = SessionWorkoutStatus.PENDING_APPROVAL
        workout.submitted_by = request.user
        workout.submitted_at = timezone.now()
        workout.rejected_by = None
        workout.rejected_at = None
        workout.rejection_reason = ''
        workout.save(
            update_fields=[
                'status',
                'submitted_by',
                'submitted_at',
                'rejected_by',
                'rejected_at',
                'rejection_reason',
                'updated_at',
            ]
        )
        _create_workout_revision(workout=workout, actor=request.user, event=SessionWorkoutRevisionEvent.SUBMITTED)
        _record_workout_audit(
            actor=request.user,
            workout=workout,
            action='session_workout_submitted_for_approval',
            description='Coach enviou WOD para aprovacao.',
            metadata={'session_id': workout.session_id, 'version': workout.version},
        )
        messages.success(request, 'WOD enviado para aprovacao do owner ou manager.')
        return redirect('coach-session-workout-editor', session_id=self.session.id)

    def _handle_duplicate_workout(self, request):
        workout = self._get_workout()
        form = WorkoutDuplicateForm(request.POST)
        if workout is None:
            messages.error(request, 'Salve um WOD antes de duplicar.')
            return redirect('coach-session-workout-editor', session_id=self.session.id)
        if not form.is_valid():
            messages.error(request, 'Escolha uma aula valida para duplicacao.')
            return redirect('coach-session-workout-editor', session_id=self.session.id)
        target_session = get_object_or_404(ClassSession, pk=form.cleaned_data['target_session_id'])
        if hasattr(target_session, 'workout'):
            messages.error(request, 'A aula de destino ja possui um WOD. Escolha outra aula.')
            return redirect('coach-session-workout-editor', session_id=self.session.id)
        duplicated_workout = SessionWorkout.objects.create(
            session=target_session,
            title=workout.title,
            coach_notes=workout.coach_notes,
            status=SessionWorkoutStatus.DRAFT,
            created_by=request.user,
            version=1,
        )
        for block in workout.blocks.all():
            duplicated_block = SessionWorkoutBlock.objects.create(
                workout=duplicated_workout,
                kind=block.kind,
                title=block.title,
                notes=block.notes,
                sort_order=block.sort_order,
            )
            for movement in block.movements.all():
                SessionWorkoutMovement.objects.create(
                    block=duplicated_block,
                    movement_slug=movement.movement_slug,
                    movement_label=movement.movement_label,
                    sets=movement.sets,
                    reps=movement.reps,
                    load_type=movement.load_type,
                    load_value=movement.load_value,
                    notes=movement.notes,
                    sort_order=movement.sort_order,
                )
        _create_workout_revision(
            workout=duplicated_workout,
            actor=request.user,
            event=SessionWorkoutRevisionEvent.DUPLICATED,
            extra_snapshot={'source_workout_id': workout.id, 'source_session_id': workout.session_id},
        )
        _record_workout_audit(
            actor=request.user,
            workout=duplicated_workout,
            action='session_workout_duplicated',
            description='Coach duplicou WOD para outra aula.',
            metadata={
                'session_id': duplicated_workout.session_id,
                'version': duplicated_workout.version,
                'source_workout_id': workout.id,
                'source_session_id': workout.session_id,
            },
        )
        messages.success(request, 'WOD duplicado como rascunho para a nova aula.')
        return redirect('coach-session-workout-editor', session_id=target_session.id)
