"""
ARQUIVO: testes da retencao de eventos Stripe processados (S5).

POR QUE EXISTE:
- Garante que so PaymentWebhookEvent PROCESSED antigos sao apagados; FAILED
  (dead-letter) e PROCESSED recentes sao preservados.
"""

from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from integrations.stripe.models import PaymentWebhookEvent, PaymentWebhookStatus
from integrations.stripe.retention import purge_processed_payment_webhook_events


def _event(event_id, status, age_days):
    event = PaymentWebhookEvent.objects.create(
        event_id=event_id,
        event_type='checkout.session.completed',
        payload={'id': event_id},
        status=status,
    )
    # updated_at tem auto_now; .update() bypassa para simular idade.
    aged = timezone.now() - timedelta(days=age_days)
    PaymentWebhookEvent.objects.filter(pk=event.pk).update(updated_at=aged)
    return event


class WebhookRetentionTests(TestCase):
    def test_purges_only_old_processed_events(self):
        old_processed = _event('old_proc', PaymentWebhookStatus.PROCESSED, age_days=120)
        recent_processed = _event('recent_proc', PaymentWebhookStatus.PROCESSED, age_days=10)
        old_failed = _event('old_failed', PaymentWebhookStatus.FAILED, age_days=120)

        deleted = purge_processed_payment_webhook_events(days=90)

        self.assertEqual(deleted, 1)
        self.assertFalse(PaymentWebhookEvent.objects.filter(pk=old_processed.pk).exists())
        self.assertTrue(PaymentWebhookEvent.objects.filter(pk=recent_processed.pk).exists())
        self.assertTrue(PaymentWebhookEvent.objects.filter(pk=old_failed.pk).exists())

    def test_nothing_purged_when_all_recent(self):
        _event('p1', PaymentWebhookStatus.PROCESSED, age_days=5)
        _event('p2', PaymentWebhookStatus.PROCESSED, age_days=1)

        deleted = purge_processed_payment_webhook_events(days=90)

        self.assertEqual(deleted, 0)
        self.assertEqual(PaymentWebhookEvent.objects.count(), 2)
