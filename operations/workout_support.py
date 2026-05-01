"""
ARQUIVO: suporte compartilhado do corredor de WOD operacional.

POR QUE ELE EXISTE:
- centraliza helpers compartilhados por board, editor e action views sem depender de `workspace_views.py`.

O QUE ESTE ARQUIVO FAZ:
1. serializa snapshot de WOD.
2. cria revisoes e auditoria.
3. monta review snapshot para aprovacao.
4. monta historico curto de checkpoint semanal.
5. expoe utilitarios de semana operacional.

PONTOS CRITICOS:
- manter este modulo livre de request/response.
- qualquer regressao aqui afeta editor, aprovacao e trilha de auditoria.
"""

from datetime import timedelta

from django.utils import timezone

from auditing import log_audit_event
from student_app.models import (
    SessionWorkoutRevision,
    SessionWorkoutRevisionEvent,
    SessionWorkoutStatus,
    WorkoutWeeklyManagementCheckpoint,
)

from .workout_approval_policy import resolve_workout_approval_policy
from .workout_telemetry import emit_wod_policy_decision
from .workout_board_builders import (
    build_snapshot_presentation,
    build_student_preview_diff,
    build_student_preview_payload,
    build_workout_decision_assist,
    build_workout_diff_snapshot,
    normalize_load_type_label,
    build_snapshot_blocks,
)


def serialize_workout_snapshot(workout):
    blocks = []
    for block in workout.blocks.all():
        blocks.append(
            {
                'sort_order': block.sort_order,
                'title': block.title,
                'kind': block.kind,
                'kind_label': block.get_kind_display(),
                'notes': block.notes,
                'movements': [
                    {
                        'sort_order': movement.sort_order,
                        'movement_slug': movement.movement_slug,
                        'movement_label': movement.movement_label,
                        'sets': movement.sets,
                        'reps': movement.reps,
                        'load_type': movement.load_type,
                        'load_value': str(movement.load_value) if movement.load_value is not None else '',
                        'notes': movement.notes,
                    }
                    for movement in block.movements.all()
                ],
            }
        )
    return {
        'title': workout.title,
        'coach_notes': workout.coach_notes,
        'status': workout.status,
        'session_id': workout.session_id,
        'version': workout.version,
        'blocks': blocks,
    }


def create_workout_revision(*, workout, actor, event, extra_snapshot=None):
    snapshot = serialize_workout_snapshot(workout)
    if extra_snapshot:
        snapshot.update(extra_snapshot)
    return SessionWorkoutRevision.objects.create(
        workout=workout,
        version=workout.version,
        event=event,
        created_by=actor,
        snapshot=snapshot,
    )


def record_workout_audit(*, actor, workout, action, description, metadata=None):
    log_audit_event(
        actor=actor,
        action=action,
        target=workout,
        description=description,
        metadata=metadata or {},
    )


def build_workout_review_snapshot(workout):
    blocks = list(workout.blocks.all())
    movements = [movement for block in blocks for movement in block.movements.all()]
    block_kind_labels = []
    for block in blocks:
        kind_label = block.get_kind_display()
        if kind_label not in block_kind_labels:
            block_kind_labels.append(kind_label)

    percentage_rm_count = sum(1 for movement in movements if movement.load_type == 'percentage_of_rm')
    fixed_load_count = sum(1 for movement in movements if movement.load_type == 'fixed_kg')
    free_load_count = sum(1 for movement in movements if movement.load_type == 'free')

    review_signals = [
        {
            'label': 'Blocos',
            'value': len(blocks),
            'tone': 'info',
            'copy': 'Quantos capitulos esse treino entrega ao aluno.',
        },
        {
            'label': 'Movimentos',
            'value': len(movements),
            'tone': 'accent',
            'copy': 'Volume total de exercicios que o aprovador vai liberar.',
        },
        {
            'label': '% RM',
            'value': percentage_rm_count,
            'tone': 'success' if percentage_rm_count else 'info',
            'copy': 'Movimentos que usam recomendacao personalizada por RM.',
        },
        {
            'label': 'Carga fixa',
            'value': fixed_load_count,
            'tone': 'warning' if fixed_load_count else 'info',
            'copy': 'Movimentos que ja chegam com peso fechado.',
        },
        {
            'label': 'Carga livre',
            'value': free_load_count,
            'tone': 'info',
            'copy': 'Movimentos em que o coach deixa ajuste de esforco livre.',
        },
    ]

    block_summaries = []
    for block in blocks:
        block_movements = list(block.movements.all())
        block_summaries.append(
            {
                'title': block.title,
                'kind_label': block.get_kind_display(),
                'notes': block.notes,
                'sort_order': block.sort_order,
                'movement_count': len(block_movements),
                'movement_preview': ', '.join(movement.movement_label for movement in block_movements[:3]),
            }
        )

    submitted_by_label = ''
    if workout.submitted_by is not None:
        submitted_by_label = workout.submitted_by.get_full_name() or workout.submitted_by.username

    current_snapshot = serialize_workout_snapshot(workout)
    last_published_revision = workout.revisions.filter(event=SessionWorkoutRevisionEvent.PUBLISHED).order_by('-created_at', '-id').first()
    diff_snapshot = build_workout_diff_snapshot(
        published_snapshot=(last_published_revision.snapshot if last_published_revision is not None else None),
        current_snapshot=current_snapshot,
    )
    previous_snapshot = last_published_revision.snapshot if last_published_revision is not None else {}
    comparison_snapshot = {
        'previous': build_snapshot_presentation(previous_snapshot) if last_published_revision is not None else None,
        'current': build_snapshot_presentation(current_snapshot),
    }
    for side in ('previous', 'current'):
        snapshot_side = comparison_snapshot.get(side)
        if snapshot_side is None:
            continue
        for block in snapshot_side['blocks']:
            for movement in block['movements']:
                movement['load_type_label'] = normalize_load_type_label(movement.get('load_type'))
    revision_history = []
    for revision in workout.revisions.select_related('created_by').order_by('-created_at', '-id')[:5]:
        actor_label = ''
        if revision.created_by is not None:
            actor_label = revision.created_by.get_full_name() or revision.created_by.username
        created_at_local = timezone.localtime(revision.created_at)
        detail = ''
        snapshot = revision.snapshot or {}
        if snapshot.get('approval_reason_summary'):
            detail = snapshot['approval_reason_summary']
        elif snapshot.get('rejection_reason'):
            detail = snapshot['rejection_reason']
        revision_history.append(
            {
                'event_label': revision.get_event_display(),
                'version': revision.version,
                'created_at_label': created_at_local.strftime('%d/%m %H:%M'),
                'actor_label': actor_label,
                'detail': detail,
                'sort_at': created_at_local,
            }
        )
    if workout.submitted_at:
        submitted_at_local = timezone.localtime(workout.submitted_at)
        revision_history.append(
            {
                'event_label': 'Entrada na fila',
                'version': workout.version,
                'created_at_label': submitted_at_local.strftime('%d/%m %H:%M'),
                'actor_label': submitted_by_label,
                'sort_at': submitted_at_local,
            }
        )
    revision_history = sorted(
        revision_history,
        key=lambda item: (item['sort_at'], item['version']),
        reverse=True,
    )[:6]
    student_preview_current = build_student_preview_payload(
        session_title=workout.session.title,
        session_scheduled_label=workout.session.scheduled_at.strftime('%d/%m %H:%M'),
        coach_name=workout.session.coach.get_full_name() if workout.session.coach else 'Equipe OctoBox',
        workout_title=workout.title or workout.session.title,
        coach_notes=workout.coach_notes,
        blocks=blocks,
    )
    student_preview_previous = None
    if last_published_revision is not None:
        student_preview_previous = build_student_preview_payload(
            session_title=workout.session.title,
            session_scheduled_label=workout.session.scheduled_at.strftime('%d/%m %H:%M'),
            coach_name=workout.session.coach.get_full_name() if workout.session.coach else 'Equipe OctoBox',
            workout_title=previous_snapshot.get('title') or workout.session.title,
            coach_notes=previous_snapshot.get('coach_notes', ''),
            blocks=build_snapshot_blocks(previous_snapshot),
        )
    student_preview_diff = build_student_preview_diff(
        previous_preview=student_preview_previous,
        current_preview=student_preview_current,
    )
    decision_assist = build_workout_decision_assist(
        workout=workout,
        diff_snapshot=diff_snapshot,
        student_preview_diff=student_preview_diff,
    )

    return {
        'submitted_by_label': submitted_by_label,
        'submitted_at_label': timezone.localtime(workout.submitted_at).strftime('%d/%m %H:%M') if workout.submitted_at else '',
        'block_kind_labels': block_kind_labels,
        'review_signals': review_signals,
        'block_summaries': block_summaries,
        'movement_total': len(movements),
        'has_percentage_rm': percentage_rm_count > 0,
        'has_fixed_load': fixed_load_count > 0,
        'has_free_load': free_load_count > 0,
        'review_summary': (
            f'{len(blocks)} bloco(s), {len(movements)} movimento(s) e {percentage_rm_count} prescricao(oes) por % RM.'
        ),
        'revision_digest': (
            f'Versao {workout.version} aguardando leitura final com {len(block_kind_labels)} tipo(s) de bloco.'
        ),
        'diff_snapshot': diff_snapshot,
        'requires_confirmation': diff_snapshot['is_sensitive'],
        'comparison_snapshot': comparison_snapshot,
        'decision_assist': decision_assist,
        'student_preview': {
            'previous': student_preview_previous,
            'current': student_preview_current,
            'diff': student_preview_diff,
        },
        'last_published_revision': last_published_revision,
        'revision_history': revision_history,
    }


def build_weekly_checkpoint_history(*, limit=4):
    history = []
    checkpoints = WorkoutWeeklyManagementCheckpoint.objects.select_related('updated_by').order_by('-week_start')[:limit]
    for checkpoint in checkpoints:
        updated_by_label = ''
        if checkpoint.updated_by is not None:
            updated_by_label = checkpoint.updated_by.get_full_name() or checkpoint.updated_by.username
        history.append(
            {
                'week_label': checkpoint.week_start.strftime('%d/%m/%Y'),
                'week_start': checkpoint.week_start,
                'execution_status': checkpoint.execution_status,
                'execution_status_label': checkpoint.get_execution_status_display(),
                'responsible_role': checkpoint.responsible_role,
                'responsible_role_label': checkpoint.get_responsible_role_display(),
                'closure_status': checkpoint.closure_status,
                'closure_status_label': checkpoint.get_closure_status_display() if checkpoint.closure_status else 'Sem fechamento',
                'governance_commitment_status': checkpoint.governance_commitment_status,
                'governance_commitment_status_label': checkpoint.get_governance_commitment_status_display(),
                'governance_commitment_note': checkpoint.governance_commitment_note,
                'summary_note': checkpoint.summary_note,
                'updated_by_label': updated_by_label,
            }
        )
    return history


def week_start_for(date_value):
    return date_value - timedelta(days=date_value.weekday())




def should_require_workout_approval(*, workout, coach, source, source_template=None):
    policy = resolve_workout_approval_policy(actor=coach, session=getattr(workout, 'session', None))
    if policy == 'strict':
        return True
    if policy == 'trusted_template':
        # SmartPlan produz output canonico validado — semanticamente equivalente a um
        # template confiavel. Bypass segue a mesma logica de trusted_template.
        if source == 'smartplan':
            return False
        if source == 'template' and getattr(source_template, 'is_trusted', False):
            return False
    if policy == 'coach_autonomy' and getattr(coach, 'is_trusted_author', False):
        return False
    return True


def route_workout_submission(*, actor, workout, source='manual', source_template=None):
    requires_approval = should_require_workout_approval(
        workout=workout,
        coach=actor,
        source=source,
        source_template=source_template,
    )
    policy = resolve_workout_approval_policy(actor=actor, session=getattr(workout, 'session', None))
    source_template_id = getattr(source_template, 'id', None)
    source_template_trusted = bool(getattr(source_template, 'is_trusted', False))

    workout.rejected_by = None
    workout.rejected_at = None
    workout.rejection_reason = ''

    if requires_approval:
        workout.status = SessionWorkoutStatus.PENDING_APPROVAL
        workout.submitted_by = actor
        workout.submitted_at = timezone.now()
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
        decision_snapshot = {
            'approval_policy': policy,
            'submission_source': source,
            'source_template_id': source_template_id,
            'source_template_trusted': source_template_trusted,
            'bypass_approval': False,
            'policy_decision_label': 'Enviado para aprovacao',
        }
        create_workout_revision(
            workout=workout,
            actor=actor,
            event=SessionWorkoutRevisionEvent.SUBMITTED,
            extra_snapshot=decision_snapshot,
        )
        record_workout_audit(
            actor=actor,
            workout=workout,
            action='session_workout_submitted_for_approval',
            description='Coach enviou WOD para aprovacao conforme politica ativa.',
            metadata={
                'session_id': workout.session_id,
                'version': workout.version,
                **decision_snapshot,
            },
        )
        emit_wod_policy_decision(
            actor=actor,
            workout=workout,
            approval_policy=policy,
            submission_source=source,
            source_template=source_template,
            bypass_approval=False,
        )
        return {'status': 'pending_approval', 'policy': policy, 'bypass_approval': False, 'decision_label': 'Enviado para aprovacao'}

    now = timezone.now()
    workout.status = SessionWorkoutStatus.PUBLISHED
    workout.submitted_by = actor
    workout.submitted_at = workout.submitted_at or now
    workout.approved_by = actor
    workout.approved_at = now
    workout.save(
        update_fields=[
            'status',
            'submitted_by',
            'submitted_at',
            'approved_by',
            'approved_at',
            'rejected_by',
            'rejected_at',
            'rejection_reason',
            'updated_at',
        ]
    )
    decision_snapshot = {
        'approval_policy': policy,
        'submission_source': source,
        'source_template_id': source_template_id,
        'source_template_trusted': source_template_trusted,
        'bypass_approval': True,
        'policy_decision_label': 'Publicado direto pela politica',
    }
    create_workout_revision(
        workout=workout,
        actor=actor,
        event=SessionWorkoutRevisionEvent.PUBLISHED,
        extra_snapshot=decision_snapshot,
    )
    record_workout_audit(
        actor=actor,
        workout=workout,
        action='session_workout_published_directly',
        description='WOD publicado diretamente pela politica ativa.',
        metadata={
            'session_id': workout.session_id,
            'version': workout.version,
            **decision_snapshot,
        },
    )
    emit_wod_policy_decision(
        actor=actor,
        workout=workout,
        approval_policy=policy,
        submission_source=source,
        source_template=source_template,
        bypass_approval=True,
    )
    return {'status': 'published', 'policy': policy, 'bypass_approval': True, 'decision_label': 'Publicado direto pela politica'}


def extract_latest_policy_snapshot(workout, *, preferred_event=None):
    revisions = list(workout.revisions.all()) if hasattr(workout, 'revisions') else []
    if not revisions:
        return {}
    candidates = revisions
    if preferred_event is not None:
        filtered = [revision for revision in revisions if revision.event == preferred_event]
        if filtered:
            candidates = filtered
    latest = sorted(candidates, key=lambda revision: (revision.created_at, revision.id), reverse=True)[0]
    return latest.snapshot or {}


def build_policy_badge_from_snapshot(snapshot):
    if not snapshot:
        return None
    approval_policy = (snapshot.get('approval_policy') or '').strip()
    if not approval_policy:
        return None
    bypass_approval = bool(snapshot.get('bypass_approval'))
    source = (snapshot.get('submission_source') or '').strip()
    source_template_trusted = bool(snapshot.get('source_template_trusted'))
    policy_label_map = {
        'strict': 'Fila obrigatoria',
        'trusted_template': 'Trusted template',
        'coach_autonomy': 'Coach autonomy',
    }
    if bypass_approval and approval_policy == 'trusted_template' and source_template_trusted:
        detail = 'Publicado direto via template confiavel.'
        tone = 'success'
    elif bypass_approval and approval_policy == 'coach_autonomy':
        detail = 'Publicado direto pela autonomia do coach.'
        tone = 'accent'
    elif approval_policy == 'strict':
        detail = 'Politica exigiu passagem pela fila de aprovacao.'
        tone = 'warning'
    else:
        detail = 'Politica aplicada registrada no corredor.'
        tone = 'info'
    if source == 'template' and source_template_trusted and not bypass_approval:
        detail = 'Template confiavel usado, mas a politica ainda manteve revisao manual.'
    return {
        'label': policy_label_map.get(approval_policy, approval_policy),
        'detail': detail,
        'tone': tone,
        'bypass_approval': bypass_approval,
        'policy': approval_policy,
    }
