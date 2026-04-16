"""
ARQUIVO: testes do tracking de retry do webhook do WhatsApp.

POR QUE ELE EXISTE:
- garante que `WebhookEvent` fale a retry policy canonica da mesh.
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from integrations.whatsapp.models import WebhookDeliveryStatus, WebhookEvent


class IntegrationsWhatsAppModelsTests(SimpleTestCase):
    @patch.object(WebhookEvent, 'save')
    def test_register_failure_schedules_retry_for_retryable_failure(self, save_mock):
        webhook_event = WebhookEvent(
            provider='evolution',
            payload={},
            attempts=0,
            max_retries=3,
        )

        decision = webhook_event.register_failure(
            failure_kind='retryable',
            error_message='timeout',
            reason='timeout',
        )

        self.assertTrue(decision.should_retry)
        self.assertEqual(webhook_event.status, WebhookDeliveryStatus.PENDING)
        self.assertEqual(webhook_event.attempts, 1)
        self.assertIsNotNone(webhook_event.next_retry_at)
        save_mock.assert_called_once()

    @patch.object(WebhookEvent, 'save')
    def test_register_failure_gives_up_for_non_retryable_failure(self, save_mock):
        webhook_event = WebhookEvent(
            provider='evolution',
            payload={},
            attempts=0,
            max_retries=3,
        )

        decision = webhook_event.register_failure(
            failure_kind='invalid_payload',
            error_message='invalid-json',
            reason='invalid-json',
        )

        self.assertFalse(decision.should_retry)
        self.assertEqual(webhook_event.status, WebhookDeliveryStatus.FAILED)
        self.assertEqual(webhook_event.attempts, 1)
        self.assertIsNone(webhook_event.next_retry_at)
        save_mock.assert_called_once()
