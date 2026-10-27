"""Aplica templates por data, modalidade e permissão, com estado reversível."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, get_user_role
from operations.models import ClassSession, ClassType, SessionStatus, WorkoutTemplate
from operations.workout_templates import apply_persisted_workout_template
from student_app.models import SessionWorkout, SessionWorkoutStatus

from .wod_day_apply_state import undo_cache_key, workout_state

_UNDO_TTL = 60
logger = logging.getLogger(__name__)


@dataclass
class DayApplyResult:
    applied_count: int
    skipped_count: int
    undo_token: str
    applied_session_ids: list[int] = field(default_factory=list)
    skipped_reasons: list[dict] = field(default_factory=list)


@transaction.atomic
def execute_day_apply(*, actor, target_date: date, template_id: int, class_type: str, mode: str) -> DayApplyResult:
    role = get_user_role(actor)
    if role is None or role.slug not in {ROLE_COACH, ROLE_MANAGER, ROLE_OWNER}:
        raise PermissionDenied('Sem permissão para aplicar WODs.')
    if class_type not in ClassType.values or mode not in {'replace_empty', 'overwrite'}:
        raise ValidationError('Escolha a modalidade e o modo de aplicação.')

    template = WorkoutTemplate.objects.select_for_update().filter(
        id=template_id, is_active=True, archived_at__isnull=True,
    ).first()
    if template is None:
        raise ValidationError('Template não encontrado ou arquivado.')
    if role.slug == ROLE_COACH and template.created_by_id != actor.pk:
        raise PermissionDenied('Use um template criado por você.')

    range_start = timezone.make_aware(datetime.combine(target_date, time.min))
    sessions = ClassSession.objects.select_for_update().filter(
        scheduled_at__gte=range_start,
        scheduled_at__lt=range_start + timedelta(days=1),
        class_type=class_type,
        status__in=(SessionStatus.SCHEDULED, SessionStatus.OPEN, SessionStatus.COMPLETED),
    ).order_by('id')
    if role.slug == ROLE_COACH:
        sessions = sessions.filter(coach=actor)
    sessions = list(sessions)
    workouts = {
        workout.session_id: workout for workout in SessionWorkout.objects.select_for_update().filter(
            session_id__in=[session.id for session in sessions],
        )
    }
    return apply_template_to_locked_sessions(actor=actor, template=template, sessions=sessions, workouts=workouts, mode=mode)


def apply_template_to_locked_sessions(*, actor, template, sessions, workouts, mode,
                                      skip_completed=False, defer_undo_cache=False,
                                      on_undo_unavailable=None) -> DayApplyResult:
    """Shared write path; caller owns the transaction and ordered row locks."""
    changes = []
    skipped = []
    for session in sessions:
        if skip_completed and session.status == SessionStatus.COMPLETED:
            skipped.append({'session_id': session.id, 'reason': 'Aula concluída preservada.', 'code': 'skipped_completed'})
            continue
        if session.status == SessionStatus.CANCELED:
            skipped.append({'session_id': session.id, 'reason': 'Aula cancelada preservada.', 'code': 'skipped_canceled'})
            continue
        workout = workouts.get(session.id)
        if workout is not None:
            if mode == 'replace_empty' or workout.status != SessionWorkoutStatus.DRAFT:
                skipped.append({'session_id': session.id, 'reason': 'WOD existente preservado; substituição permite apenas rascunhos.'})
                continue
            session.workout = workout
        before = workout_state(workout)
        if workout is not None:
            workout.blocks.all().delete()
        result = apply_persisted_workout_template(actor=actor, template=template, target_session=session)
        if not result.get('ok'):
            # Falhar reverte o lote inteiro, inclusive qualquer limpeza anterior.
            raise ValidationError('Não foi possível aplicar o template. Nenhuma aula foi alterada.')
        applied = result['workout']
        applied.refresh_from_db()
        changes.append({'session_id': session.id, 'before': before, 'after': workout_state(applied)})

    token = str(uuid.uuid4()) if changes else ''
    if changes:
        if defer_undo_cache:
            def save_undo():
                try:
                    stored = cache.set(undo_cache_key(actor, token), {'changes': changes}, timeout=_UNDO_TTL)
                    if stored is False:
                        raise RuntimeError('cache backend recusou o payload de undo')
                except Exception as exc:
                    logger.error('daily_wod_undo_cache_write_failed error_type=%s', type(exc).__name__)
                    if on_undo_unavailable is not None:
                        try:
                            on_undo_unavailable()
                        except Exception as callback_exc:
                            logger.error(
                                'daily_wod_undo_unavailable_callback_failed error_type=%s',
                                type(callback_exc).__name__,
                            )
            transaction.on_commit(save_undo)
        else:
            cache.set(undo_cache_key(actor, token), {'changes': changes}, timeout=_UNDO_TTL)
    return DayApplyResult(
        applied_count=len(changes), skipped_count=len(skipped), undo_token=token,
        applied_session_ids=[change['session_id'] for change in changes], skipped_reasons=skipped,
    )


__all__ = ['DayApplyResult', 'execute_day_apply', 'apply_template_to_locked_sessions']
