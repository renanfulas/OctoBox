"""Signed receipt input validation without a database or a real provider."""

import base64
import hashlib
import hmac
import json
from datetime import datetime
from unittest.mock import patch

import pytest
from django.test import RequestFactory, override_settings
from django.utils import timezone

from api.v1.integrations_views import ResendPaymentNotificationWebhookView


def signed_request(created_at):
    payload = json.dumps({
        'type': 'email.delivered', 'created_at': created_at,
        'data': {'email_id': 'synthetic-email', 'tags': {
            'octobox_box': 'box_test', 'octobox_delivery': '1',
        }},
    }).encode()
    event_id = 'synthetic-event'
    timestamp = str(int(timezone.now().timestamp()))
    signed = b'.'.join((event_id.encode(), timestamp.encode(), payload))
    signature = base64.b64encode(hmac.new(b'synthetic_test_secret', signed, hashlib.sha256).digest()).decode()
    return RequestFactory().post(
        '/synthetic-webhook/', data=payload, content_type='application/json',
        HTTP_SVIX_ID=event_id, HTTP_SVIX_TIMESTAMP=timestamp,
        HTTP_SVIX_SIGNATURE=f'v1,{signature}',
    )


@pytest.mark.parametrize('created_at', (
    '2026-02-30T12:00:00Z',
    '2026-13-01T12:00:00Z',
    '2026-10-24T25:00:00Z',
    '2026-10-24T12:00:00+25:00',
    'invalid-date',
    None,
))
@override_settings(PAYMENT_NOTIFICATION_RESEND_WEBHOOK_SECRET='whsec_synthetic_test_secret')
def test_signed_receipt_with_invalid_date_returns_400_without_applying_event(created_at):
    with (
        patch('finance.notification_webhooks._resolve_active_schema', return_value='box_test'),
        patch('finance.notification_webhooks._apply_event') as apply_event,
    ):
        response = ResendPaymentNotificationWebhookView.as_view()(signed_request(created_at))
    assert response.status_code == 400
    assert json.loads(response.content) == {'accepted': False, 'reason': 'event-created-at-invalid'}
    apply_event.assert_not_called()


@pytest.mark.parametrize('created_at', ('2026-10-24T12:00:00Z', '2026-10-24T09:00:00-03:00'))
@override_settings(PAYMENT_NOTIFICATION_RESEND_WEBHOOK_SECRET='whsec_synthetic_test_secret')
def test_signed_receipt_with_valid_date_reaches_event_writer(created_at):
    with (
        patch('finance.notification_webhooks._resolve_active_schema', return_value='box_test'),
        patch('finance.notification_webhooks._apply_event', return_value={'accepted': True}) as apply_event,
    ):
        response = ResendPaymentNotificationWebhookView.as_view()(signed_request(created_at))
    assert response.status_code == 200
    apply_event.assert_called_once()
    assert apply_event.call_args.kwargs['occurred_at'] == datetime.fromisoformat(created_at)
