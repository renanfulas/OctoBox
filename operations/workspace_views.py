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
from django.urls import reverse
from django.utils import timezone
from django.views import View

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
from operations.workout_support import (
    create_workout_revision as _create_workout_revision,
    record_workout_audit as _record_workout_audit,
)
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
        subtitle='Chegada, agenda e cobranca curta no balcao.',
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
        subtitle='Triagem, vinculo e cobranca em ordem curta.',
        scope='operations-manager',
        snapshot=snapshot,
        focus_key='manager_operational_focus',
    )




class OwnerWorkspaceView(OperationBaseView):
    allowed_roles = (ROLE_OWNER,)
    template_name = 'operations/owner.html'
    page_title = 'Minha operacao'
    page_subtitle = 'Crescimento, caixa e estrutura sem leitura longa.'

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
    page_subtitle = 'Rastros, fronteiras e manutencao sem invadir a operacao.'

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
    page_subtitle = 'Triagem, vinculo e cobranca em ordem curta.'

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
    page_subtitle = 'Aula, presenca e ocorrencia com leitura curta.'

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


class CoachSessionWorkoutEditorView(OperationBaseView):
    allowed_roles = (ROLE_COACH,)
    template_name = 'operations/coach_session_workout_editor.html'
    page_title = 'Publicar WOD'
    page_subtitle = 'Monte o treino da aula com blocos e movimentos sem sair do fluxo do coach.'

    def dispatch(self, request, *args, **kwargs):
        self.session = get_object_or_404(
            ClassSession.objects.select_related('coach', 'workout').prefetch_related('workout__blocks__movements'),
            pk=kwargs['session_id'],
        )
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

    def _build_page_payload(self, context):
        payload = build_page_payload(
            context={
                'page_key': 'operations-coach-wod-editor',
                'title': self.page_title,
                'subtitle': self.page_subtitle,
                'mode': 'workspace',
                'role_slug': context['current_role'].slug,
            },
            data={
                'hero': build_page_hero(
                    eyebrow='Coach',
                    title=f'WOD da aula: {self.session.title}',
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

    def _build_context(self, *, workout_form=None, block_form=None, movement_form=None):
        context = self.get_context_data()
        context.update(self.get_base_context())
        workout = self._get_workout()
        duplicate_sessions = ClassSession.objects.filter(scheduled_at__gte=self.session.scheduled_at).exclude(pk=self.session.id).order_by('scheduled_at')[:12]
        self._build_page_payload(context)
        context.update(
            {
                'session': self.session,
                'workout': workout,
                'workout_form': workout_form or CoachSessionWorkoutForm(
                    initial={
                        'title': getattr(workout, 'title', self.session.title),
                        'coach_notes': getattr(workout, 'coach_notes', ''),
                    }
                ),
                'block_form': block_form or CoachWorkoutBlockForm(
                    initial={
                        'sort_order': (workout.blocks.count() + 1) if workout is not None else 1,
                    }
                ),
                'movement_form': movement_form or CoachWorkoutMovementForm(
                    initial={
                        'sort_order': 1,
                    }
                ),
                'duplicate_sessions': duplicate_sessions,
                'duplicate_form': WorkoutDuplicateForm(),
            }
        )
        return context

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self._build_context())

    def post(self, request, *args, **kwargs):
        intent = request.POST.get('intent')
        if intent == 'save_workout':
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

        if intent == 'add_block':
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

        if intent == 'delete_block':
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

        if intent == 'update_block':
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

        if intent == 'add_movement':
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

        if intent == 'delete_movement':
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

        if intent == 'update_movement':
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

        if intent == 'submit_for_approval':
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

        if intent == 'duplicate_workout':
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

        messages.error(request, 'Acao de WOD nao reconhecida neste fluxo.')
        return redirect('coach-session-workout-editor', session_id=self.session.id)


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
    page_subtitle = 'Chegada, agenda e cobranca curta no balcao.'

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
    page_subtitle = 'Central de comunicacao e relacionamento com seus alunos.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        context['whatsapp_placeholder_hero'] = build_page_hero(
            eyebrow='Mensagens',
            title='Central em preparo.',
            copy='Veja o que ja esta definido, o que ainda chega e para onde seguir sem ruido.',
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
        )
        return context
