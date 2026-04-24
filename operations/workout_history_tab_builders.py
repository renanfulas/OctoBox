"""
ARQUIVO: builders puros das superficies de historico do corredor de WOD.

POR QUE ELE EXISTE:
- separa as tres intencoes do historico sem prender a logica na borda HTTP.

O QUE ESTE ARQUIVO FAZ:
1. monta o contexto de publicados.
2. monta o contexto de checkpoint semanal.
3. monta o contexto de alertas e follow-ups.

PONTOS CRITICOS:
- manter este modulo sem request, redirect ou messages.
- preservar compatibilidade enquanto a UI ainda usa a surface monolitica.
"""

from operations.workout_board_weekly_builders import (
    build_weekly_checkpoint_maturity,
    build_weekly_checkpoint_rhythm,
    build_weekly_governance_action,
)
from student_app.models import (
    WorkoutWeeklyManagementCheckpoint,
    WorkoutWeeklyCheckpointOwner,
    WorkoutWeeklyCheckpointStatus,
    WorkoutWeeklyGovernanceCommitmentStatus,
)


def build_published_wods_context(
    *,
    coach_username='',
    session_id=None,
    today_only=False,
    published_reason='',
    current_role_slug='',
):
    from operations.workout_published_history import build_published_workout_history

    return {
        'published_history': build_published_workout_history(
            limit=12,
            coach_username=coach_username,
            session_id=session_id,
            today_only=today_only,
            published_reason=published_reason,
            current_role_slug=current_role_slug,
        ),
    }


def build_checkpoint_context(*, today):
    from operations.workout_support import build_weekly_checkpoint_history, week_start_for

    current_week_start = week_start_for(today)
    weekly_checkpoint = WorkoutWeeklyManagementCheckpoint.objects.filter(week_start=current_week_start).first()
    weekly_checkpoint_history = build_weekly_checkpoint_history()
    weekly_checkpoint_rhythm = build_weekly_checkpoint_rhythm(checkpoint_history=weekly_checkpoint_history)
    weekly_checkpoint_maturity = build_weekly_checkpoint_maturity(
        checkpoint_history=weekly_checkpoint_history,
        rhythm_cards=weekly_checkpoint_rhythm,
    )
    return {
        'weekly_checkpoint': weekly_checkpoint,
        'weekly_checkpoint_form_initial': {
            'execution_status': getattr(weekly_checkpoint, 'execution_status', WorkoutWeeklyCheckpointStatus.NOT_STARTED),
            'responsible_role': getattr(weekly_checkpoint, 'responsible_role', WorkoutWeeklyCheckpointOwner.MANAGER),
            'closure_status': getattr(weekly_checkpoint, 'closure_status', ''),
            'governance_commitment_status': getattr(
                weekly_checkpoint,
                'governance_commitment_status',
                WorkoutWeeklyGovernanceCommitmentStatus.NOT_ASSUMED,
            ),
            'governance_commitment_note': getattr(weekly_checkpoint, 'governance_commitment_note', ''),
            'summary_note': getattr(weekly_checkpoint, 'summary_note', ''),
        },
        'weekly_checkpoint_week_label': current_week_start.strftime('%d/%m/%Y'),
        'weekly_checkpoint_history': weekly_checkpoint_history,
        'weekly_checkpoint_rhythm': weekly_checkpoint_rhythm,
        'weekly_checkpoint_maturity': weekly_checkpoint_maturity,
        'weekly_governance_action': build_weekly_governance_action(maturity=weekly_checkpoint_maturity),
    }


def build_alerts_context(
    *,
    coach_username='',
    session_id=None,
    today_only=False,
    published_reason='',
    current_role_slug='',
    published_history=None,
):
    if published_history is None:
        from operations.workout_published_history import build_published_workout_history

        published_history = build_published_workout_history(
            limit=12,
            coach_username=coach_username,
            session_id=session_id,
            today_only=today_only,
            published_reason=published_reason,
            current_role_slug=current_role_slug,
        )
    return {
        'published_history': published_history,
    }


__all__ = [
    'build_alerts_context',
    'build_checkpoint_context',
    'build_published_wods_context',
]
