"""Reader-first exact email lookup for shared PendingSignup records."""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from shared_support.crypto_fields import generate_pending_signup_email_blind_index

from .models import PendingSignup


def _matches_email(rows, normalized):
    return [
        row for row in rows
        if (row.email or '').strip().casefold() == normalized
    ]


def pending_signups_for_email(email, *, queryset=None):
    """Return every exact casefold email match; repeat signups are intentional."""
    normalized = (email or '').strip().casefold()
    if not normalized:
        return []
    candidates = queryset if queryset is not None else PendingSignup.objects.all()
    if not getattr(settings, 'PENDING_SIGNUP_EMAIL_LOOKUP_INDEX_READY', False):
        return _matches_email(
            candidates.filter(email__iexact=(email or '').strip()),
            normalized,
        )
    if not getattr(settings, 'EMAIL_BLIND_INDEX_KEY', ''):
        raise ImproperlyConfigured(
            'PendingSignup email lookup index is active without EMAIL_BLIND_INDEX_KEY.'
        )
    digest = generate_pending_signup_email_blind_index(normalized)
    return _matches_email(candidates.filter(email_lookup_index=digest), normalized)


__all__ = ['pending_signups_for_email']
