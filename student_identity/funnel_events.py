from __future__ import annotations

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
    return AuditEvent.objects.create(
        actor=actor,
        actor_role=actor_role,
        action=build_student_onboarding_event_action(journey=journey, event=event),
        target_model=target_model,
        target_id=target_id,
        target_label=target_label,
        description=description,
        metadata=payload,
    )
