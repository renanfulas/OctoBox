"""
ARQUIVO: catalogo de templates rapidos de WOD.

POR QUE ELE EXISTE:
- abre reaproveitamento de treinos sem criar modelo novo persistente ainda.

O QUE ESTE ARQUIVO FAZ:
1. lista WODs publicados recentes como templates rapidos.
2. filtra o que faz sentido para o papel atual.
"""

from access.roles import ROLE_COACH
from student_app.models import SessionWorkout, SessionWorkoutStatus


def build_recent_published_workout_templates(*, current_session, current_role_slug, actor, limit=8):
    queryset = (
        SessionWorkout.objects.select_related('session', 'session__coach')
        .filter(status=SessionWorkoutStatus.PUBLISHED)
        .exclude(session_id=current_session.id)
        .order_by('-approved_at', '-updated_at')
    )
    if current_role_slug == ROLE_COACH:
        queryset = queryset.filter(session__coach=actor)

    templates = []
    for workout in queryset[:limit]:
        block_count = workout.blocks.count()
        movement_count = sum(block.movements.count() for block in workout.blocks.all())
        templates.append(
            {
                'id': workout.id,
                'label': f"{workout.title or workout.session.title} — {workout.session.scheduled_at:%d/%m %H:%M}",
                'coach_label': (
                    workout.session.coach.get_full_name() or workout.session.coach.username
                    if workout.session.coach
                    else 'Sem coach'
                ),
                'block_count': block_count,
                'movement_count': movement_count,
                'summary': f'{block_count} bloco(s) · {movement_count} movimento(s)',
            }
        )
    return tuple(templates)


__all__ = ['build_recent_published_workout_templates']
