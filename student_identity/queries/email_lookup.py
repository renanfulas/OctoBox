"""Exact StudentIdentity email lookup with a reader-first blind-index gate."""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from shared_support.crypto_fields import generate_email_blind_index
from student_identity.models import StudentIdentity


def identities_for_email(email, *, queryset=None):
    """Return exact email matches, retaining legacy lookup until backfill is ready.

    After the operator verifies the complete public-schema backfill, the ready
    flag switches reads to the HMAC index. Candidate values are compared again
    in Python so the lookup remains exact even in the event of an HMAC collision.
    """

    normalized = (email or "").strip().casefold()
    if not normalized:
        return []

    candidates = queryset if queryset is not None else StudentIdentity.objects.all()

    if not getattr(settings, "STUDENT_IDENTITY_EMAIL_LOOKUP_INDEX_READY", False):
        return list(candidates.filter(email__iexact=email.strip()))

    if not getattr(settings, "EMAIL_BLIND_INDEX_KEY", ""):
        raise ImproperlyConfigured("Email lookup index is active without EMAIL_BLIND_INDEX_KEY.")

    lookup_index = generate_email_blind_index(normalized)
    indexed = candidates.filter(email_lookup_index=lookup_index)
    return [identity for identity in indexed if (identity.email or "").strip().casefold() == normalized]


__all__ = ["identities_for_email"]
