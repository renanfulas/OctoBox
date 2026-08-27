"""
ARQUIVO: teste de gate da Onda 3 — Pix nao reconcilia antes da confirmacao real.

POR QUE EXISTE:
- Pix (e qualquer metodo delayed-notification) dispara checkout.session.completed
  NA HORA do clique, com payment_status='unpaid' — o dinheiro ainda nao chegou.
  Antes desta onda, _handle_student_payment reconciliava so olhando amount_total,
  ignorando payment_status: um Pix apenas gerado (nunca pago, ou expirado) dava
  baixa no Payment como se tivesse sido pago.
- O resultado real chega depois via checkout.session.async_payment_succeeded
  (paga) ou ..._failed (expirou/falhou) — ambos roteiam para o mesmo handler
  (_HANDLERS em integrations/stripe/router.py), com o mesmo formato de payload.

@pytest.mark.public_schema: mesmo padrao de test_stripe_reconcile_tenant.py —
simula a condicao real do webhook (schema public, sem tenant resolvido).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.test import TestCase
from django_tenants.utils import schema_context

from finance.models import Payment, PaymentStatus
from integrations.stripe.models import PaymentWebhookEvent, PaymentWebhookStatus, StripePaymentRef
from integrations.stripe.router import route_payment_webhook_event
from tests.factories import PaymentFactory

TENANT_SCHEMA = 'box_test'


def _checkout_event(*, event_id, event_type, payment_id, amount_cents, payment_status,
                     payment_intent='pi_pix_test', version=0):
    return PaymentWebhookEvent.objects.create(
        event_id=event_id,
        event_type=event_type,
        payload={
            'id': event_id,
            'type': event_type,
            'data': {'object': {
                'amount_total': amount_cents,
                'payment_intent': payment_intent,
                'payment_status': payment_status,
                'metadata': {
                    'payment_id': str(payment_id),
                    'version_locked': str(version),
                    'box_schema': TENANT_SCHEMA,
                },
            }},
        },
    )


@pytest.mark.public_schema
class PixAsyncConfirmationTests(TestCase):
    def _make_tenant_payment(self, amount='149.90'):
        with schema_context(TENANT_SCHEMA):
            payment = PaymentFactory(amount=amount, status=PaymentStatus.PENDING)
            return payment.id, int(Decimal(amount) * 100)

    def test_unpaid_checkout_completed_does_not_reconcile(self):
        """Pix: clique no QR code dispara completed com payment_status=unpaid.
        Não pode dar baixa — o dinheiro ainda não chegou."""
        payment_id, amount_cents = self._make_tenant_payment()

        event = _checkout_event(
            event_id='evt_pix_unpaid',
            event_type='checkout.session.completed',
            payment_id=payment_id,
            amount_cents=amount_cents,
            payment_status='unpaid',
        )
        route_payment_webhook_event(event)

        event.refresh_from_db()
        self.assertEqual(
            event.status, PaymentWebhookStatus.PROCESSED,
            'evento nao deveria falhar — so nao reconcilia ainda',
        )
        with schema_context(TENANT_SCHEMA):
            payment = Payment.objects.get(pk=payment_id)
            self.assertEqual(
                payment.status, PaymentStatus.PENDING,
                'Payment foi reconciliado com Pix ainda unpaid — a baixa aconteceu antes do dinheiro chegar',
            )

    def test_unpaid_checkout_completed_still_records_payment_ref(self):
        """Mesmo sem reconciliar, o StripePaymentRef precisa existir — os
        eventos async_payment_succeeded/_failed e charge.* que vem depois
        dependem dele para achar o box."""
        payment_id, amount_cents = self._make_tenant_payment()

        event = _checkout_event(
            event_id='evt_pix_ref',
            event_type='checkout.session.completed',
            payment_id=payment_id,
            amount_cents=amount_cents,
            payment_status='unpaid',
            payment_intent='pi_pix_ref_test',
        )
        route_payment_webhook_event(event)

        ref = StripePaymentRef.objects.get(payment_intent_id='pi_pix_ref_test')
        self.assertEqual(ref.box_schema, TENANT_SCHEMA)
        self.assertEqual(ref.payment_id, payment_id)

    def test_async_payment_succeeded_reconciles(self):
        """Confirmação real do Pix chega depois — DEVE reconciliar."""
        payment_id, amount_cents = self._make_tenant_payment()

        # Passo 1: clique gera o Pix (unpaid, não reconcilia — replica o fluxo real).
        route_payment_webhook_event(_checkout_event(
            event_id='evt_pix_click',
            event_type='checkout.session.completed',
            payment_id=payment_id,
            amount_cents=amount_cents,
            payment_status='unpaid',
        ))
        with schema_context(TENANT_SCHEMA):
            self.assertEqual(Payment.objects.get(pk=payment_id).status, PaymentStatus.PENDING)

        # Passo 2: aluno paga o Pix no banco dele — Stripe confirma via async event.
        event = _checkout_event(
            event_id='evt_pix_paid',
            event_type='checkout.session.async_payment_succeeded',
            payment_id=payment_id,
            amount_cents=amount_cents,
            payment_status='paid',
        )
        route_payment_webhook_event(event)

        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.PROCESSED)
        with schema_context(TENANT_SCHEMA):
            payment = Payment.objects.get(pk=payment_id)
            self.assertEqual(payment.status, PaymentStatus.PAID)
            self.assertIsNotNone(payment.paid_at)

    def test_async_payment_failed_never_reconciles(self):
        """Pix expirado/falhou — Payment permanece PENDING para sempre (a
        menos que o aluno gere um novo checkout)."""
        payment_id, amount_cents = self._make_tenant_payment()

        route_payment_webhook_event(_checkout_event(
            event_id='evt_pix_click2',
            event_type='checkout.session.completed',
            payment_id=payment_id,
            amount_cents=amount_cents,
            payment_status='unpaid',
        ))

        event = _checkout_event(
            event_id='evt_pix_expired',
            event_type='checkout.session.async_payment_failed',
            payment_id=payment_id,
            amount_cents=amount_cents,
            payment_status='unpaid',
        )
        route_payment_webhook_event(event)

        event.refresh_from_db()
        self.assertEqual(
            event.status, PaymentWebhookStatus.PROCESSED,
            'Pix expirado nao e erro do sistema — evento processa normalmente, so nao reconcilia',
        )
        with schema_context(TENANT_SCHEMA):
            payment = Payment.objects.get(pk=payment_id)
            self.assertEqual(payment.status, PaymentStatus.PENDING)
            self.assertIsNone(payment.paid_at)

    def test_card_payment_still_reconciles_immediately(self):
        """Contraprova: cartao e sincrono, payment_status ja vem 'paid' no
        completed — comportamento anterior a esta onda continua intacto."""
        payment_id, amount_cents = self._make_tenant_payment()

        event = _checkout_event(
            event_id='evt_card_sync',
            event_type='checkout.session.completed',
            payment_id=payment_id,
            amount_cents=amount_cents,
            payment_status='paid',
        )
        route_payment_webhook_event(event)

        with schema_context(TENANT_SCHEMA):
            payment = Payment.objects.get(pk=payment_id)
            self.assertEqual(payment.status, PaymentStatus.PAID)
