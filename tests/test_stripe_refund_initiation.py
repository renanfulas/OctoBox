"""
ARQUIVO: testes do estorno real iniciado pelo staff (F6).

POR QUE EXISTE:
- Antes, refund-payment so mudava o status no banco — o operador achava que tinha
  devolvido o dinheiro, mas nada era estornado na Stripe. Agora, pagamento pago
  via Stripe dispara a API de refund; pagamento manual (PIX/dinheiro) segue so a
  baixa local. Falha do gateway nao pode deixar o pagamento "estornado" sem grana.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import stripe
from django.test import SimpleTestCase, TestCase

from catalog.services.student_payment_actions import handle_student_payment_action
from finance.models import PaymentStatus
from integrations.stripe.services import refund_payment
from tests.factories import PaymentFactory, StudentFactory, UserFactory


class RefundPaymentServiceTests(SimpleTestCase):
    @patch('integrations.stripe.services.log_audit_event')
    @patch('integrations.stripe.services.stripe.Refund.create')
    def test_refund_uses_payment_intent_and_idempotency_key(self, refund_mock, _audit):
        refund_mock.return_value = SimpleNamespace(id='re_test_1')
        payment = SimpleNamespace(id=31, version=5, stripe_payment_intent_id='pi_x', stripe_charge_id='')

        refund_id = refund_payment(payment)

        self.assertEqual(refund_id, 're_test_1')
        kwargs = refund_mock.call_args.kwargs
        self.assertEqual(kwargs['payment_intent'], 'pi_x')
        self.assertEqual(kwargs['idempotency_key'], 'octobox_refund_pay_31_v5')

    @patch('integrations.stripe.services.log_audit_event')
    @patch('integrations.stripe.services.stripe.Refund.create')
    def test_refund_falls_back_to_charge_when_no_payment_intent(self, refund_mock, _audit):
        refund_mock.return_value = SimpleNamespace(id='re_test_2')
        payment = SimpleNamespace(id=7, version=0, stripe_payment_intent_id='', stripe_charge_id='ch_y')

        refund_payment(payment)

        kwargs = refund_mock.call_args.kwargs
        self.assertEqual(kwargs['charge'], 'ch_y')
        self.assertNotIn('payment_intent', kwargs)

    def test_refund_without_stripe_link_raises_value_error(self):
        payment = SimpleNamespace(id=1, version=0, stripe_payment_intent_id='', stripe_charge_id='')
        with self.assertRaises(ValueError):
            refund_payment(payment)

    @patch('integrations.stripe.services.log_audit_event')
    @patch('integrations.stripe.services.stripe.Refund.create', side_effect=stripe.StripeError('boom'))
    def test_refund_wraps_stripe_error_as_runtime_error(self, _refund_mock, _audit):
        payment = SimpleNamespace(id=2, version=0, stripe_payment_intent_id='pi_y', stripe_charge_id='')
        with self.assertRaises(RuntimeError):
            refund_payment(payment)


class HandleRefundActionTests(TestCase):
    @patch('integrations.stripe.services.refund_payment')
    def test_stripe_backed_refund_calls_gateway_and_marks_refunded(self, refund_mock):
        student = StudentFactory()
        payment = PaymentFactory(
            student=student, status=PaymentStatus.PAID, stripe_payment_intent_id='pi_z'
        )
        actor = UserFactory(username='refund-owner')

        handle_student_payment_action(
            actor=actor, student=student, payment=payment, action='refund-payment'
        )

        refund_mock.assert_called_once()
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.REFUNDED)

    @patch('integrations.stripe.services.refund_payment')
    def test_manual_refund_does_not_call_gateway(self, refund_mock):
        student = StudentFactory()
        payment = PaymentFactory(student=student, status=PaymentStatus.PAID)  # sem vinculo Stripe
        actor = UserFactory(username='refund-owner-manual')

        handle_student_payment_action(
            actor=actor, student=student, payment=payment, action='refund-payment'
        )

        refund_mock.assert_not_called()
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.REFUNDED)
