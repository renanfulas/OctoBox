from __future__ import annotations

from django.core import signing


STATE_SALT = 'student_identity.oauth_state'
STATE_MAX_AGE_SECONDS = 600


def build_oauth_state(*, provider: str, invite_token: str = '') -> str:
    return signing.dumps(
        {
            'provider': provider,
            'invite_token': (invite_token or '').strip(),
        },
        salt=STATE_SALT,
        compress=True,
    )


def read_oauth_state(raw_state: str):
    if not raw_state:
        return None
    try:
        return signing.loads(raw_state, salt=STATE_SALT, max_age=STATE_MAX_AGE_SECONDS)
    except signing.BadSignature:
        return None
