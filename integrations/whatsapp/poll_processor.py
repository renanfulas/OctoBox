"""Tenant-scoped, idempotent processing for authenticated WhatsApp poll votes."""

from __future__ import annotations

import re
from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context

from control.models import Box
from control.tenant_write_fence import TenantWritesFrozen, tenant_write_guard
from integrations.mesh import (
    classify_duplicate,
    classify_invalid_payload,
    classify_non_retryable,
    classify_retryable,
    decide_retry,
)
from operations.model_definitions import Attendance, AttendanceStatus, ClassSession
from shared_support.crypto_fields import generate_blind_index
from shared_support.phone_numbers import normalize_phone_number
from students.model_definitions import Student

from .contracts import WhatsAppInboundPollVote, WhatsAppWebhookProcessingResult
from .models import WhatsAppPollWebhookIntent


_SCHEMA_RE = re.compile(r'^box_[a-z0-9_-]{1,59}$')


def _lookup_student_by_phone(phone: str) -> tuple[Student | None, str]:
    """Resolve exactly one student using the stable index for encrypted phone."""

    phone_index = generate_blind_index(phone)
    if not phone_index:
        return None, 'phone-lookup-unavailable'

    candidates = list(Student.objects.filter(phone_lookup_index=phone_index).only('pk')[:2])
    if len(candidates) > 1:
        return None, 'ambiguous-student-phone'
    if not candidates:
        return None, 'student-not-found'
    return candidates[0], ''


def _parse_voted_hour(value: str) -> int | None:
    normalized = str(value or '').strip().lower()
    if normalized.endswith('h'):
        normalized = normalized[:-1].strip()
    elif normalized.endswith(':00'):
        normalized = normalized[:-3].strip()
    if not normalized.isdigit():
        return None
    hour = int(normalized)
    return hour if 0 <= hour <= 23 else None


def _result(
    *,
    accepted: bool,
    reason: str,
    failure_kind: str = '',
    retryable: bool = False,
    retry_action: str = '',
    attempts: int = 0,
    max_attempts: int = 0,
    next_retry_at=None,
) -> WhatsAppWebhookProcessingResult:
    return WhatsAppWebhookProcessingResult(
        accepted=accepted,
        reason=reason,
        failure_kind=failure_kind,
        retryable=retryable,
        retry_action=retry_action,
        attempt_number=attempts,
        max_attempts=max_attempts,
        next_retry_at=next_retry_at.isoformat() if next_retry_at else '',
    )


def _store_failure(intent, *, failure_kind: str, reason: str, now):
    decision = decide_retry(
        failure_kind=failure_kind,
        attempts=intent.attempts,
        max_attempts=intent.max_retries,
        reason=reason,
        now=now,
    )
    intent.attempts = decision.attempt_number
    intent.status = (
        WhatsAppPollWebhookIntent.Status.PENDING
        if decision.should_retry
        else WhatsAppPollWebhookIntent.Status.FAILED
    )
    intent.next_retry_at = decision.next_retry_at
    # Only stable, non-PII reason codes are persisted.
    intent.last_error_code = reason[:64]
    intent.save(update_fields=[
        'attempts', 'status', 'next_retry_at', 'last_error_code', 'updated_at',
    ])
    return decision


def _apply_vote(*, intent, poll_vote: WhatsAppInboundPollVote, now):
    student, lookup_failure = _lookup_student_by_phone(poll_vote.phone)
    if student is None:
        failure = classify_non_retryable(reason=lookup_failure or 'student-not-found')
        decision = _store_failure(intent, failure_kind=failure.kind, reason=failure.reason, now=now)
        return _result(
            accepted=False,
            reason=failure.reason,
            failure_kind=failure.kind,
            retry_action=decision.action,
            attempts=decision.attempt_number,
            max_attempts=decision.max_attempts,
        )

    hour_voted = _parse_voted_hour(poll_vote.option_voted)
    if hour_voted is None:
        failure = classify_invalid_payload(reason='invalid-poll-option')
        decision = _store_failure(intent, failure_kind=failure.kind, reason=failure.reason, now=now)
        return _result(
            accepted=False,
            reason=failure.reason,
            failure_kind=failure.kind,
            retry_action=decision.action,
            attempts=decision.attempt_number,
            max_attempts=decision.max_attempts,
        )

    local_today = timezone.localdate(now)
    start_time = timezone.make_aware(datetime.combine(local_today, time(hour=hour_voted)))
    end_time = start_time + timedelta(hours=1) - timedelta(microseconds=1)
    sessions = list(
        ClassSession.objects.filter(scheduled_at__range=(start_time, end_time))
        .order_by('scheduled_at', 'pk')[:2]
    )
    if len(sessions) != 1:
        reason = 'session-not-found' if not sessions else 'ambiguous-class-session'
        failure = classify_non_retryable(reason=reason)
        decision = _store_failure(intent, failure_kind=failure.kind, reason=failure.reason, now=now)
        return _result(
            accepted=False,
            reason=failure.reason,
            failure_kind=failure.kind,
            retry_action=decision.action,
            attempts=decision.attempt_number,
            max_attempts=decision.max_attempts,
        )

    _, created = Attendance.objects.update_or_create(
        student=student,
        session=sessions[0],
        defaults={
            'status': AttendanceStatus.CHECKED_IN,
            'check_in_at': now,
            'reservation_source': 'whatsapp_poll',
        },
    )
    intent.status = WhatsAppPollWebhookIntent.Status.PROCESSED
    intent.processed_at = now
    intent.next_retry_at = None
    intent.last_error_code = ''
    intent.save(update_fields=[
        'status', 'processed_at', 'next_retry_at', 'last_error_code', 'updated_at',
    ])
    return _result(
        accepted=True,
        reason='attendance-created' if created else 'attendance-checked-in',
    )


def process_poll_vote_webhook(
    *,
    poll_vote: WhatsAppInboundPollVote,
    tenant_schema: str,
    now=None,
) -> WhatsAppWebhookProcessingResult:
    """Persist and apply one verified vote inside its Box and write fence."""

    if not _SCHEMA_RE.fullmatch(tenant_schema or ''):
        failure = classify_invalid_payload(reason='invalid-tenant-route')
        return _result(
            accepted=False,
            reason=failure.reason,
            failure_kind=failure.kind,
            retry_action='give_up',
        )
    event_id = str(poll_vote.event_id or '').strip()
    if not event_id or len(event_id) > 255:
        failure = classify_invalid_payload(reason='invalid-event-envelope')
        return _result(
            accepted=False,
            reason=failure.reason,
            failure_kind=failure.kind,
            retry_action='give_up',
        )

    current_time = now or timezone.now()
    try:
        with tenant_write_guard(tenant_schema):
            with schema_context(get_public_schema_name()):
                active_box = Box.objects.filter(
                    schema_name=tenant_schema,
                    status=Box.Status.ACTIVE,
                ).exists()
            if not active_box:
                retry_at = current_time + timedelta(seconds=60)
                return _result(
                    accepted=False,
                    reason='box-not-active',
                    failure_kind='retryable',
                    retryable=True,
                    retry_action='retry',
                    next_retry_at=retry_at,
                )

            with schema_context(tenant_schema):
                with transaction.atomic():
                    intent, _ = WhatsAppPollWebhookIntent.objects.get_or_create(
                        provider='evolution',
                        event_id=event_id,
                        defaults={
                            'phone': poll_vote.phone,
                            'poll_title': poll_vote.poll_title,
                            'option_voted': poll_vote.option_voted,
                        },
                    )
                    intent = WhatsAppPollWebhookIntent.objects.select_for_update().get(pk=intent.pk)
                    if (
                        normalize_phone_number(intent.phone) != normalize_phone_number(poll_vote.phone)
                        or intent.poll_title != poll_vote.poll_title
                        or intent.option_voted != poll_vote.option_voted
                    ):
                        failure = classify_invalid_payload(reason='event-payload-conflict')
                        return _result(
                            accepted=False,
                            reason=failure.reason,
                            failure_kind=failure.kind,
                            retry_action='contain',
                        )
                    if intent.status == WhatsAppPollWebhookIntent.Status.PROCESSED:
                        duplicate = classify_duplicate(reason='duplicate-event')
                        decision = decide_retry(
                            failure_kind=duplicate.kind,
                            attempts=intent.attempts,
                            max_attempts=intent.max_retries,
                            reason=duplicate.reason,
                            now=current_time,
                        )
                        return _result(
                            accepted=True,
                            reason=duplicate.reason,
                            failure_kind=duplicate.kind,
                            retry_action=decision.action,
                            attempts=intent.attempts,
                            max_attempts=intent.max_retries,
                        )
                    if intent.status == WhatsAppPollWebhookIntent.Status.FAILED:
                        return _result(
                            accepted=False,
                            reason=intent.last_error_code or 'intent-failed',
                            failure_kind='non_retryable',
                            retry_action='give_up',
                            attempts=intent.attempts,
                            max_attempts=intent.max_retries,
                        )
                    if intent.next_retry_at and intent.next_retry_at > current_time:
                        return _result(
                            accepted=False,
                            reason=intent.last_error_code or 'retry-not-due',
                            failure_kind='retryable',
                            retryable=True,
                            retry_action='retry',
                            attempts=intent.attempts,
                            max_attempts=intent.max_retries,
                            next_retry_at=intent.next_retry_at,
                        )
                    return _apply_vote(intent=intent, poll_vote=poll_vote, now=current_time)
    except TenantWritesFrozen:
        retry_at = current_time + timedelta(seconds=60)
        return _result(
            accepted=False,
            reason='tenant-write-frozen',
            failure_kind='retryable',
            retryable=True,
            retry_action='retry',
            next_retry_at=retry_at,
        )
    except Exception as exc:  # noqa: BLE001 — persist a sanitized retry after transaction rollback
        reason = f'processor-{exc.__class__.__name__.lower()}'[:64]
        try:
            with tenant_write_guard(tenant_schema):
                with schema_context(tenant_schema):
                    with transaction.atomic():
                        intent = WhatsAppPollWebhookIntent.objects.select_for_update().filter(
                            provider='evolution', event_id=event_id,
                        ).first()
                        if intent is not None and intent.status != WhatsAppPollWebhookIntent.Status.PROCESSED:
                            decision = _store_failure(
                                intent,
                                failure_kind=classify_retryable(reason=reason).kind,
                                reason=reason,
                                now=current_time,
                            )
                            return _result(
                                accepted=False,
                                reason=reason,
                                failure_kind='retryable',
                                retryable=decision.should_retry,
                                retry_action=decision.action,
                                attempts=decision.attempt_number,
                                max_attempts=decision.max_attempts,
                                next_retry_at=decision.next_retry_at,
                            )
        except Exception:  # noqa: BLE001 — caller receives a retryable response if DB is unavailable
            pass
        return _result(
            accepted=False,
            reason='processor-temporary-failure',
            failure_kind='retryable',
            retryable=True,
            retry_action='retry',
            next_retry_at=current_time + timedelta(seconds=60),
        )


__all__ = ['_lookup_student_by_phone', 'process_poll_vote_webhook']
