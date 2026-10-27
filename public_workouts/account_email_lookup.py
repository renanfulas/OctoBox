"""Reader-first exact email lookup for public workout accounts."""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, transaction

from public_workouts.models import PublicWorkoutAccount
from shared_support.crypto_fields import generate_public_workout_account_email_blind_index


def public_workout_accounts_for_email(email, *, queryset=None):
    """Return exact normalized matches via plaintext or the verified HMAC index."""

    normalized = (email or "").strip().casefold()
    if not normalized:
        return []

    candidates = queryset if queryset is not None else PublicWorkoutAccount.objects.all()
    if not getattr(settings, "PUBLIC_WORKOUT_ACCOUNT_EMAIL_LOOKUP_INDEX_READY", False):
        return list(candidates.filter(email__iexact=(email or "").strip()))

    if not getattr(settings, "EMAIL_BLIND_INDEX_KEY", ""):
        raise ImproperlyConfigured(
            "Public workout account email index is active without EMAIL_BLIND_INDEX_KEY."
        )

    lookup_index = generate_public_workout_account_email_blind_index(normalized)
    indexed = candidates.filter(email_lookup_index=lookup_index)
    return [
        account for account in indexed
        if (account.email or "").strip().casefold() == normalized
    ]


def get_or_create_public_workout_account(*, email, defaults=None):
    """Resolve an account by normalized email and safely create it if missing.

    The existing database uniqueness on plaintext email remains the concurrency
    backstop during the reader-first phase. Case variants are reconciled by the
    normalized lookup before attempting creation.
    """

    normalized = (email or "").strip().lower()
    if not normalized:
        raise ValueError("Public workout account email is required.")

    matches = public_workout_accounts_for_email(normalized)
    if matches:
        return matches[0], False

    try:
        with transaction.atomic():
            account = PublicWorkoutAccount.objects.create(
                email=normalized,
                **(defaults or {}),
            )
    except IntegrityError:
        # A concurrent normalized-email insert may have won. Re-read only
        # through the configured compatibility/indexed path after rollback.
        matches = public_workout_accounts_for_email(normalized)
        if not matches:
            raise
        return matches[0], False
    return account, True


__all__ = ["get_or_create_public_workout_account", "public_workout_accounts_for_email"]
