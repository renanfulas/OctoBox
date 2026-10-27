"""Reader-first exact email lookup for StudentAppInvitation operations."""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from shared_support.crypto_fields import generate_student_app_invitation_email_blind_index

from student_identity.models import StudentAppInvitation


def invitations_for_email(email, *, queryset=None):
    """Resolve exact normalized email matches through legacy or HMAC lookup."""
    normalized = (email or '').strip().casefold()
    if not normalized:
        return []
    candidates = queryset if queryset is not None else StudentAppInvitation.objects.all()
    if not getattr(settings, 'STUDENT_APP_INVITATION_EMAIL_LOOKUP_INDEX_READY', False):
        return list(candidates.filter(invited_email__iexact=(email or '').strip()))
    if not getattr(settings, 'EMAIL_BLIND_INDEX_KEY', ''):
        raise ImproperlyConfigured(
            'Student invitation email index is active without EMAIL_BLIND_INDEX_KEY.'
        )
    digest = generate_student_app_invitation_email_blind_index(normalized)
    return [
        invitation for invitation in candidates.filter(email_lookup_index=digest)
        if (invitation.invited_email or '').strip().casefold() == normalized
    ]


__all__ = ['invitations_for_email']
