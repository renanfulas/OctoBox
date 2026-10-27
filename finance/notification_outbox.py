"""Tenant-local transactional outbox for payment confirmations.

Enqueue in the payment reconciliation transaction. Delivery and network I/O
run later, outside that transaction, under a short-lived lease.
"""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from django.db import connection, transaction
from django.db.models import F
from django.utils import timezone

from finance.models import PaymentNotificationDelivery, PaymentNotificationDeliveryStatus, PaymentStatus

logger = logging.getLogger(__name__)

LEASE_SECONDS = 300
CONFIG_RECHECK_SECONDS = 3600
MAX_ATTEMPTS = 8


def enqueue_payment_confirmation(payment) -> int:
    """Create one durable row per eligible channel destination, idempotently.

    Call only inside the transaction that changes Payment to paid. Recipient
    keys are opaque internal IDs; contact data is resolved again at send time.
    """
    from student_identity.models import StudentPushSubscription
    from student_identity.box_scope import get_student_identity_box_scope

    event_key = f'payment-confirmed:v1:{payment.pk}'
    created_count = 0

    def create_delivery(*, channel, recipient_key, status, reason_code=''):
        nonlocal created_count
        _, created = PaymentNotificationDelivery.objects.get_or_create(
            logical_event_key=event_key,
            channel=channel,
            recipient_key=recipient_key,
            message_version=1,
            defaults={
                'payment': payment,
                'status': status,
                'reason_code': reason_code,
            },
        )
        created_count += int(created)
        if not created:
            # Keep a tenant-local, durable count of idempotent enqueue replays.
            # This is operational evidence only; it never changes send state.
            PaymentNotificationDelivery.objects.filter(
                logical_event_key=event_key,
                channel=channel,
                recipient_key=recipient_key,
                message_version=1,
            ).update(
                duplicate_suppressed_count=F('duplicate_suppressed_count') + 1,
                updated_at=timezone.now(),
            )

    student_key = f'student:{payment.student_id}'
    email = (getattr(payment.student, 'email', '') or '').strip()
    create_delivery(
        channel='email',
        recipient_key=student_key,
        status=(PaymentNotificationDeliveryStatus.PENDING if email else PaymentNotificationDeliveryStatus.SKIPPED),
        reason_code='' if email else 'email_recipient_missing',
    )

    box_scope = get_student_identity_box_scope()
    subscriptions = list(
        StudentPushSubscription.objects.filter(
            box_scope.predicate,
            identity__student_id=payment.student_id,
            revoked_at__isnull=True,
        ).values_list('pk', flat=True)
    )
    if subscriptions:
        for subscription_id in subscriptions:
            create_delivery(
                channel='push',
                recipient_key=f'push_subscription:{subscription_id}',
                status=PaymentNotificationDeliveryStatus.PENDING,
            )
    else:
        create_delivery(
            channel='push',
            recipient_key=student_key,
            status=PaymentNotificationDeliveryStatus.SKIPPED,
            reason_code='push_recipient_missing',
        )

    create_delivery(
        channel='whatsapp',
        recipient_key=student_key,
        status=PaymentNotificationDeliveryStatus.SKIPPED,
        reason_code='whatsapp_sender_not_implemented',
    )
    if PaymentNotificationDelivery.objects.filter(
        logical_event_key=event_key,
        status=PaymentNotificationDeliveryStatus.PENDING,
    ).exists():
        # Wakeup reduces latency; the tenant scanner remains the recovery path
        # if the process exits before this callback or its daemon thread runs.
        transaction.on_commit(_safe_wake_payment_notification_dispatcher)
    return created_count


def _safe_wake_payment_notification_dispatcher():
    try:
        from shared_support.background_jobs import run_in_background

        run_in_background(run_due_payment_notification_deliveries, limit=25)
    except Exception as exc:  # the committed outbox remains recoverable by the scanner
        logger.warning(
            'payment notification wakeup unavailable: exception=%s',
            type(exc).__name__,
        )


def claim_due_payment_notification_deliveries(*, limit=25, now=None):
    """Claim due rows; an expired lease becomes unknown to avoid duplicate sends."""
    now = now or timezone.now()
    lease_until = now + timedelta(seconds=LEASE_SECONDS)
    claims = []

    with transaction.atomic():
        PaymentNotificationDelivery.objects.filter(
            status=PaymentNotificationDeliveryStatus.LEASED,
            lease_expires_at__lte=now,
        ).update(
            status=PaymentNotificationDeliveryStatus.UNKNOWN,
            reason_code='lease_expired_delivery_unknown',
            lease_token=None,
            lease_expires_at=None,
            finished_at=now,
        )
        PaymentNotificationDelivery.objects.filter(
            status__in=(PaymentNotificationDeliveryStatus.PENDING, PaymentNotificationDeliveryStatus.RETRY_WAIT),
            attempt_count__gte=MAX_ATTEMPTS,
            available_at__lte=now,
        ).update(
            status=PaymentNotificationDeliveryStatus.FAILED,
            reason_code='retry_limit_exceeded',
            finished_at=now,
        )

        due = PaymentNotificationDelivery.objects.filter(
            status__in=(PaymentNotificationDeliveryStatus.PENDING, PaymentNotificationDeliveryStatus.RETRY_WAIT),
            available_at__lte=now,
        ).order_by('available_at', 'pk')
        if connection.features.has_select_for_update:
            lock_options = {'skip_locked': True} if connection.features.has_select_for_update_skip_locked else {}
            due = due.select_for_update(**lock_options)
        for delivery in due[:max(1, int(limit))]:
            token = uuid.uuid4()
            delivery.status = PaymentNotificationDeliveryStatus.LEASED
            delivery.lease_token = token
            delivery.lease_expires_at = lease_until
            delivery.last_attempt_at = now
            delivery.attempt_count += 1
            delivery.save(update_fields=[
                'status', 'lease_token', 'lease_expires_at', 'last_attempt_at',
                'attempt_count', 'updated_at',
            ])
            claims.append((delivery.pk, token))

    return claims


def dispatch_claimed_payment_notification_delivery(*, delivery_id, lease_token, now=None) -> str:
    """Send one claimed intent and finalize only if this worker still owns it."""
    now = now or timezone.now()
    from finance.models import Payment

    with transaction.atomic():
        delivery = PaymentNotificationDelivery.objects.select_for_update().filter(
            pk=delivery_id,
            status=PaymentNotificationDeliveryStatus.LEASED,
            lease_token=lease_token,
        ).first()
        if delivery is None:
            return 'lease_lost'

        if delivery.payment_id is None:
            _finish(delivery, status=PaymentNotificationDeliveryStatus.SKIPPED, reason='payment_missing', now=now)
            return PaymentNotificationDeliveryStatus.SKIPPED

        payment = Payment.objects.select_related('student').filter(pk=delivery.payment_id).first()
        if payment is None or payment.status != PaymentStatus.PAID:
            _finish(delivery, status=PaymentNotificationDeliveryStatus.SKIPPED, reason='payment_not_paid', now=now)
            return PaymentNotificationDeliveryStatus.SKIPPED

        channel = delivery.channel
        recipient_key = delivery.recipient_key

    if channel == 'email':
        email = (getattr(payment.student, 'email', '') or '').strip()
        if not email:
            return _finalize_claim(
                delivery_id, lease_token, status=PaymentNotificationDeliveryStatus.SKIPPED,
                reason='email_recipient_missing', now=now,
            )
        if not _email_is_configured():
            return _retry_for_configuration(delivery_id, lease_token, 'email_configuration_missing', now)
        return _send_email(delivery_id, lease_token, payment, email, now)

    if channel == 'push':
        if not _push_is_configured():
            return _retry_for_configuration(delivery_id, lease_token, 'push_configuration_missing', now)
        return _send_push(delivery_id, lease_token, payment, recipient_key, now)

    return _finalize_claim(
        delivery_id, lease_token, status=PaymentNotificationDeliveryStatus.SKIPPED,
        reason='channel_not_supported', now=now,
    )


def _email_is_configured() -> bool:
    from finance.notification_diagnostics import build_payment_notification_diagnostics

    channels = {item['key']: item for item in build_payment_notification_diagnostics()['channels']}
    return channels['email']['status'] == 'configured'


def _push_is_configured() -> bool:
    from student_identity.push_notifications import is_student_web_push_configured

    return is_student_web_push_configured()


def _send_email(delivery_id, lease_token, payment, email, now):
    from finance.payment_notifications import build_payment_confirmation_copy
    from signup.email_sender import send_html_email
    from shared_support.box_runtime import get_box_runtime_slug

    subject, text_body, html_body = build_payment_confirmation_copy(payment)
    try:
        result = send_html_email(
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            to_email=email,
            tags=[
                {'name': 'octobox_box', 'value': get_box_runtime_slug()},
                {'name': 'octobox_delivery', 'value': str(delivery_id)},
            ],
        )
    except Exception as exc:  # provider may have accepted before the connection failed
        logger.warning(
            'payment_notification_outcome_unknown channel=email exception=%s',
            type(exc).__name__,
        )
        return _finalize_claim(
            delivery_id, lease_token, status=PaymentNotificationDeliveryStatus.UNKNOWN,
            reason='email_outcome_unknown', now=now,
        )

    return _finalize_claim(
        delivery_id,
        lease_token,
        status=PaymentNotificationDeliveryStatus.PROVIDER_ACCEPTED,
        reason='',
        provider=getattr(result, 'provider', ''),
        provider_message_id=getattr(result, 'provider_message_id', '') or '',
        now=now,
    )


def _send_push(delivery_id, lease_token, payment, recipient_key, now):
    from student_identity.box_scope import get_student_identity_box_scope
    from student_identity.models import StudentPushSubscription
    from student_identity.push_messages.payment_confirmed import build_payment_confirmed_payload
    from student_identity.push_notifications import send_student_web_push_notification

    try:
        subscription_id = int(recipient_key.removeprefix('push_subscription:'))
    except (TypeError, ValueError):
        return _finalize_claim(
            delivery_id, lease_token, status=PaymentNotificationDeliveryStatus.FAILED,
            reason='push_recipient_key_invalid', now=now,
        )

    box_scope = get_student_identity_box_scope()
    subscription = StudentPushSubscription.objects.filter(
        box_scope.predicate,
        pk=subscription_id,
        identity__student_id=payment.student_id,
        revoked_at__isnull=True,
    ).first()
    if subscription is None:
        return _finalize_claim(
            delivery_id, lease_token, status=PaymentNotificationDeliveryStatus.SKIPPED,
            reason='push_subscription_unavailable', now=now,
        )

    payload = build_payment_confirmed_payload(payment_id=payment.id, amount=payment.amount)
    try:
        accepted = send_student_web_push_notification(
            subscription=subscription,
            title=payload.title,
            body=payload.body,
            url=payload.url,
            tag=payload.tag,
        )
    except Exception as exc:
        logger.warning(
            'payment_notification_outcome_unknown channel=push exception=%s',
            type(exc).__name__,
        )
        accepted = False

    if not accepted:
        # The sender hides provider response details. Retrying could duplicate a
        # notification after an ambiguous timeout, so require reconciliation.
        return _finalize_claim(
            delivery_id, lease_token, status=PaymentNotificationDeliveryStatus.UNKNOWN,
            reason='push_outcome_unknown', now=now,
        )
    return _finalize_claim(
        delivery_id, lease_token, status=PaymentNotificationDeliveryStatus.PROVIDER_ACCEPTED,
        reason='', provider='web_push', now=now,
    )


def _retry_for_configuration(delivery_id, lease_token, reason, now):
    delivery = PaymentNotificationDelivery.objects.filter(
        pk=delivery_id,
        status=PaymentNotificationDeliveryStatus.LEASED,
        lease_token=lease_token,
    ).first()
    if delivery is None:
        return 'lease_lost'
    if delivery.attempt_count >= MAX_ATTEMPTS:
        status = PaymentNotificationDeliveryStatus.FAILED
        reason = 'retry_limit_exceeded'
        finished_at = now
    else:
        status = PaymentNotificationDeliveryStatus.RETRY_WAIT
        finished_at = None
    updated = PaymentNotificationDelivery.objects.filter(
        pk=delivery_id,
        status=PaymentNotificationDeliveryStatus.LEASED,
        lease_token=lease_token,
    ).update(
        status=status,
        reason_code=reason,
        available_at=now + timedelta(seconds=CONFIG_RECHECK_SECONDS),
        lease_token=None,
        lease_expires_at=None,
        finished_at=finished_at,
        updated_at=now,
    )
    return status if updated else 'lease_lost'


def _finalize_claim(
    delivery_id,
    lease_token,
    *,
    status,
    reason,
    provider='',
    provider_message_id='',
    now,
):
    values = {
        'status': status,
        'reason_code': reason,
        'provider': provider,
        'provider_message_id': provider_message_id[:180],
        'lease_token': None,
        'lease_expires_at': None,
        'updated_at': now,
    }
    if status in {
        PaymentNotificationDeliveryStatus.SKIPPED,
        PaymentNotificationDeliveryStatus.FAILED,
        PaymentNotificationDeliveryStatus.UNKNOWN,
    }:
        values['finished_at'] = now
    if status == PaymentNotificationDeliveryStatus.PROVIDER_ACCEPTED:
        values['provider_accepted_at'] = now
    if status == PaymentNotificationDeliveryStatus.DELIVERED:
        values['delivered_at'] = now
    updated = PaymentNotificationDelivery.objects.filter(
        pk=delivery_id,
        status=PaymentNotificationDeliveryStatus.LEASED,
        lease_token=lease_token,
    ).update(**values)
    return status if updated else 'lease_lost'


def _finish(delivery, *, status, reason, now):
    delivery.status = status
    delivery.reason_code = reason
    delivery.finished_at = now
    delivery.lease_token = None
    delivery.lease_expires_at = None
    delivery.save(update_fields=[
        'status', 'reason_code', 'finished_at', 'lease_token', 'lease_expires_at', 'updated_at',
    ])


def run_due_payment_notification_deliveries(*, limit=25, now=None) -> dict[str, int]:
    """Claim and execute one bounded batch inside the current tenant schema."""
    now = now or timezone.now()
    claims = claim_due_payment_notification_deliveries(limit=limit, now=now)
    counts = {'claimed': len(claims), 'provider_accepted': 0, 'retry_wait': 0, 'unknown': 0, 'skipped': 0, 'failed': 0}
    for delivery_id, lease_token in claims:
        status = dispatch_claimed_payment_notification_delivery(
            delivery_id=delivery_id,
            lease_token=lease_token,
            now=now,
        )
        if status in counts:
            counts[status] += 1
    return counts


__all__ = [
    'claim_due_payment_notification_deliveries',
    'dispatch_claimed_payment_notification_delivery',
    'enqueue_payment_confirmation',
    'run_due_payment_notification_deliveries',
]
