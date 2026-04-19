from __future__ import annotations

from typing import Any


STUDENT_ONBOARDING_SESSION_KEY = 'student_pending_onboarding'


def store_pending_student_onboarding(request, *, payload: dict[str, Any]) -> None:
    request.session[STUDENT_ONBOARDING_SESSION_KEY] = payload
    request.session.modified = True


def read_pending_student_onboarding(request) -> dict[str, Any] | None:
    payload = request.session.get(STUDENT_ONBOARDING_SESSION_KEY)
    return payload if isinstance(payload, dict) else None


def clear_pending_student_onboarding(request) -> None:
    if STUDENT_ONBOARDING_SESSION_KEY in request.session:
        del request.session[STUDENT_ONBOARDING_SESSION_KEY]
        request.session.modified = True
