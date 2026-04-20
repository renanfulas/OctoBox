"""
ARQUIVO: actions do corredor de aprovacao do WOD.

POR QUE ELE EXISTE:
- separa da action view as mutacoes reais de aprovar ou rejeitar um WOD.

O QUE ESTE ARQUIVO FAZ:
1. publica workout aprovado com revisao e auditoria.
2. rejeita workout com motivo, revisao e auditoria.

PONTOS CRITICOS:
- manter side effects, revisoes e trilha de auditoria identicos ao fluxo anterior.
"""

from django.utils import timezone

from student_app.models import SessionWorkoutRevisionEvent, SessionWorkoutStatus

from .workout_support import create_workout_revision, record_workout_audit


def approve_workout(*, actor, workout, review_snapshot, approval_reason):
    workout.status = SessionWorkoutStatus.PUBLISHED
    workout.approved_by = actor
    workout.approved_at = timezone.now()
    workout.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
    create_workout_revision(
        workout=workout,
        actor=actor,
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
        actor=actor,
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
    return workout


def reject_workout(*, actor, workout, rejection_reason, rejection_category):
    workout.status = SessionWorkoutStatus.REJECTED
    workout.rejected_by = actor
    workout.rejected_at = timezone.now()
    workout.rejection_reason = rejection_reason
    workout.save(update_fields=['status', 'rejected_by', 'rejected_at', 'rejection_reason', 'updated_at'])
    create_workout_revision(
        workout=workout,
        actor=actor,
        event=SessionWorkoutRevisionEvent.REJECTED,
        extra_snapshot={
            'rejection_reason': rejection_reason,
            'rejection_category': rejection_category,
        },
    )
    record_workout_audit(
        actor=actor,
        workout=workout,
        action='session_workout_rejected',
        description='Owner ou manager rejeitou o WOD para ajuste.',
        metadata={
            'session_id': workout.session_id,
            'version': workout.version,
            'rejection_reason': rejection_reason,
            'rejection_category': rejection_category,
        },
    )
    return workout


__all__ = ['approve_workout', 'reject_workout']
