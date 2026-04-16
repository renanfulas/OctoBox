from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as dt_timezone

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.dateparse import parse_datetime

from auditing.services import log_audit_event
from .models import (
    StudentInvitationDelivery,
    StudentInvitationDeliveryEvent,
    StudentInvitationDeliveryStatus,
)


class ResendWebhookVerificationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ResendWebhookHeaders:
    webhook_id: str
    timestamp: str
    signature: str


EVENT_STATUS_MAP = {
    'email.delivered': StudentInvitationDeliveryStatus.DELIVERED,
    'email.delivery_delayed': StudentInvitationDeliveryStatus.DELAYED,
    'email.bounced': StudentInvitationDeliveryStatus.BOUNCED,
    'email.complained': StudentInvitationDeliveryStatus.COMPLAINED,
    'email.suppressed': StudentInvitationDeliveryStatus.SUPPRESSED,
    'email.failed': StudentInvitationDeliveryStatus.FAILED,
}


def _get_webhook_secret() -> str:
    return getattr(settings, 'STUDENT_RESEND_WEBHOOK_SECRET', '').strip()


def _verify_timestamp(timestamp: str) -> None:
    try:
        event_time = datetime.fromtimestamp(int(timestamp), tz=dt_timezone.utc)
    except (TypeError, ValueError, OSError) as exc:
        raise ResendWebhookVerificationError('invalid-timestamp') from exc

    if abs((timezone.now() - event_time).total_seconds()) > timedelta(minutes=5).total_seconds():
        raise ResendWebhookVerificationError('timestamp-out-of-window')


def verify_resend_webhook_signature(*, payload: bytes, headers: ResendWebhookHeaders) -> None:
    secret = _get_webhook_secret()
    if not secret:
        raise ResendWebhookVerificationError('webhook-secret-missing')

    _verify_timestamp(headers.timestamp)

    if not secret.startswith('whsec_'):
        raise ResendWebhookVerificationError('invalid-webhook-secret-format')
    signing_secret = secret[len('whsec_'):]
    signed_content = b'.'.join(
        [
            headers.webhook_id.encode('utf-8'),
            headers.timestamp.encode('utf-8'),
            payload,
        ]
    )
    expected_signature = base64.b64encode(
        hmac.new(signing_secret.encode('utf-8'), signed_content, hashlib.sha256).digest()
    ).decode('utf-8')

    provided_signatures = []
    for item in headers.signature.split():
        if ',' not in item:
            continue
        version, signature = item.split(',', 1)
        if version == 'v1':
            provided_signatures.append(signature)

    if not any(constant_time_compare(expected_signature, signature) for signature in provided_signatures):
        raise ResendWebhookVerificationError('signature-mismatch')


def _parse_payload(payload: bytes) -> dict:
    try:
        return json.loads(payload.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResendWebhookVerificationError('invalid-json') from exc


def _parse_occurred_at(value: str | None):
    if not value:
        return None
    return parse_datetime(value)


@transaction.atomic
def process_resend_webhook(*, payload: bytes, headers: ResendWebhookHeaders) -> dict:
    verify_resend_webhook_signature(payload=payload, headers=headers)
    body = _parse_payload(payload)
    event_type = (body.get('type') or '').strip()
    if event_type not in EVENT_STATUS_MAP:
        return {'accepted': True, 'reason': 'ignored-event-type', 'event_type': event_type}

    data = body.get('data') or {}
    provider_message_id = str(data.get('email_id') or '').strip()
    if not provider_message_id:
        raise ResendWebhookVerificationError('email-id-missing')

    delivery = (
        StudentInvitationDelivery.objects.select_related('invitation', 'invitation__student')
        .filter(provider='resend', provider_message_id=provider_message_id)
        .first()
    )
    if delivery is None:
        return {'accepted': True, 'reason': 'delivery-not-found', 'event_type': event_type}

    if StudentInvitationDeliveryEvent.objects.filter(provider_event_id=headers.webhook_id).exists():
        return {'accepted': True, 'reason': 'duplicate-event', 'event_type': event_type}

    occurred_at = _parse_occurred_at(body.get('created_at') or data.get('created_at')) or timezone.now()
    StudentInvitationDeliveryEvent.objects.create(
        delivery=delivery,
        provider_event_id=headers.webhook_id,
        provider='resend',
        event_type=event_type,
        occurred_at=occurred_at,
        payload=body,
    )

    delivery.status = EVENT_STATUS_MAP[event_type]
    delivery.metadata = {**(delivery.metadata or {}), 'last_webhook_event_type': event_type}
    if event_type == 'email.delivered':
        delivery.sent_at = delivery.sent_at or occurred_at
    else:
        delivery.failed_at = delivery.failed_at or occurred_at
        if event_type in {'email.bounced', 'email.failed', 'email.complained', 'email.suppressed'}:
            delivery.error_message = (event_type or '')[:255]
    delivery.save(update_fields=['status', 'metadata', 'sent_at', 'failed_at', 'error_message', 'updated_at'])

    log_audit_event(
        actor=None,
        action='student_invitation.delivery.webhook_processed',
        target=delivery.invitation,
        description=f'Webhook do Resend processado para convite do app do aluno: {event_type}.',
        metadata={
            'provider': 'resend',
            'provider_event_id': headers.webhook_id,
            'provider_message_id': provider_message_id,
            'delivery_id': delivery.id,
            'event_type': event_type,
        },
    )

    return {'accepted': True, 'reason': 'processed', 'event_type': event_type, 'delivery_id': delivery.id}


__all__ = [
    'ResendWebhookHeaders',
    'ResendWebhookVerificationError',
    'process_resend_webhook',
    'verify_resend_webhook_signature',
]
