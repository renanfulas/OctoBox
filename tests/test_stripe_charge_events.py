"""
ARQUIVO: testes dos handlers de charge.refunded / charge.dispute.* do Stripe.

POR QUE EXISTE:
- Esses eventos chegam SEM a nossa metadata (so trazem payment_intent), entao o
  webhook (schema public) so consegue achar o tenant via StripePaymentRef. Estes
  testes provam: estorno do lado Stripe vira REFUNDED no box certo (idempotente),
  charge sem ref e no-op, e disputa gera audit event (sem mexer no status).

@pytest.mark.public_schema: simula a condicao real do webhook. Payment/AuditEvent
sao verificados dentro de schema_context('box_test'); StripePaymentRef e shared.
"""

from __future__ import annotations

import pytest
from django.test import TestCase
from django_tenants.utils import schema_context

from auditing.models import AuditEvent
from finance.models import Payment, PaymentStatus
from integrations.stripe.models import (
    PaymentWebhookEvent,
    PaymentWebhookStatus,
    StripePaymentRef,
)
from integrations.stripe.router import route_payment_webhook_event
from tests.factories import PaymentFactory

TENANT_SCHEMA = 'box_test'


def _charge_event(*, event_id, event_type, payment_intent, charge_id='ch_test', status=None):
    obj = {'id': charge_id, 'payment_intent': payment_intent}
    if status is not None:
        obj['status'] = status
    return PaymentWebhookEvent.objects.create(
        event_id=event_id,
        event_type=event_type,
        payload={'id': event_id, 'type': event_type, 'data': {'object': obj}},
    )


@pytest.mark.public_schema
class StripeChargeEventsTests(TestCase):
    def _paid_payment_with_ref(self, payment_intent):
        with schema_context(TENANT_SCHEMA):
            payment = PaymentFactory(amount='149.90', status=PaymentStatus.PAID)
            pid = payment.id
        StripePaymentRef.objects.create(
            payment_intent_id=payment_intent,
            box_schema=TENANT_SCHEMA,
            payment_id=pid,
        )
        return pid

    def test_charge_refunded_marks_payment_refunded(self):
        pid = self._paid_payment_with_ref('pi_refund')

        event = _charge_event(
            event_id='evt_refund',
            event_type='charge.refunded',
            payment_intent='pi_refund',
            charge_id='ch_abc',
        )
        route_payment_webhook_event(event)

        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.PROCESSED)
        with schema_context(TENANT_SCHEMA):
            payment = Payment.objects.get(pk=pid)
            self.assertEqual(payment.status, PaymentStatus.REFUNDED)
            self.assertEqual(payment.stripe_charge_id, 'ch_abc')

    def test_charge_refunded_is_idempotent(self):
        pid = self._paid_payment_with_ref('pi_idem')

        for eid in ('evt_idem_1', 'evt_idem_2'):
            route_payment_webhook_event(
                _charge_event(event_id=eid, event_type='charge.refunded', payment_intent='pi_idem')
            )

        with schema_context(TENANT_SCHEMA):
            self.assertEqual(Payment.objects.get(pk=pid).status, PaymentStatus.REFUNDED)

    def test_charge_refunded_without_ref_is_noop(self):
        with schema_context(TENANT_SCHEMA):
            payment = PaymentFactory(amount='149.90', status=PaymentStatus.PAID)
            pid = payment.id

        event = _charge_event(
            event_id='evt_noref',
            event_type='charge.refunded',
            payment_intent='pi_unknown',
        )
        route_payment_webhook_event(event)

        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.PROCESSED)  # no-op, nao falha
        with schema_context(TENANT_SCHEMA):
            self.assertEqual(Payment.objects.get(pk=pid).status, PaymentStatus.PAID)

    def test_dispute_created_records_audit_event_without_changing_status(self):
        pid = self._paid_payment_with_ref('pi_dispute')

        event = _charge_event(
            event_id='evt_dispute',
            event_type='charge.dispute.created',
            payment_intent='pi_dispute',
            status='needs_response',
        )
        route_payment_webhook_event(event)

        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.PROCESSED)
        with schema_context(TENANT_SCHEMA):
            audit = AuditEvent.objects.filter(action='payment_dispute_via_stripe').latest('created_at')
            self.assertEqual(audit.metadata.get('dispute_status'), 'needs_response')
            # Disputa nao e estorno: status do Payment permanece PAID.
            self.assertEqual(Payment.objects.get(pk=pid).status, PaymentStatus.PAID)
