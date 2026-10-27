"""Pure tests for tenant-aware WhatsApp poll retries and legacy containment."""

from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from integrations.whatsapp.reprocessing import reprocess_due_webhook_events


class IntegrationsWhatsAppReprocessingTests(SimpleTestCase):
    @patch('integrations.whatsapp.reprocessing.record_retry_sweep')
    @patch('integrations.whatsapp.reprocessing.get_alert_siren_defense_policy')
    @patch('integrations.whatsapp.reprocessing.WebhookEvent.objects.filter')
    @patch('integrations.whatsapp.reprocessing.WhatsAppPollWebhookIntent.objects.filter')
    @patch('integrations.whatsapp.reprocessing.Box.objects.filter')
    @patch('integrations.whatsapp.reprocessing.schema_context', return_value=nullcontext())
    def test_retries_are_contained_when_alert_siren_is_high(
        self,
        _schema_context_mock,
        box_filter_mock,
        intent_filter_mock,
        legacy_filter_mock,
        defense_policy_mock,
        record_retry_sweep_mock,
    ):
        box_filter_mock.return_value.only.return_value.order_by.return_value = []
        legacy_filter_mock.return_value.count.return_value = 3
        defense_policy_mock.return_value = {
            'level': 'high',
            'pause_webhook_retries': True,
            'webhook_limit_cap': 0,
        }

        result = reprocess_due_webhook_events(
            limit=10,
            now=datetime(2026, 10, 23, 12, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(result['processed_count'], 0)
        self.assertEqual(result['legacy_unrouted_count'], 3)
        self.assertEqual(result['skipped'][0]['reason'], 'alert-siren-contained')
        intent_filter_mock.assert_not_called()
        record_retry_sweep_mock.assert_called_once()

    @patch('integrations.whatsapp.reprocessing.record_retry_sweep')
    @patch('integrations.whatsapp.reprocessing.get_alert_siren_defense_policy')
    @patch('integrations.whatsapp.reprocessing.process_poll_vote_webhook')
    @patch('integrations.whatsapp.reprocessing.WebhookEvent.objects.filter')
    @patch('integrations.whatsapp.reprocessing.WhatsAppPollWebhookIntent.objects.filter')
    @patch('integrations.whatsapp.reprocessing.Box.objects.filter')
    @patch('integrations.whatsapp.reprocessing.schema_context', return_value=nullcontext())
    def test_retries_intent_inside_its_box_scope(
        self,
        _schema_context_mock,
        box_filter_mock,
        intent_filter_mock,
        legacy_filter_mock,
        process_poll_vote_webhook_mock,
        defense_policy_mock,
        record_retry_sweep_mock,
    ):
        box = SimpleNamespace(schema_name='box_alpha')
        box_filter_mock.return_value.only.return_value.order_by.return_value = [box]
        intent = SimpleNamespace(
            event_id='evt-1',
            phone='+5511999999999',
            poll_title='Check in - 23.MAR',
            option_voted='18h',
        )
        queryset = intent_filter_mock.return_value.order_by.return_value
        queryset.count.return_value = 1
        queryset.__getitem__.return_value = [intent]
        legacy_filter_mock.return_value.count.return_value = 0
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
            now=datetime(2026, 10, 23, 12, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(result['processed_count'], 1)
        self.assertEqual(result['processed'][0]['tenant_schema'], 'box_alpha')
        self.assertEqual(result['processed'][0]['event_id'], 'evt-1')
        call = process_poll_vote_webhook_mock.call_args.kwargs
        self.assertEqual(call['tenant_schema'], 'box_alpha')
        self.assertEqual(call['poll_vote'].event_id, 'evt-1')
        record_retry_sweep_mock.assert_called_once()

    @patch('integrations.whatsapp.reprocessing.record_retry_sweep')
    @patch('integrations.whatsapp.reprocessing.get_alert_siren_defense_policy')
    @patch('integrations.whatsapp.reprocessing.WebhookEvent.objects.filter')
    @patch('integrations.whatsapp.reprocessing.WhatsAppPollWebhookIntent.objects.filter')
    @patch('integrations.whatsapp.reprocessing.Box.objects.filter')
    @patch('integrations.whatsapp.reprocessing.schema_context', return_value=nullcontext())
    def test_legacy_public_event_is_counted_but_never_routed_by_guess(
        self,
        _schema_context_mock,
        box_filter_mock,
        intent_filter_mock,
        legacy_filter_mock,
        defense_policy_mock,
        record_retry_sweep_mock,
    ):
        box_filter_mock.return_value.only.return_value.order_by.return_value = []
        legacy_filter_mock.return_value.count.return_value = 1
        defense_policy_mock.return_value = {
            'level': 'silent',
            'pause_webhook_retries': False,
            'webhook_limit_cap': None,
        }

        result = reprocess_due_webhook_events(
            limit=10,
            now=datetime(2026, 10, 23, 12, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(result['processed_count'], 0)
        self.assertEqual(result['legacy_unrouted_count'], 1)
        self.assertEqual(result['skipped'][0]['reason'], 'legacy-event-without-tenant-route')
        intent_filter_mock.assert_not_called()
        record_retry_sweep_mock.assert_called_once()
