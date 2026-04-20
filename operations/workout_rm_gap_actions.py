"""
ARQUIVO: mutacao do corredor operacional de gap de RM.

POR QUE ELE EXISTE:
- separa a escrita final do gap de RM da action view.

O QUE ESTE ARQUIVO FAZ:
1. salva ou atualiza a acao de gap de RM.
2. registra auditoria operacional do corredor.

PONTOS CRITICOS:
- manter side effects, metadata e mensagem final identicos ao fluxo anterior.
"""

from auditing import log_audit_event
from student_app.models import SessionWorkoutRmGapAction


def save_workout_rm_gap_action(*, actor, workout, attendance, payload):
    action, _ = SessionWorkoutRmGapAction.objects.update_or_create(
        workout=workout,
        student=attendance.student,
        exercise_slug=payload['exercise_slug'],
        defaults={
            'exercise_label': payload['exercise_label'],
            'status': payload['status'],
            'note': payload['note'],
            'updated_by': actor,
        },
    )
    log_audit_event(
        actor=actor,
        action='session_workout_rm_gap_action_saved',
        target=action,
        description='Owner ou manager atualizou o corredor operacional de RM do WOD publicado.',
        metadata={
            'session_id': workout.session_id,
            'workout_id': workout.id,
            'student_id': attendance.student_id,
            'student_name': attendance.student.full_name,
            'exercise_slug': action.exercise_slug,
            'exercise_label': action.exercise_label,
            'status': action.status,
            'status_label': action.get_status_display(),
            'note': action.note,
        },
    )
    return action


__all__ = ['save_workout_rm_gap_action']
