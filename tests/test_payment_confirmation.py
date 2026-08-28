"""
ARQUIVO: testes da confirmacao ao aluno na baixa do pagamento (T5).

POR QUE EXISTE:
- Garante que a baixa do pagamento dispara a confirmacao (e-mail real + WhatsApp
  como fundacao) sem nunca falhar o webhook, e que a segunda passagem do mesmo
  evento (already_paid) nao reconfirma.
- Garante tambem que a confirmacao NAO trava a resposta do webhook: o envio
  (SMTP/HTTP) roda em thread separada (run_in_background), entao os testes
  que verificam a chamada precisam esperar essa thread antes de assertar —
  mesmo padrao ja usado em tests/test_background_jobs_schema.py.
"""

from __future__ import annotations

import threading
import time
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import TestCase, override_settings
from django_tenants.utils import schema_context

from finance.models import PaymentStatus
from finance.payment_notifications import notify_payment_confirmed
from integrations.stripe.models import PaymentWebhookEvent
from integrations.stripe.router import route_payment_webhook_event
from student_identity.models import (
    StudentIdentity,
    StudentIdentityProvider,
    StudentIdentityStatus,
    StudentPushSubscription,
)
from tests.factories import PaymentFactory, StudentFactory

TENANT_SCHEMA = 'box_test'


def _create_push_subscription(*, student, box_root_slug=TENANT_SCHEMA, provider_subject='google-push-test'):
    identity = StudentIdentity.objects.create(
        student_id=student.id,
        box_root_slug=box_root_slug,
        primary_box_root_slug=box_root_slug,
        provider=StudentIdentityProvider.GOOGLE,
        provider_subject=provider_subject,
        email=student.email or 'aluno@example.com',
        status=StudentIdentityStatus.ACTIVE,
    )
    return StudentPushSubscription.objects.create(
        identity=identity,
        box_root_slug=box_root_slug,
        endpoint=f'https://push.example/test-endpoint-{provider_subject}',
        subscription={
            'endpoint': f'https://push.example/test-endpoint-{provider_subject}',
            'keys': {'p256dh': 'fake-p256dh', 'auth': 'fake-auth'},
        },
    )


def _route_and_join_background_threads(event, *, timeout=5.0):
    """route_payment_webhook_event despacha a confirmacao em thread daemon
    (run_in_background); sem juntar essa thread aqui, asserts logo em seguida
    correm risco de rodar antes dela terminar (flake, nao bug de produto)."""
    before = set(threading.enumerate())
    route_payment_webhook_event(event)
    for spawned in set(threading.enumerate()) - before:
        spawned.join(timeout=timeout)


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

    @patch('signup.email_sender.send_html_email')
    def test_push_skipped_without_subscription(self, _send_mock):
        student = StudentFactory(email='aluno@example.com')
        payment = PaymentFactory(student=student, status=PaymentStatus.PAID)

        result = notify_payment_confirmed(payment)

        self.assertEqual(result['push'], 'skipped')

    @patch('student_identity.push_notifications.send_student_web_push_notification', return_value=True)
    @patch('signup.email_sender.send_html_email')
    def test_push_sent_to_each_active_subscription(self, _send_mock, push_mock):
        student = StudentFactory(email='aluno@example.com')
        payment = PaymentFactory(student=student, amount='149.90', status=PaymentStatus.PAID)
        _create_push_subscription(student=student, provider_subject='device-1')
        _create_push_subscription(student=student, provider_subject='device-2')

        result = notify_payment_confirmed(payment)

        self.assertEqual(result['push'], 'sent')
        self.assertEqual(push_mock.call_count, 2)
        self.assertEqual(push_mock.call_args.kwargs['title'], 'Pagamento confirmado')
        self.assertIn('149,90', push_mock.call_args.kwargs['body'])

    @patch('student_identity.push_notifications.send_student_web_push_notification', return_value=False)
    @patch('signup.email_sender.send_html_email')
    def test_push_error_is_isolated(self, _send_mock, _push_mock):
        student = StudentFactory(email='aluno@example.com')
        payment = PaymentFactory(student=student, status=PaymentStatus.PAID)
        _create_push_subscription(student=student)

        result = notify_payment_confirmed(payment)  # nao deve propagar

        self.assertEqual(result['push'], 'error')
        self.assertEqual(result['email'], 'sent')


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

        _route_and_join_background_threads(
            self._event(event_id='evt_confirm', payment_id=pid, amount_cents=cents)
        )

        notify_mock.assert_called_once()

    @patch('finance.payment_notifications.notify_payment_confirmed')
    def test_already_paid_does_not_reconfirm(self, notify_mock):
        pid, cents = self._make_tenant_payment()

        route_payment_webhook_event(self._event(event_id='evt_c1', payment_id=pid, amount_cents=cents))
        notify_mock.reset_mock()
        route_payment_webhook_event(self._event(event_id='evt_c2', payment_id=pid, amount_cents=cents))

        notify_mock.assert_not_called()

    @patch('finance.payment_notifications.notify_payment_confirmed')
    def test_confirmation_does_not_block_webhook_response(self, notify_mock):
        """A confirmacao roda em thread separada — route_payment_webhook_event
        precisa retornar mesmo que o envio da notificacao esteja lento/travado.

        Sem isso, um provedor de e-mail lento prenderia a worker do gunicorn
        que atende ESTE endpoint para TODOS os boxes (webhook e compartilhado).
        """
        release_notify = threading.Event()

        def _slow_notify(payment):
            release_notify.wait(timeout=5.0)
            return {'email': 'sent', 'whatsapp': 'skipped'}

        notify_mock.side_effect = _slow_notify

        pid, cents = self._make_tenant_payment()
        event = self._event(event_id='evt_slow_confirm', payment_id=pid, amount_cents=cents)

        started_at = time.monotonic()
        route_payment_webhook_event(event)
        elapsed = time.monotonic() - started_at

        # notify_mock ainda esta bloqueado (release_notify nao foi setado) —
        # se route_payment_webhook_event tivesse retornado tao rapido por
        # OUTRO motivo (ex.: nao ter chamado a confirmacao), isso nao provaria
        # nada; garantimos que a chamada de fato aconteceu.
        self.assertLess(elapsed, 1.0, 'webhook esperou a notificacao terminar — voltou a ser sincrono')

        release_notify.set()
        for _ in range(50):
            if notify_mock.called:
                break
            time.sleep(0.05)
        notify_mock.assert_called_once()
