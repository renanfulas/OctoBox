"""
ARQUIVO: testes do dead-letter sweep de eventos Stripe.

POR QUE EXISTE:
- Protege a drenagem automatica de PaymentWebhookEvent vencidos (F3): antes deste
  sweep, eventos Stripe que falhavam de forma reprocessavel ficavam PENDING para
  sempre. Garante tambem que a defense policy do alert-siren e respeitada.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from integrations.stripe.models import PaymentWebhookEvent, PaymentWebhookStatus
from integrations.stripe.reprocessing import reprocess_due_stripe_webhook_events


def _pending_event(event_id, *, next_retry_at, event_type='payment_intent.succeeded'):
    # payment_intent.succeeded nao tem handler em _HANDLERS -> route apenas
    # mark_processed: isola o teste do sweep da logica de reconciliacao de tenant.
    return PaymentWebhookEvent.objects.create(
        event_id=event_id,
        event_type=event_type,
        payload={'id': event_id, 'type': event_type, 'data': {}},
        status=PaymentWebhookStatus.PENDING,
        next_retry_at=next_retry_at,
    )


@patch('integrations.stripe.reprocessing.remember_signal_mesh_sweep')
@patch('integrations.stripe.reprocessing.record_retry_sweep')
class StripeReprocessingTests(TestCase):
    @patch('integrations.stripe.reprocessing.get_alert_siren_defense_policy', return_value={})
    def test_due_pending_event_is_rerouted(self, _policy, _metric, _runtime):
        event = _pending_event('evt_due', next_retry_at=timezone.now() - timedelta(minutes=5))

        result = reprocess_due_stripe_webhook_events(limit=10)

        self.assertEqual(result['processed_count'], 1)
        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.PROCESSED)

    @patch('integrations.stripe.reprocessing.get_alert_siren_defense_policy', return_value={})
    def test_future_retry_is_not_picked(self, _policy, _metric, _runtime):
        _pending_event('evt_future', next_retry_at=timezone.now() + timedelta(hours=1))

        result = reprocess_due_stripe_webhook_events(limit=10)

        self.assertEqual(result['processed_count'], 0)

    @patch(
        'integrations.stripe.reprocessing.get_alert_siren_defense_policy',
        return_value={'pause_webhook_retries': True, 'level': 'contained'},
    )
    def test_defense_policy_pause_skips_processing(self, _policy, _metric, _runtime):
        event = _pending_event('evt_paused', next_retry_at=timezone.now() - timedelta(minutes=5))

        result = reprocess_due_stripe_webhook_events(limit=10)

        self.assertEqual(result['processed_count'], 0)
        self.assertGreaterEqual(result['skipped_count'], 1)
        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.PENDING)
