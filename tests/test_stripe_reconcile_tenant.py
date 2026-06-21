"""
ARQUIVO: teste de fidelidade do reconcile de pagamento de aluno em multi-tenant.

POR QUE EXISTE:
- O webhook Stripe chega no schema `public` (esta em PUBLIC_SCHEMA_PATHS), mas
  Payment vive no schema do box (TENANT_APP). Antes do fix, o reconcile fazia
  SELECT em public e estourava 'relation does not exist' — o aluno pagava e o
  OctoBox nunca dava baixa. A cobertura existente do router MOCKA o reconcile,
  entao nunca exercia esse caminho real: este arquivo fecha essa lacuna.

ESCOPO:
- checkout.session.completed com metadata.box_schema reconcilia o Payment do
  tenant correto (de PENDING para PAID) rodando a partir do schema public.
- box_schema ausente/desconhecido => falha NAO reprocessavel, Payment intacto.

@pytest.mark.public_schema: simula a condicao real do webhook (sem tenant
resolvido). PaymentWebhookEvent e Box sao shared (public); Payment e criado e
verificado dentro de schema_context('box_test').
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.test import TestCase
from django_tenants.utils import schema_context

from finance.models import Payment, PaymentStatus
from integrations.stripe.models import PaymentWebhookEvent, PaymentWebhookStatus
from integrations.stripe.router import route_payment_webhook_event
from tests.factories import PaymentFactory

TENANT_SCHEMA = 'box_test'


def _checkout_completed_event(*, event_id, payment_id, amount_cents, box_schema, version=0):
    metadata = {'payment_id': str(payment_id), 'version_locked': str(version)}
    if box_schema is not None:
        metadata['box_schema'] = box_schema
    return PaymentWebhookEvent.objects.create(
        event_id=event_id,
        event_type='checkout.session.completed',
        payload={
            'id': event_id,
            'type': 'checkout.session.completed',
            'data': {'object': {'amount_total': amount_cents, 'metadata': metadata}},
        },
    )


@pytest.mark.public_schema
class StripeReconcileTenantTests(TestCase):
    def _make_tenant_payment(self, amount='149.90'):
        with schema_context(TENANT_SCHEMA):
            payment = PaymentFactory(amount=amount, status=PaymentStatus.PENDING)
            return payment.id, int(Decimal(amount) * 100)

    def test_reconcile_marks_tenant_payment_paid_from_public_schema(self):
        payment_id, amount_cents = self._make_tenant_payment()

        event = _checkout_completed_event(
            event_id='evt_reconcile_ok',
            payment_id=payment_id,
            amount_cents=amount_cents,
            box_schema=TENANT_SCHEMA,
        )

        route_payment_webhook_event(event)

        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.PROCESSED)

        with schema_context(TENANT_SCHEMA):
            payment = Payment.objects.get(pk=payment_id)
            self.assertEqual(payment.status, PaymentStatus.PAID)
            self.assertIsNotNone(payment.paid_at)

    def test_missing_box_schema_fails_non_retryable_and_leaves_payment_pending(self):
        payment_id, amount_cents = self._make_tenant_payment()

        event = _checkout_completed_event(
            event_id='evt_no_box',
            payment_id=payment_id,
            amount_cents=amount_cents,
            box_schema=None,
        )

        route_payment_webhook_event(event)

        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.FAILED)

        with schema_context(TENANT_SCHEMA):
            payment = Payment.objects.get(pk=payment_id)
            self.assertEqual(payment.status, PaymentStatus.PENDING)

    def test_unknown_box_schema_fails_non_retryable(self):
        payment_id, amount_cents = self._make_tenant_payment()

        event = _checkout_completed_event(
            event_id='evt_bad_box',
            payment_id=payment_id,
            amount_cents=amount_cents,
            box_schema='box_does_not_exist',
        )

        route_payment_webhook_event(event)

        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.FAILED)
        with schema_context(TENANT_SCHEMA):
            self.assertEqual(Payment.objects.get(pk=payment_id).status, PaymentStatus.PENDING)
