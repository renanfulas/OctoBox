"""
ARQUIVO: testes do middleware de idempotencia de integracoes.

POR QUE ELE EXISTE:
- protege correlation id transversal e header de resposta da borda de webhook.
"""

import json
from unittest.mock import patch

from django.http import JsonResponse
from django.test import RequestFactory, SimpleTestCase

from integrations.middleware import WebhookIdempotencyMiddleware


class IntegrationsMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch('integrations.middleware.WebhookEvent.objects.filter')
    @patch('integrations.middleware.build_correlation_id')
    @patch('integrations.middleware._webhook_event_table_available')
    def test_process_webhook_sets_correlation_header_on_normal_flow(
        self,
        webhook_table_available_mock,
        build_correlation_id_mock,
        webhook_filter_mock,
    ):
        webhook_table_available_mock.return_value = True
        build_correlation_id_mock.return_value = 'corr-webhook-1'
        webhook_filter_mock.return_value.exists.return_value = False
        request = self.factory.post(
            '/api/v1/integrations/whatsapp/webhook/poll-vote/',
            data=json.dumps({'event_id': 'evt-1'}),
            content_type='application/json',
        )
        middleware = WebhookIdempotencyMiddleware(lambda req: JsonResponse({'accepted': True}))

        response = middleware(request)

        self.assertEqual(response['X-OctoBox-Correlation-Id'], 'corr-webhook-1')
        self.assertEqual(request.octobox_correlation_id, 'corr-webhook-1')

    @patch('integrations.middleware.WebhookEvent.objects.filter')
    @patch('integrations.middleware.build_correlation_id')
    @patch('integrations.middleware._webhook_event_table_available')
    def test_process_webhook_duplicate_response_includes_canonical_idempotency_key(
        self,
        webhook_table_available_mock,
        build_correlation_id_mock,
        webhook_filter_mock,
    ):
        webhook_table_available_mock.return_value = True
        build_correlation_id_mock.return_value = 'corr-webhook-2'
        webhook_filter_mock.return_value.exists.return_value = True
        request = self.factory.post(
            '/api/v1/integrations/whatsapp/webhook/poll-vote/',
            data=json.dumps({'event_id': 'evt-77', 'external_id': 'ext-77'}),
            content_type='application/json',
        )
        middleware = WebhookIdempotencyMiddleware(lambda req: JsonResponse({'accepted': True}))

        response = middleware(request)

        payload = json.loads(response.content)
        self.assertEqual(payload['idempotency_key'], 'evt-77')

    @patch('integrations.middleware.WebhookEvent.objects.filter')
    @patch('integrations.middleware.build_correlation_id')
    @patch('integrations.middleware._webhook_event_table_available')
    def test_process_webhook_skips_dedupe_when_event_table_is_missing(
        self,
        webhook_table_available_mock,
        build_correlation_id_mock,
        webhook_filter_mock,
    ):
        webhook_table_available_mock.return_value = False
        build_correlation_id_mock.return_value = 'corr-webhook-3'
        request = self.factory.post(
            '/api/v1/integrations/whatsapp/webhook/poll-vote/',
            data=json.dumps({'event_id': 'evt-missing-table'}),
            content_type='application/json',
        )
        middleware = WebhookIdempotencyMiddleware(lambda req: JsonResponse({'accepted': True}))

        response = middleware(request)

        webhook_filter_mock.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-OctoBox-Correlation-Id'], 'corr-webhook-3')
