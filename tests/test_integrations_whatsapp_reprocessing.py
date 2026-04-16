"""
ARQUIVO: testes do reprocessamento de webhooks vencidos.

POR QUE ELE EXISTE:
- garante a simetria do corredor de retries para `WebhookEvent.next_retry_at`.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from integrations.whatsapp.reprocessing import reprocess_due_webhook_events


class IntegrationsWhatsAppReprocessingTests(SimpleTestCase):
    @patch('integrations.whatsapp.reprocessing.record_retry_sweep')
    @patch('integrations.whatsapp.reprocessing.get_alert_siren_defense_policy')
    @patch('integrations.whatsapp.reprocessing.WebhookEvent.objects.filter')
    def test_reprocess_due_webhook_events_contains_queue_when_alert_siren_is_high(
        self,
        webhook_filter_mock,
        defense_policy_mock,
        record_retry_sweep_mock,
    ):
        webhook_filter_mock.return_value.count.return_value = 3
        defense_policy_mock.return_value = {
            'level': 'high',
            'pause_webhook_retries': True,
            'webhook_limit_cap': 0,
        }

        result = reprocess_due_webhook_events(
            limit=10,
            now=datetime(2026, 4, 16, 12, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(result['processed_count'], 0)
        self.assertEqual(result['skipped'][0]['reason'], 'alert-siren-contained')
        record_retry_sweep_mock.assert_called_once()

    @patch('integrations.whatsapp.reprocessing.record_retry_sweep')
    @patch('integrations.whatsapp.reprocessing.get_alert_siren_defense_policy')
    @patch('integrations.whatsapp.reprocessing.process_poll_vote_webhook')
    @patch('integrations.whatsapp.reprocessing.WebhookEvent.objects.filter')
    def test_reprocess_due_webhook_events_processes_supported_payload(
        self,
        webhook_filter_mock,
        process_poll_vote_webhook_mock,
        defense_policy_mock,
        record_retry_sweep_mock,
    ):
        due_event = SimpleNamespace(
            event_id='evt-1',
            payload={
                'kind': 'poll_vote',
                'raw_payload': {
                    'voter_phone': '+5511999999999',
                    'poll_name': 'Check in - 23.MAR',
                    'option_text': '18h',
                    'event_id': 'evt-1',
                },
            },
        )
        webhook_filter_mock.return_value.count.return_value = 1
        webhook_filter_mock.return_value.order_by.return_value.__getitem__.return_value = [due_event]
        defense_policy_mock.return_value = {
            'level': 'silent',
            'pause_webhook_retries': False,
            'webhook_limit_cap': None,
        }
        process_poll_vote_webhook_mock.return_value = SimpleNamespace(
            accepted=True,
            retry_action='',
            failure_kind='',
        )

        result = reprocess_due_webhook_events(
            limit=10,
            now=datetime(2026, 4, 16, 12, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(result['processed_count'], 1)
        self.assertEqual(result['processed'][0]['event_id'], 'evt-1')
        record_retry_sweep_mock.assert_called_once()

    @patch('integrations.whatsapp.reprocessing.record_retry_sweep')
    @patch('integrations.whatsapp.reprocessing.get_alert_siren_defense_policy')
    @patch('integrations.whatsapp.reprocessing.WebhookEvent.objects.filter')
    def test_reprocess_due_webhook_events_skips_unsupported_payload(
        self,
        webhook_filter_mock,
        defense_policy_mock,
        record_retry_sweep_mock,
    ):
        due_event = SimpleNamespace(
            event_id='evt-2',
            payload={'kind': 'unknown'},
        )
        webhook_filter_mock.return_value.count.return_value = 1
        webhook_filter_mock.return_value.order_by.return_value.__getitem__.return_value = [due_event]
        defense_policy_mock.return_value = {
            'level': 'silent',
            'pause_webhook_retries': False,
            'webhook_limit_cap': None,
        }

        result = reprocess_due_webhook_events(
            limit=10,
            now=datetime(2026, 4, 16, 12, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(result['processed_count'], 0)
        self.assertEqual(result['skipped'][0]['reason'], 'unsupported-or-incomplete-payload')
        record_retry_sweep_mock.assert_called_once()
