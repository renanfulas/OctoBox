from __future__ import annotations

import threading

from django.conf import settings
from django.db import transaction

from auditing.models import AuditEvent


def build_student_onboarding_event_action(*, journey: str, event: str) -> str:
    return f'student_onboarding.{journey}.{event}'


def record_student_onboarding_event(
    *,
    journey: str,
    event: str,
    target_model: str = '',
    target_id: str = '',
    target_label: str = '',
    description: str = '',
    actor=None,
    actor_role: str = '',
    metadata: dict | None = None,
):
    payload = {
        'journey': journey,
        **(metadata or {}),
    }
    kwargs = dict(
        actor=actor,
        actor_role=actor_role,
        action=build_student_onboarding_event_action(journey=journey, event=event),
        target_model=target_model,
        target_id=target_id,
        target_label=target_label,
        description=description,
        metadata=payload,
    )
    if getattr(settings, 'STUDENT_AUDIT_ASYNC', False):
        def _write():
            AuditEvent.objects.create(**kwargs)
        transaction.on_commit(lambda: threading.Thread(target=_write, daemon=True).start())
        return None
    return AuditEvent.objects.create(**kwargs)
