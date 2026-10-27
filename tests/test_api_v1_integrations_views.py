"""
ARQUIVO: testes da borda de integracao da API v1.

POR QUE ELE EXISTE:
- protege que o webhook normalize contrato e preserve o `event_id` para idempotencia.
"""

import hashlib
import hmac
import json
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, override_settings
from django.utils import timezone

from api.v1.integrations_views import ResendPaymentNotificationWebhookView, WhatsAppPollWebhookView
from integrations.whatsapp.webhook_auth import (
    AuthenticatedPollRoute,
    canonical_poll_webhook_message,
)
from student_identity.resend_webhooks import ResendWebhookHeaders


@override_settings(ALLOWED_HOSTS=['testserver'])
class ApiV1IntegrationsViewsTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch('api.v1.integrations_views.process_poll_vote_webhook')
    @patch('api.v1.integrations_views.schema_context', return_value=nullcontext())
    def test_whatsapp_poll_rejects_shared_box_key_before_schema_or_writes(
        self,
        schema_context_mock,
        process_poll_vote_mock,
    ):
        secret = 'shared-test-hmac-secret-with-32-bytes'
        raw_body = b'{"event_id":"evt-shared-key","voter_phone":"+5511999999999","poll_name":"Check-in","option_text":"18h"}'
        timestamp = str(int(timezone.now().timestamp()))
        headers = {
            'X-OctoBox-Instance': 'instance-alpha',
            'X-OctoBox-Timestamp': timestamp,
            'X-OctoBox-Event-Id': 'evt-shared-key',
            'X-OctoBox-Key-Id': 'hmac-v1',
        }
        message = canonical_poll_webhook_message(
            instance_id=headers['X-OctoBox-Instance'],
            key_id=headers['X-OctoBox-Key-Id'],
            timestamp=timestamp,
            event_id=headers['X-OctoBox-Event-Id'],
            raw_body=raw_body,
        )
        headers['X-OctoBox-Signature'] = (
            'v1=' + hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
        )
        duplicate_box_config = json.dumps({
            'instance-alpha': {'schema': 'box_alpha', 'keys': {'hmac-v1': secret}},
            'instance-bravo': {'schema': 'box_bravo', 'keys': {'hmac-v1': secret}},
        })
        request = self.factory.post(
            '/api/v1/integrations/whatsapp/webhook/poll-vote/',
            data=raw_body,
            content_type='application/json',
            **{
                'HTTP_X_OCTOBOX_INSTANCE': headers['X-OctoBox-Instance'],
                'HTTP_X_OCTOBOX_TIMESTAMP': headers['X-OctoBox-Timestamp'],
                'HTTP_X_OCTOBOX_EVENT_ID': headers['X-OctoBox-Event-Id'],
                'HTTP_X_OCTOBOX_KEY_ID': headers['X-OctoBox-Key-Id'],
                'HTTP_X_OCTOBOX_SIGNATURE': headers['X-OctoBox-Signature'],
            },
        )

        with override_settings(WHATSAPP_POLL_WEBHOOK_INSTANCES_JSON=duplicate_box_config):
            response = WhatsAppPollWebhookView.as_view()(request)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(json.loads(response.content)['reason'], 'webhook-route-config-invalid')
        self.assertEqual(response['Retry-After'], '60')
        schema_context_mock.assert_not_called()
        process_poll_vote_mock.assert_not_called()

    @patch('api.v1.integrations_views.process_resend_payment_notification_webhook')
    def test_resend_payment_webhook_passes_raw_body_and_svix_headers(self, process_mock):
        process_mock.return_value = {'accepted': True, 'reason': 'processed'}
        raw_body = b'{"type":"email.delivered"}'
        request = self.factory.post(
            '/api/v1/integrations/resend/webhook/payment-notifications/',
            data=raw_body,
            content_type='application/json',
            HTTP_SVIX_ID='evt_123',
            HTTP_SVIX_TIMESTAMP='1782200000',
            HTTP_SVIX_SIGNATURE='v1,signature',
        )

        response = ResendPaymentNotificationWebhookView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {'accepted': True, 'reason': 'processed'})
        process_mock.assert_called_once_with(
            payload=raw_body,
            headers=ResendWebhookHeaders(
                webhook_id='evt_123', timestamp='1782200000', signature='v1,signature',
            ),
        )

    @override_settings(PAYMENT_NOTIFICATION_RESEND_WEBHOOK_SECRET='whsec_test_secret')
    def test_resend_payment_webhook_rejects_invalid_signature(self):
        timestamp = str(int(timezone.now().timestamp()))
        request = self.factory.post(
            '/api/v1/integrations/resend/webhook/payment-notifications/',
            data=b'{}',
            content_type='application/json',
            HTTP_SVIX_ID='evt_invalid',
            HTTP_SVIX_TIMESTAMP=timestamp,
            HTTP_SVIX_SIGNATURE='v1,invalid',
        )

        response = ResendPaymentNotificationWebhookView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)['reason'], 'signature-mismatch')

    @patch('api.v1.integrations_views.process_poll_vote_webhook')
    @patch('api.v1.integrations_views.Box.objects.filter')
    @patch('api.v1.integrations_views.schema_context', return_value=nullcontext())
    @patch('api.v1.integrations_views.authenticate_poll_webhook')
    def test_whatsapp_poll_webhook_passes_event_id_into_contract(
        self,
        authenticate_mock,
        schema_context_mock,
        box_filter_mock,
        process_poll_vote_webhook_mock,
    ):
        authenticate_mock.return_value = (
            AuthenticatedPollRoute(
                instance_id='i-box-test',
                schema_name='box_test',
                key_id='k1',
                event_id='evt_123',
                payload={
                    'voter_phone': '+5511999999999',
                    'poll_name': 'Check in - 23.MAR',
                    'option_text': '18h',
                    'event_id': 'evt_123',
                },
            ),
            None,
        )
        box_filter_mock.return_value.only.return_value.first.return_value = SimpleNamespace(status='active')
        process_poll_vote_webhook_mock.return_value = SimpleNamespace(accepted=True, reason='ok')
        process_poll_vote_webhook_mock.return_value.failure_kind = ''
        process_poll_vote_webhook_mock.return_value.retryable = False
        process_poll_vote_webhook_mock.return_value.retry_action = ''
        process_poll_vote_webhook_mock.return_value.attempt_number = 0
        process_poll_vote_webhook_mock.return_value.max_attempts = 0
        process_poll_vote_webhook_mock.return_value.next_retry_at = ''
        request = self.factory.post(
            '/api/v1/integrations/whatsapp/webhook/poll-vote/',
            data=json.dumps(
                {
                    'voter_phone': '+5511999999999',
                    'poll_name': 'Check in - 23.MAR',
                    'option_text': '18h',
                    'event_id': 'evt_123',
                }
            ),
            content_type='application/json',
        )

        response = WhatsAppPollWebhookView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload['correlation_id'], response['X-OctoBox-Correlation-Id'])
        self.assertEqual(payload['failure_kind'], '')
        self.assertFalse(payload['retryable'])
        self.assertEqual(payload['retry_action'], '')
        poll_vote = process_poll_vote_webhook_mock.call_args.kwargs['poll_vote']
        self.assertEqual(poll_vote.event_id, 'evt_123')
        self.assertEqual(poll_vote.external_id, 'evt_123')
        self.assertEqual(process_poll_vote_webhook_mock.call_args.kwargs['tenant_schema'], 'box_test')

    @patch('api.v1.integrations_views.process_poll_vote_webhook')
    @patch('api.v1.integrations_views.Box.objects.filter')
    @patch('api.v1.integrations_views.schema_context', return_value=nullcontext())
    @patch('api.v1.integrations_views.authenticate_poll_webhook')
    def test_whatsapp_poll_webhook_uses_503_when_retry_is_scheduled(
        self,
        authenticate_mock,
        schema_context_mock,
        box_filter_mock,
        process_poll_vote_webhook_mock,
    ):
        authenticate_mock.return_value = (
            AuthenticatedPollRoute(
                instance_id='i-box-test',
                schema_name='box_test',
                key_id='k1',
                event_id='evt_999',
                payload={
                    'voter_phone': '+5511999999999',
                    'poll_name': 'Check in - 23.MAR',
                    'option_text': '18h',
                    'event_id': 'evt_999',
                },
            ),
            None,
        )
        box_filter_mock.return_value.only.return_value.first.return_value = SimpleNamespace(status='active')
        process_poll_vote_webhook_mock.return_value = SimpleNamespace(
            accepted=False,
            reason='temporary timeout',
            failure_kind='retryable',
            retryable=True,
            retry_action='retry',
            attempt_number=1,
            max_attempts=3,
            next_retry_at='2026-04-16T12:00:10+00:00',
        )
        request = self.factory.post(
            '/api/v1/integrations/whatsapp/webhook/poll-vote/',
            data=json.dumps(
                {
                    'voter_phone': '+5511999999999',
                    'poll_name': 'Check in - 23.MAR',
                    'option_text': '18h',
                    'event_id': 'evt_999',
                }
            ),
            content_type='application/json',
        )

        response = WhatsAppPollWebhookView.as_view()(request)

        self.assertEqual(response.status_code, 503)
        payload = json.loads(response.content)
        self.assertEqual(payload['retry_action'], 'retry')
        self.assertEqual(payload['attempt_number'], 1)
