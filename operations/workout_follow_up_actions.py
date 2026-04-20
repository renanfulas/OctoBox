"""
ARQUIVO: actions do corredor de follow-up pos-publicacao do WOD.

POR QUE ELE EXISTE:
- separa da action view a persistencia do resultado operacional sugerido.

O QUE ESTE ARQUIVO FAZ:
1. cria ou atualiza follow-up action.
2. registra auditoria com baseline e resultado.

PONTOS CRITICOS:
- manter baseline, upsert e metadata de auditoria identicos ao fluxo anterior.
"""

from django.utils import timezone

from student_app.models import SessionWorkoutFollowUpAction

from .workout_support import record_workout_audit


def save_workout_follow_up_action(*, actor, workout, payload, baseline_metrics):
    follow_up_action, created = SessionWorkoutFollowUpAction.objects.get_or_create(
        workout=workout,
        action_key=payload['action_key'],
        defaults={
            'action_label': payload['action_label'],
            'status': payload['status'],
            'outcome_note': payload['outcome_note'],
            'baseline_metrics': baseline_metrics,
            'resolved_by': actor,
            'resolved_at': timezone.now(),
        },
    )
    if not created:
        follow_up_action.action_label = payload['action_label']
        follow_up_action.status = payload['status']
        follow_up_action.outcome_note = payload['outcome_note']
        if not follow_up_action.baseline_metrics:
            follow_up_action.baseline_metrics = baseline_metrics
        follow_up_action.resolved_by = actor
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
        actor=actor,
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
    return follow_up_action


__all__ = ['save_workout_follow_up_action']
