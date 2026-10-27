"""Verified, tenant-aware delivery receipts for Resend payment emails."""

from __future__ import annotations

import json
import re

from django.conf import settings
from django.db import transaction
from django.db.models import Case, IntegerField, When
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django_tenants.utils import get_public_schema_name, schema_context

from finance.models import (
    PaymentNotificationDelivery,
    PaymentNotificationDeliveryEvent,
    PaymentNotificationDeliveryStatus,
)
from student_identity.resend_webhooks import (
    ResendWebhookHeaders,
    ResendWebhookVerificationError,
    verify_resend_webhook_signature,
)


_SCHEMA_RE = re.compile(r'^box_[a-z0-9_-]{1,59}$')
_DELIVERY_ID_RE = re.compile(r'^[1-9][0-9]{0,18}$')
_PAYMENT_EMAIL_EVENTS = {
    'email.sent',
    'email.delivered',
    'email.delivery_delayed',
    'email.bounced',
    'email.complained',
    'email.suppressed',
    'email.failed',
}
_EVENT_PRIORITY = {
    'email.complained': 0,
    'email.sent': 1,
    'email.delivery_delayed': 2,
    'email.bounced': 3,
    'email.suppressed': 3,
    'email.failed': 3,
    'email.delivered': 4,
}
_FAILURE_REASON = {
    'email.bounced': 'resend_email_bounced',
    'email.suppressed': 'resend_email_suppressed',
    'email.failed': 'resend_email_failed',
}


class ResendPaymentWebhookTenantUnresolved(RuntimeError):
    """A signed provider event cannot be attributed to a live tenant safely."""


class ResendPaymentWebhookConflict(RuntimeError):
    """A signed event conflicts with an already-correlated delivery."""


def _event_tags(data: dict) -> dict[str, str]:
    raw_tags = data.get('tags') or {}
    if isinstance(raw_tags, list):
        raw_tags = {
            item.get('name'): item.get('value')
            for item in raw_tags
            if isinstance(item, dict)
        }
    if not isinstance(raw_tags, dict):
        return {}
    return {str(key): str(value) for key, value in raw_tags.items() if value is not None}


def _resolve_active_schema(schema_name: str):
    from control.models import Box

    if not _SCHEMA_RE.fullmatch(schema_name or ''):
        raise ResendPaymentWebhookTenantUnresolved('tenant-tag-invalid')
    with schema_context(get_public_schema_name()):
        box = Box.objects.filter(schema_name=schema_name, status=Box.Status.ACTIVE).only('schema_name').first()
    if box is None:
        raise ResendPaymentWebhookTenantUnresolved('tenant-not-active')
    return box.schema_name


def _event_time(body: dict):
    value = body.get('created_at')
    try:
        occurred_at = parse_datetime(value) if isinstance(value, str) else None
    except ValueError as exc:
        # ISO-shaped input may still contain an impossible date/time/offset.
        raise ResendWebhookVerificationError('event-created-at-invalid') from exc
    if occurred_at is None:
        raise ResendWebhookVerificationError('event-created-at-invalid')
    if timezone.is_naive(occurred_at):
        raise ResendWebhookVerificationError('event-created-at-naive')
    return occurred_at


def _apply_event(*, schema_name, delivery_id, event_id, provider_message_id, event_type, occurred_at):
    from control.tenant_write_fence import tenant_write_guard

    # Commit the receipt before releasing the tenant fence, so a freeze cannot
    # complete while this signed provider event is still uncommitted.
    with tenant_write_guard(schema_name):
        with transaction.atomic():
            with schema_context(schema_name):
                return _apply_event_in_schema(
                    delivery_id=delivery_id,
                    event_id=event_id,
                    provider_message_id=provider_message_id,
                    event_type=event_type,
                    occurred_at=occurred_at,
                )


def _apply_event_in_schema(*, delivery_id, event_id, provider_message_id, event_type, occurred_at):
    delivery = PaymentNotificationDelivery.objects.select_for_update().filter(
        pk=delivery_id,
        channel='email',
    ).first()
    if delivery is None:
        return {'accepted': True, 'reason': 'delivery-not-found', 'event_type': event_type}

    existing_event = PaymentNotificationDeliveryEvent.objects.filter(
        provider_event_id=event_id,
    ).first()
    if existing_event is not None:
        if existing_event.delivery_id != delivery.pk:
            raise ResendPaymentWebhookConflict('provider-event-id-collision')
        return {'accepted': True, 'reason': 'duplicate-event', 'event_type': event_type}

    if delivery.provider not in ('', 'resend'):
        raise ResendPaymentWebhookConflict('delivery-provider-mismatch')
    if delivery.provider_message_id and delivery.provider_message_id != provider_message_id:
        raise ResendPaymentWebhookConflict('provider-message-id-mismatch')

    event = PaymentNotificationDeliveryEvent.objects.create(
        delivery=delivery,
        provider_event_id=event_id,
        provider='resend',
        event_type=event_type,
        occurred_at=occurred_at,
    )
    # Eventos informativos não avançam a ordenação do estado de entrega.
    # Em empate, preserve a maior prioridade já observada, independentemente
    # da ordem em que recibos atrasados foram inseridos.
    latest_event = delivery.provider_events.exclude(pk=event.pk).exclude(
        event_type='email.complained',
    ).annotate(state_priority=Case(
        *(When(event_type=kind, then=priority) for kind, priority in _EVENT_PRIORITY.items()),
        default=-1, output_field=IntegerField(),
    )).order_by('-occurred_at', '-state_priority', '-pk').first()
    delivery.provider = 'resend'
    delivery.provider_message_id = provider_message_id[:180]

    is_newer = latest_event is None or occurred_at > latest_event.occurred_at
    if latest_event is not None and occurred_at == latest_event.occurred_at:
        is_newer = _EVENT_PRIORITY[event_type] > _EVENT_PRIORITY.get(latest_event.event_type, -1)
    if not is_newer:
        delivery.save(update_fields=['provider', 'provider_message_id', 'updated_at'])
        return {'accepted': True, 'reason': 'out-of-order-event-recorded', 'event_type': event_type}

    if event_type == 'email.complained':
        delivery.save(update_fields=['provider', 'provider_message_id', 'updated_at'])
        return {'accepted': True, 'reason': 'event-recorded-no-state-change', 'event_type': event_type}

    if event_type in {'email.sent', 'email.delivery_delayed'}:
        if delivery.status != PaymentNotificationDeliveryStatus.DELIVERED:
            delivery.status = PaymentNotificationDeliveryStatus.PROVIDER_ACCEPTED
            delivery.reason_code = (
                'email_delivery_delayed' if event_type == 'email.delivery_delayed' else ''
            )
            delivery.provider_accepted_at = delivery.provider_accepted_at or occurred_at
            delivery.lease_token = None
            delivery.lease_expires_at = None
            delivery.finished_at = None
    elif event_type == 'email.delivered':
        delivery.status = PaymentNotificationDeliveryStatus.DELIVERED
        delivery.reason_code = ''
        delivery.provider_accepted_at = delivery.provider_accepted_at or occurred_at
        delivery.delivered_at = delivery.delivered_at or occurred_at
        delivery.finished_at = occurred_at
        delivery.lease_token = None
        delivery.lease_expires_at = None
    elif event_type in _FAILURE_REASON:
        if delivery.status != PaymentNotificationDeliveryStatus.DELIVERED:
            delivery.status = PaymentNotificationDeliveryStatus.FAILED
            delivery.reason_code = _FAILURE_REASON[event_type]
            delivery.finished_at = occurred_at
            delivery.lease_token = None
            delivery.lease_expires_at = None

    delivery.save(update_fields=[
        'provider', 'provider_message_id', 'status', 'reason_code',
        'provider_accepted_at', 'delivered_at', 'finished_at',
        'lease_token', 'lease_expires_at', 'updated_at',
    ])
    return {'accepted': True, 'reason': 'processed', 'event_type': event_type, 'delivery_id': delivery.pk}


def process_resend_payment_notification_webhook(*, payload: bytes, headers: ResendWebhookHeaders) -> dict:
    """Correlate signed Resend events through non-PII send tags, then fence tenant writes."""
    verify_resend_webhook_signature(
        payload=payload,
        headers=headers,
        webhook_secret=getattr(settings, 'PAYMENT_NOTIFICATION_RESEND_WEBHOOK_SECRET', '').strip(),
    )
    try:
        body = json.loads(payload.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResendWebhookVerificationError('invalid-json') from exc
    if not isinstance(body, dict):
        raise ResendWebhookVerificationError('invalid-payload')
    event_type = str(body.get('type') or '').strip()
    if event_type not in _PAYMENT_EMAIL_EVENTS:
        return {'accepted': True, 'reason': 'ignored-event-type', 'event_type': event_type}

    data = body.get('data')
    if not isinstance(data, dict):
        raise ResendWebhookVerificationError('event-data-invalid')
    provider_message_id = str(data.get('email_id') or '').strip()
    if not provider_message_id:
        raise ResendWebhookVerificationError('email-id-missing')
    event_id = (headers.webhook_id or '').strip()
    if not event_id or len(event_id) > 120:
        raise ResendWebhookVerificationError('invalid-webhook-id')

    tags = _event_tags(data)
    schema_name = tags.get('octobox_box', '')
    delivery_id_text = tags.get('octobox_delivery', '')
    if not schema_name and not delivery_id_text:
        return {'accepted': True, 'reason': 'unrelated-email-event', 'event_type': event_type}
    if not _SCHEMA_RE.fullmatch(schema_name) or not _DELIVERY_ID_RE.fullmatch(delivery_id_text):
        raise ResendPaymentWebhookTenantUnresolved('delivery-correlation-tag-missing')

    active_schema = _resolve_active_schema(schema_name)
    return _apply_event(
        schema_name=active_schema,
        delivery_id=int(delivery_id_text),
        event_id=event_id,
        provider_message_id=provider_message_id,
        event_type=event_type,
        occurred_at=_event_time(body),
    )


__all__ = [
    'ResendPaymentWebhookConflict',
    'ResendPaymentWebhookTenantUnresolved',
    'process_resend_payment_notification_webhook',
]
