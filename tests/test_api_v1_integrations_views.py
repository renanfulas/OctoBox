"""
ARQUIVO: testes da borda de integracao da API v1.

POR QUE ELE EXISTE:
- protege que o webhook normalize contrato e preserve o `event_id` para idempotencia.
"""

import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, override_settings

from api.v1.integrations_views import WhatsAppPollWebhookView


@override_settings(ALLOWED_HOSTS=['testserver'])
class ApiV1IntegrationsViewsTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch('api.v1.integrations_views.process_poll_vote_webhook')
    @patch('api.v1.integrations_views.os.getenv')
    def test_whatsapp_poll_webhook_passes_event_id_into_contract(
        self,
        getenv_mock,
        process_poll_vote_webhook_mock,
    ):
        getenv_mock.return_value = 'secret-token'
        process_poll_vote_webhook_mock.return_value = SimpleNamespace(accepted=True, reason='ok')
        process_poll_vote_webhook_mock.return_value.failure_kind = ''
        process_poll_vote_webhook_mock.return_value.retryable = False
        process_poll_vote_webhook_mock.return_value.retry_action = ''
        process_poll_vote_webhook_mock.return_value.attempt_number = 0
        process_poll_vote_webhook_mock.return_value.max_attempts = 0
        process_poll_vote_webhook_mock.return_value.next_retry_at = ''
        request = self.factory.post(
            '/api/v1/integrations/whatsapp/poll-webhook/',
            data=json.dumps(
                {
                    'voter_phone': '+5511999999999',
                    'poll_name': 'Check in - 23.MAR',
                    'option_text': '18h',
                    'event_id': 'evt_123',
                }
            ),
            content_type='application/json',
            HTTP_X_OCTOBOX_WEBHOOK_TOKEN='secret-token',
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

    @patch('api.v1.integrations_views.process_poll_vote_webhook')
    @patch('api.v1.integrations_views.os.getenv')
    def test_whatsapp_poll_webhook_uses_503_when_retry_is_scheduled(
        self,
        getenv_mock,
        process_poll_vote_webhook_mock,
    ):
        getenv_mock.return_value = 'secret-token'
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
            '/api/v1/integrations/whatsapp/poll-webhook/',
            data=json.dumps(
                {
                    'voter_phone': '+5511999999999',
                    'poll_name': 'Check in - 23.MAR',
                    'option_text': '18h',
                    'event_id': 'evt_999',
                }
            ),
            content_type='application/json',
            HTTP_X_OCTOBOX_WEBHOOK_TOKEN='secret-token',
        )

        response = WhatsAppPollWebhookView.as_view()(request)

        self.assertEqual(response.status_code, 503)
        payload = json.loads(response.content)
        self.assertEqual(payload['retry_action'], 'retry')
        self.assertEqual(payload['attempt_number'], 1)
