"""Reader-first exact email lookup for shared Public Workouts commerce rows."""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, transaction

from public_workouts.models import (
    PublicWorkoutCheckoutLead,
    PublicWorkoutWaitlistEntry,
    PublicWorkoutWaitlistStatus,
)
from shared_support.crypto_fields import (
    generate_public_workout_checkout_lead_email_blind_index,
    generate_public_workout_waitlist_email_blind_index,
)


def _matches_email(rows, email):
    normalized = (email or "").strip().casefold()
    return [row for row in rows if (row.email or "").strip().casefold() == normalized]


def checkout_leads_for_email(email, *, queryset=None):
    """Return case-insensitive exact matches through the active reader path."""
    normalized = (email or "").strip().casefold()
    if not normalized:
        return []
    candidates = queryset if queryset is not None else PublicWorkoutCheckoutLead.objects.all()
    if not getattr(settings, "PUBLIC_WORKOUT_CHECKOUT_LEAD_EMAIL_LOOKUP_INDEX_READY", False):
        return list(candidates.filter(email__iexact=(email or "").strip()))
    if not getattr(settings, "EMAIL_BLIND_INDEX_KEY", ""):
        raise ImproperlyConfigured("Checkout lead email index is active without EMAIL_BLIND_INDEX_KEY.")
    digest = generate_public_workout_checkout_lead_email_blind_index(normalized)
    return _matches_email(candidates.filter(email_lookup_index=digest), normalized)


def waitlist_entries_for_email(email, *, queryset=None):
    """Return case-insensitive exact matches through the active reader path."""
    normalized = (email or "").strip().casefold()
    if not normalized:
        return []
    candidates = queryset if queryset is not None else PublicWorkoutWaitlistEntry.objects.all()
    if not getattr(settings, "PUBLIC_WORKOUT_WAITLIST_EMAIL_LOOKUP_INDEX_READY", False):
        return list(candidates.filter(email__iexact=(email or "").strip()))
    if not getattr(settings, "EMAIL_BLIND_INDEX_KEY", ""):
        raise ImproperlyConfigured("Waitlist email index is active without EMAIL_BLIND_INDEX_KEY.")
    digest = generate_public_workout_waitlist_email_blind_index(normalized)
    return _matches_email(candidates.filter(email_lookup_index=digest), normalized)


def get_or_create_checkout_lead(*, email, defaults=None):
    """Resolve or create the single unpaid lead while retaining DB uniqueness."""
    normalized = (email or "").strip().lower()
    if not normalized:
        raise ValueError("Checkout lead email is required.")
    candidates = PublicWorkoutCheckoutLead.objects.filter(paid_at__isnull=True)
    matches = checkout_leads_for_email(normalized, queryset=candidates)
    if matches:
        return matches[0], False
    try:
        with transaction.atomic():
            lead = PublicWorkoutCheckoutLead.objects.create(email=normalized, **(defaults or {}))
    except IntegrityError:
        matches = checkout_leads_for_email(normalized, queryset=candidates)
        if not matches:
            raise
        return matches[0], False
    return lead, True


def get_or_create_waiting_waitlist_entry(*, email, tier, defaults=None):
    """Resolve or create a waiting entry; partial unique constraint backs races."""
    normalized = (email or "").strip().lower()
    if not normalized:
        raise ValueError("Waitlist email is required.")
    candidates = PublicWorkoutWaitlistEntry.objects.filter(
        tier=tier, status=PublicWorkoutWaitlistStatus.WAITING,
    )
    matches = waitlist_entries_for_email(normalized, queryset=candidates)
    if matches:
        return matches[0], False
    try:
        with transaction.atomic():
            entry = PublicWorkoutWaitlistEntry.objects.create(
                email=normalized,
                tier=tier,
                status=PublicWorkoutWaitlistStatus.WAITING,
                **(defaults or {}),
            )
    except IntegrityError:
        matches = waitlist_entries_for_email(normalized, queryset=candidates)
        if not matches:
            raise
        return matches[0], False
    return entry, True


__all__ = [
    "checkout_leads_for_email",
    "get_or_create_checkout_lead",
    "get_or_create_waiting_waitlist_entry",
    "waitlist_entries_for_email",
]
