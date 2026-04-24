"""
ARQUIVO: duplicacao segura de WOD entre sessoes.

POR QUE ELE EXISTE:
- evita copiar a mesma rotina de clonagem em editor, planner e futuras actions.

O QUE ESTE ARQUIVO FAZ:
1. clona workout, blocos e movimentos para outra aula.
2. registra revisao e auditoria de duplicacao.

PONTOS CRITICOS:
- nao sobrescrever aula que ja possui WOD.
- sempre criar o WOD de destino como rascunho.
"""

from student_app.models import (
    SessionWorkout,
    SessionWorkoutBlock,
    SessionWorkoutMovement,
    SessionWorkoutRevisionEvent,
    SessionWorkoutStatus,
)

from .workout_support import create_workout_revision, record_workout_audit


def clone_workout_to_session(*, actor, source_workout, target_session):
    duplicated_workout = SessionWorkout.objects.create(
        session=target_session,
        title=source_workout.title,
        coach_notes=source_workout.coach_notes,
        status=SessionWorkoutStatus.DRAFT,
        created_by=actor,
        version=1,
    )
    for block in source_workout.blocks.all():
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
    create_workout_revision(
        workout=duplicated_workout,
        actor=actor,
        event=SessionWorkoutRevisionEvent.DUPLICATED,
        extra_snapshot={'source_workout_id': source_workout.id, 'source_session_id': source_workout.session_id},
    )
    record_workout_audit(
        actor=actor,
        workout=duplicated_workout,
        action='session_workout_duplicated',
        description='WOD duplicado para outra aula.',
        metadata={
            'session_id': duplicated_workout.session_id,
            'version': duplicated_workout.version,
            'source_workout_id': source_workout.id,
            'source_session_id': source_workout.session_id,
        },
    )
    return duplicated_workout


def apply_workout_template_to_session(*, actor, source_workout, target_session):
    target_workout = getattr(target_session, 'workout', None)
    if target_workout is not None and target_workout.blocks.exists():
        return {
            'ok': False,
            'reason': 'target_has_blocks',
            'target_block_count': target_workout.blocks.count(),
            'target_movement_count': sum(block.movements.count() for block in target_workout.blocks.all()),
        }

    created = False
    if target_workout is None:
        target_workout = SessionWorkout.objects.create(
            session=target_session,
            title=source_workout.title,
            coach_notes=source_workout.coach_notes,
            status=SessionWorkoutStatus.DRAFT,
            created_by=actor,
            version=1,
        )
        created = True
    else:
        target_workout.title = source_workout.title
        target_workout.coach_notes = source_workout.coach_notes
        target_workout.status = SessionWorkoutStatus.DRAFT
        target_workout.submitted_by = None
        target_workout.submitted_at = None
        target_workout.approved_by = None
        target_workout.approved_at = None
        target_workout.rejected_by = None
        target_workout.rejected_at = None
        target_workout.rejection_reason = ''
        target_workout.version += 1
        target_workout.save(
            update_fields=[
                'title',
                'coach_notes',
                'status',
                'submitted_by',
                'submitted_at',
                'approved_by',
                'approved_at',
                'rejected_by',
                'rejected_at',
                'rejection_reason',
                'version',
                'updated_at',
            ]
        )

    for block in source_workout.blocks.all():
        duplicated_block = SessionWorkoutBlock.objects.create(
            workout=target_workout,
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

    create_workout_revision(
        workout=target_workout,
        actor=actor,
        event=SessionWorkoutRevisionEvent.DUPLICATED,
        extra_snapshot={
            'source_workout_id': source_workout.id,
            'source_session_id': source_workout.session_id,
            'template_mode': 'quick_template',
        },
    )
    record_workout_audit(
        actor=actor,
        workout=target_workout,
        action='session_workout_template_applied',
        description='Template rapido de WOD aplicado na aula.',
        metadata={
            'session_id': target_workout.session_id,
            'version': target_workout.version,
            'source_workout_id': source_workout.id,
            'source_session_id': source_workout.session_id,
            'template_mode': 'quick_template',
            'created_workout': created,
        },
    )
    return {'ok': True, 'reason': 'applied', 'workout': target_workout}


__all__ = ['apply_workout_template_to_session', 'clone_workout_to_session']
