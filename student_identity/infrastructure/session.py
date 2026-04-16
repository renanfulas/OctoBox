from __future__ import annotations

from django.conf import settings
from django.core import signing


SESSION_SALT = 'student_identity.session'


def get_student_session_cookie_name() -> str:
    return getattr(settings, 'STUDENT_APP_SESSION_COOKIE_NAME', 'octobox_student_session')


def get_student_session_max_age() -> int:
    return int(getattr(settings, 'STUDENT_APP_SESSION_COOKIE_AGE', 604800))


def build_student_session_value(*, identity_id: int, box_root_slug: str) -> str:
    return signing.dumps(
        {'identity_id': int(identity_id), 'box_root_slug': box_root_slug},
        salt=SESSION_SALT,
        compress=True,
    )


def read_student_session_value(raw_value: str | None):
    if not raw_value:
        return None
    try:
        return signing.loads(
            raw_value,
            salt=SESSION_SALT,
            max_age=get_student_session_max_age(),
        )
    except signing.BadSignature:
        return None


def attach_student_session_cookie(response, *, identity_id: int, box_root_slug: str):
    response.set_cookie(
        get_student_session_cookie_name(),
        build_student_session_value(identity_id=identity_id, box_root_slug=box_root_slug),
        max_age=get_student_session_max_age(),
        httponly=True,
        secure=bool(getattr(settings, 'SESSION_COOKIE_SECURE', False)),
        samesite='Lax',
        path='/aluno/',
    )
    return response


def clear_student_session_cookie(response):
    response.delete_cookie(
        get_student_session_cookie_name(),
        path='/aluno/',
        samesite='Lax',
    )
    return response
