"""
ARQUIVO: testes da confirmacao ao aluno na baixa do pagamento (T5).

POR QUE EXISTE:
- Garante que a baixa do pagamento dispara a confirmacao (e-mail real + WhatsApp
  como fundacao) sem nunca falhar o webhook, e que a segunda passagem do mesmo
  evento (already_paid) nao reconfirma.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import TestCase, override_settings
from django_tenants.utils import schema_context

from finance.models import PaymentStatus
from finance.payment_notifications import notify_payment_confirmed
from integrations.stripe.models import PaymentWebhookEvent
from integrations.stripe.router import route_payment_webhook_event
from tests.factories import PaymentFactory, StudentFactory

TENANT_SCHEMA = 'box_test'


class PaymentConfirmationServiceTests(TestCase):
    @patch('signup.email_sender.send_html_email')
    def test_email_sent_when_student_has_email(self, send_mock):
        student = StudentFactory(email='aluno@example.com')
        payment = PaymentFactory(student=student, amount='149.90', status=PaymentStatus.PAID)

        result = notify_payment_confirmed(payment)

        self.assertEqual(result['email'], 'sent')
        self.assertEqual(send_mock.call_args.kwargs['to_email'], 'aluno@example.com')
        # WhatsApp e fundacao: desativado por padrao (flag off).
        self.assertEqual(result['whatsapp'], 'disabled')

    @patch('signup.email_sender.send_html_email')
    def test_email_skipped_without_email(self, send_mock):
        student = StudentFactory(email='')
        payment = PaymentFactory(student=student, status=PaymentStatus.PAID)

        result = notify_payment_confirmed(payment)

        self.assertEqual(result['email'], 'skipped')
        send_mock.assert_not_called()

    @patch('signup.email_sender.send_html_email', side_effect=RuntimeError('smtp down'))
    def test_email_error_is_isolated(self, _send_mock):
        student = StudentFactory(email='aluno@example.com')
        payment = PaymentFactory(student=student, status=PaymentStatus.PAID)

        result = notify_payment_confirmed(payment)  # nao deve propagar

        self.assertEqual(result['email'], 'error')

    @override_settings(PAYMENT_WHATSAPP_CONFIRMATION_ENABLED=True)
    @patch('signup.email_sender.send_html_email')
    def test_whatsapp_foundation_when_flag_on_is_not_implemented(self, _send_mock):
        student = StudentFactory(email='aluno@example.com')
        payment = PaymentFactory(student=student, status=PaymentStatus.PAID)

        result = notify_payment_confirmed(payment)

        self.assertEqual(result['whatsapp'], 'not_implemented')


@pytest.mark.public_schema
class PaymentConfirmationOnReconcileTests(TestCase):
    def _make_tenant_payment(self, amount='149.90'):
        with schema_context(TENANT_SCHEMA):
            student = StudentFactory(email='aluno@example.com')
            payment = PaymentFactory(student=student, amount=amount, status=PaymentStatus.PENDING)
            return payment.id, int(Decimal(amount) * 100)

    def _event(self, *, event_id, payment_id, amount_cents, payment_status='paid'):
        return PaymentWebhookEvent.objects.create(
            event_id=event_id,
            event_type='checkout.session.completed',
            payload={
                'id': event_id,
                'type': 'checkout.session.completed',
                'data': {'object': {
                    'amount_total': amount_cents,
                    'payment_intent': 'pi_confirm',
                    # Onda 3: payment_status='paid' — cartao confirma na hora,
                    # e e o que o payload real da Stripe sempre traz nesse
                    # caso. Pix (delayed-notification) chegaria 'unpaid' aqui
                    # e so reconciliaria depois, via async_payment_succeeded
                    # — ver test_stripe_pix_async_confirmation.py.
                    'payment_status': payment_status,
                    'metadata': {
                        'payment_id': str(payment_id),
                        'version_locked': '0',
                        'box_schema': TENANT_SCHEMA,
                    },
                }},
            },
        )

    @patch('finance.payment_notifications.notify_payment_confirmed')
    def test_reconcile_triggers_confirmation(self, notify_mock):
        pid, cents = self._make_tenant_payment()

        route_payment_webhook_event(self._event(event_id='evt_confirm', payment_id=pid, amount_cents=cents))

        notify_mock.assert_called_once()

    @patch('finance.payment_notifications.notify_payment_confirmed')
    def test_already_paid_does_not_reconfirm(self, notify_mock):
        pid, cents = self._make_tenant_payment()

        route_payment_webhook_event(self._event(event_id='evt_c1', payment_id=pid, amount_cents=cents))
        notify_mock.reset_mock()
        route_payment_webhook_event(self._event(event_id='evt_c2', payment_id=pid, amount_cents=cents))

        notify_mock.assert_not_called()
