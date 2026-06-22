"""
ARQUIVO: testes da reconciliacao Stripe<->DB (rede de seguranca de fidelidade).

POR QUE EXISTE:
- Garante que divergencias entre o status local e o estado real na Stripe sao
  detectadas e registradas (audit) — ex.: estorno feito na Stripe que o webhook
  perdeu. Read-only: o job reporta, nao muta status.

@pytest.mark.public_schema: o job itera os boxes ativos a partir do public.
get_stripe_payment_state e mockado (sem chamadas reais a Stripe).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.test import TestCase
from django_tenants.utils import schema_context

from auditing.models import AuditEvent
from finance.models import PaymentStatus
from finance.reconciliation import reconcile_stripe_payments
from tests.factories import PaymentFactory

TENANT_SCHEMA = 'box_test'


@pytest.mark.public_schema
class StripeReconciliationTests(TestCase):
    def _paid_with_pi(self, payment_intent):
        with schema_context(TENANT_SCHEMA):
            payment = PaymentFactory(
                amount='149.90',
                status=PaymentStatus.PAID,
                stripe_payment_intent_id=payment_intent,
            )
            return payment.id

    @patch(
        'integrations.stripe.services.get_stripe_payment_state',
        return_value={'pi_status': 'succeeded', 'refunded': True, 'charge_id': 'ch_1'},
    )
    def test_detects_refund_drift_and_audits(self, _state):
        pid = self._paid_with_pi('pi_recon_drift')

        report = reconcile_stripe_payments(days=3650, limit=100)

        self.assertGreaterEqual(report['drift_count'], 1)
        entry = next(d for d in report['drift'] if d['payment_id'] == pid)
        self.assertEqual(entry['reason'], 'stripe_refunded_local_not')
        with schema_context(TENANT_SCHEMA):
            self.assertTrue(AuditEvent.objects.filter(action='payment_stripe_drift').exists())

    @patch(
        'integrations.stripe.services.get_stripe_payment_state',
        return_value={'pi_status': 'succeeded', 'refunded': False, 'charge_id': 'ch_2'},
    )
    def test_no_drift_when_consistent(self, _state):
        pid = self._paid_with_pi('pi_recon_ok')

        report = reconcile_stripe_payments(days=3650, limit=100)

        self.assertFalse(any(d['payment_id'] == pid for d in report['drift']))

    @patch('integrations.stripe.services.get_stripe_payment_state', return_value=None)
    def test_missing_stripe_state_is_skipped_not_drift(self, _state):
        pid = self._paid_with_pi('pi_recon_missing')

        report = reconcile_stripe_payments(days=3650, limit=100)

        self.assertGreaterEqual(report['checked'], 1)
        self.assertFalse(any(d['payment_id'] == pid for d in report['drift']))
