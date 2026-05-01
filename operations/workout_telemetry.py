"""
ARQUIVO: telemetria do corredor operacional de WOD.

POR QUE ELE EXISTE:
- evita que views de acao acumulem responsabilidade de medicao, logger e sampling.

O QUE ESTE ARQUIVO FAZ:
1. mede duracao de actions WOD.
2. respeita toggles de settings/env.
3. emite evento `wod_action_duration_ms` no logger dedicado.

PONTOS CRITICOS:
- nao deve conhecer regras de negocio do WOD.
- nao deve decidir redirect, mensagem ou permissao.
"""

import logging
import random
from contextlib import contextmanager
from time import perf_counter

from django.conf import settings
from django.db import OperationalError, ProgrammingError, transaction

from operations.models import WorkoutPlannerTemplatePickerEvent, SmartPlanGateEvent


logger = logging.getLogger('octobox.operations.wod')


def should_emit_wod_action_telemetry():
    if not getattr(settings, 'WOD_ACTION_TELEMETRY_ENABLED', True):
        return False
    sample_rate = max(0.0, min(1.0, getattr(settings, 'WOD_ACTION_TELEMETRY_SAMPLE_RATE', 1.0)))
    return sample_rate >= 1.0 or random.random() < sample_rate


def emit_wod_action_duration(*, request, action, workout_id, started_at):
    if not should_emit_wod_action_telemetry():
        return
    duration_ms = int((perf_counter() - started_at) * 1000)
    user = getattr(request, 'user', None)
    logger.info(
        'wod_action_duration_ms',
        extra={
            'action': action,
            'workout_id': workout_id,
            'user_id': getattr(user, 'id', None),
            'duration_ms': duration_ms,
        },
    )


def emit_wod_policy_decision(*, actor, workout, approval_policy, submission_source, source_template=None, bypass_approval=False):
    if not should_emit_wod_action_telemetry():
        return
    logger.info(
        'wod_policy_decision',
        extra={
            'policy': approval_policy,
            'submission_source': submission_source,
            'workout_id': getattr(workout, 'id', None),
            'session_id': getattr(workout, 'session_id', None),
            'user_id': getattr(actor, 'id', None),
            'template_id': getattr(source_template, 'id', None),
            'template_is_trusted': bool(getattr(source_template, 'is_trusted', False)),
            'bypass_approval': bool(bypass_approval),
        },
    )


def emit_wod_planner_picker_event(*, actor, event_name, session_id=None, template_id=None, action_outcome=''):
    if not should_emit_wod_action_telemetry():
        return
    session_pk = None
    template_pk = None
    try:
        session_pk = int(session_id) if session_id is not None else None
    except (TypeError, ValueError):
        session_pk = None
    try:
        template_pk = int(template_id) if template_id is not None else None
    except (TypeError, ValueError):
        template_pk = None
    if session_pk is not None:
        try:
            with transaction.atomic():
                WorkoutPlannerTemplatePickerEvent.objects.create(
                    event_name=event_name,
                    session_id=session_pk,
                    template_id=template_pk,
                    actor=actor,
                    action_outcome=action_outcome,
                )
        except (OperationalError, ProgrammingError):
            pass
    logger.info(
        'wod_planner_template_picker',
        extra={
            'event_name': event_name,
            'session_id': session_id,
            'template_id': template_id,
            'user_id': getattr(actor, 'id', None),
            'action_outcome': action_outcome,
        },
    )


def emit_smartplan_gate_event(
    *,
    actor,
    session_id,
    outcome,
    paste_length=None,
    block_count=None,
    invalid_reason='',
    prompt_version='v1.0.0',
):
    """Registra uma passagem pelo gating SmartPlan. Fire-and-forget — nunca bloqueia."""
    try:
        session_pk = int(session_id) if session_id is not None else None
    except (TypeError, ValueError):
        session_pk = None
    if session_pk is not None:
        try:
            with transaction.atomic():
                SmartPlanGateEvent.objects.create(
                    actor=actor,
                    session_id=session_pk,
                    outcome=outcome,
                    paste_length=paste_length,
                    block_count=block_count,
                    invalid_reason=invalid_reason or '',
                    prompt_version=prompt_version,
                )
        except (OperationalError, ProgrammingError):
            pass
    logger.info(
        'smartplan_gate',
        extra={
            'outcome': outcome,
            'session_id': session_id,
            'user_id': getattr(actor, 'id', None),
            'paste_length': paste_length,
            'block_count': block_count,
            'invalid_reason': invalid_reason,
            'prompt_version': prompt_version,
        },
    )


@contextmanager
def wod_action_timer(request, *, action, workout_id=None):
    started_at = perf_counter()
    try:
        yield
    finally:
        emit_wod_action_duration(
            request=request,
            action=action,
            workout_id=workout_id,
            started_at=started_at,
        )


__all__ = [
    'emit_smartplan_gate_event',
    'emit_wod_action_duration',
    'emit_wod_planner_picker_event',
    'emit_wod_policy_decision',
    'should_emit_wod_action_telemetry',
    'wod_action_timer',
]
