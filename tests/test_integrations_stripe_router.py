"""
ARQUIVO: testes do roteador de webhooks Stripe (integrations/stripe/router.py).

POR QUE EXISTE:
- router.py e o caminho do dinheiro: decide o que cada evento Stripe dispara
  (marca PendingSignup pago, suspende/reativa Box por inadimplencia, reconcilia
  pagamento de aluno). Bug silencioso aqui = cobranca errada ou box nao provisionado.
- Antes destes testes a cobertura do arquivo era ~23%.

ESCOPO:
- route_payment_webhook_event: dispatch, mark_processed, failure retryable/nao.
- _handle_checkout_session_completed: roteamento por metadata.
- _handle_early_adopter_signup / _handle_student_payment.
- _handle_invoice_payment_failed / _handle_invoice_payment_succeeded.
- _resolve_marketing_site_url.

@pytest.mark.public_schema: alguns testes criam Box (modelo tenant) — so em public.
PaymentWebhookEvent / PendingSignup / PlatformAuditEvent sao shared (acessiveis).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from integrations.stripe.models import PaymentWebhookEvent, PaymentWebhookStatus
from integrations.stripe.router import (
    _resolve_marketing_site_url,
    route_payment_webhook_event,
)


def _event(event_type, obj, *, event_id='evt_test'):
    return PaymentWebhookEvent.objects.create(
        event_id=event_id,
        event_type=event_type,
        payload={'id': event_id, 'type': event_type, 'data': {'object': obj}},
    )


@pytest.mark.public_schema
class RouteDispatchTests(TestCase):
    """route_payment_webhook_event: dispatch + marcacao de status."""

    def test_unknown_event_type_is_marked_processed(self):
        event = _event('charge.refunded', {})
        route_payment_webhook_event(event)
        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.PROCESSED)

    def test_successful_handler_marks_processed(self):
        # checkout sem metadata reconhecivel: handler roda, nao falha, processa.
        event = _event('checkout.session.completed', {'metadata': {}})
        route_payment_webhook_event(event)
        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.PROCESSED)

    def test_value_error_registers_non_retryable_failure(self):
        # pending_signup_id invalido faz _handle_early_adopter_signup levantar ValueError.
        event = _event(
            'checkout.session.completed',
            {'metadata': {'pending_signup_id': 'nao-e-int'}},
        )
        route_payment_webhook_event(event)
        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.FAILED)
        self.assertIn('pending_signup_id', event.last_error_message)

    @patch('signup.services.mark_pending_signup_paid', side_effect=RuntimeError('boom'))
    def test_unexpected_exception_registers_retryable_failure(self, _mock):
        # Erro generico (nao-ValueError) no meio do handler -> falha REPROCESSAVEL.
        # Patch em mark_pending_signup_paid (import tardio) porque _HANDLERS guarda a
        # referencia da funcao top-level e nao seria substituida por um patch nela.
        event = _event('checkout.session.completed', {'metadata': {'pending_signup_id': '7'}})
        route_payment_webhook_event(event)
        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.PENDING)
        self.assertEqual(event.attempts, 1)
        self.assertIsNotNone(event.next_retry_at)


@pytest.mark.public_schema
class CheckoutSessionRoutingTests(TestCase):
    """_handle_checkout_session_completed: escolhe o fluxo pela metadata."""

    def test_pending_signup_metadata_routes_to_early_adopter(self):
        event = _event(
            'checkout.session.completed',
            {'metadata': {'pending_signup_id': '7'}},
        )
        with patch('integrations.stripe.router._handle_early_adopter_signup') as early:
            route_payment_webhook_event(event)
        early.assert_called_once()

    def test_payment_id_metadata_routes_to_student_payment(self):
        event = _event(
            'checkout.session.completed',
            {'metadata': {'payment_id': '42'}},
        )
        with patch('integrations.stripe.router._handle_student_payment') as student:
            route_payment_webhook_event(event)
        student.assert_called_once()

    def test_unrecognized_metadata_is_noop_but_processed(self):
        event = _event('checkout.session.completed', {'metadata': {'foo': 'bar'}})
        route_payment_webhook_event(event)
        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.PROCESSED)


@pytest.mark.public_schema
class EarlyAdopterSignupTests(TestCase):
    """_handle_early_adopter_signup: marca PendingSignup pago + dispara email."""

    def _pending(self):
        from signup.models import PendingSignup
        return PendingSignup.objects.create(
            email='owner@box.test',
            full_name='Dona do Box',
            box_name='Box Teste',
        )

    def _session(self, pending_pk):
        return {
            'id': 'cs_test_1',
            'customer': 'cus_test_1',
            'subscription': 'sub_test_1',
            'metadata': {'pending_signup_id': str(pending_pk)},
        }

    @patch('signup.services.send_onboarding_email', return_value=True)
    def test_marks_pending_paid_and_sends_email(self, send_mock):
        from signup.models import PendingSignupStatus
        pending = self._pending()
        event = _event('checkout.session.completed', self._session(pending.pk))

        route_payment_webhook_event(event)

        pending.refresh_from_db()
        self.assertEqual(pending.status, PendingSignupStatus.PAID)
        self.assertEqual(pending.stripe_session_id, 'cs_test_1')
        self.assertEqual(pending.stripe_customer_id, 'cus_test_1')
        self.assertEqual(pending.stripe_subscription_id, 'sub_test_1')
        send_mock.assert_called_once()
        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.PROCESSED)

    @patch('signup.services.send_onboarding_email', return_value=False)
    def test_email_failure_does_not_fail_webhook(self, _send_mock):
        pending = self._pending()
        event = _event('checkout.session.completed', self._session(pending.pk))

        route_payment_webhook_event(event)

        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.PROCESSED)

    @patch('signup.services.send_onboarding_email')
    def test_missing_pending_is_noop(self, send_mock):
        # pending_signup_id que nao existe: mark_pending_signup_paid retorna None,
        # o handler retorna cedo e nao envia email.
        event = _event(
            'checkout.session.completed',
            {'metadata': {'pending_signup_id': '999999'}},
        )
        route_payment_webhook_event(event)
        send_mock.assert_not_called()
        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.PROCESSED)


@pytest.mark.public_schema
class StudentPaymentTests(TestCase):
    """_handle_student_payment: valida metadata e chama o use case de reconciliacao."""

    def test_incomplete_metadata_raises_and_fails(self):
        # falta version_locked e amount_total -> ValueError -> failure nao reprocessavel
        event = _event(
            'checkout.session.completed',
            {'metadata': {'payment_id': '10'}},
        )
        route_payment_webhook_event(event)
        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.FAILED)

    @patch('finance.application.use_cases.execute_reconcile_payment_use_case')
    def test_complete_metadata_executes_reconcile(self, reconcile_mock):
        event = _event(
            'checkout.session.completed',
            {
                'amount_total': 14990,
                'metadata': {'payment_id': '10', 'version_locked': '3'},
            },
        )
        route_payment_webhook_event(event)

        reconcile_mock.assert_called_once()
        command = reconcile_mock.call_args.args[0]
        self.assertEqual(command.payment_id, 10)
        self.assertEqual(command.amount_cents, 14990)
        self.assertEqual(command.version_locked, 3)
        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.PROCESSED)


@pytest.mark.public_schema
class InvoicePaymentFailedTests(TestCase):
    """_handle_invoice_payment_failed: suspende Box por inadimplencia."""

    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user('inv_owner', 'inv_owner@test.com')

    def _box(self, *, slug, sub='', cus='', status=None):
        from control.models import Box
        return Box.objects.create(
            slug=slug,
            schema_name=f'box_{slug}',
            display_name=slug,
            owner_user=self.owner,
            status=status or Box.Status.ACTIVE,
            stripe_subscription_id=sub,
            stripe_customer_id=cus,
        )

    def test_suspends_box_found_by_subscription(self):
        from control.models import Box, PlatformAuditEvent
        box = self._box(slug='inv-sub', sub='sub_die')
        event = _event('invoice.payment_failed', {'subscription': 'sub_die', 'customer': ''})

        route_payment_webhook_event(event)

        box.refresh_from_db()
        self.assertEqual(box.status, Box.Status.SUSPENDED)
        self.assertIsNotNone(box.suspended_at)
        self.assertTrue(
            PlatformAuditEvent.objects.filter(
                target_box=box, kind='box.suspended_payment_failed'
            ).exists()
        )

    def test_suspends_box_found_by_customer_when_no_subscription(self):
        from control.models import Box
        box = self._box(slug='inv-cus', cus='cus_die')
        event = _event('invoice.payment_failed', {'subscription': '', 'customer': 'cus_die'})

        route_payment_webhook_event(event)

        box.refresh_from_db()
        self.assertEqual(box.status, Box.Status.SUSPENDED)

    def test_no_subscription_no_customer_is_noop(self):
        event = _event('invoice.payment_failed', {'subscription': '', 'customer': ''})
        route_payment_webhook_event(event)
        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.PROCESSED)

    def test_unknown_box_is_noop(self):
        event = _event('invoice.payment_failed', {'subscription': 'sub_ghost', 'customer': ''})
        route_payment_webhook_event(event)
        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.PROCESSED)

    def test_already_suspended_box_is_noop(self):
        from control.models import Box, PlatformAuditEvent
        box = self._box(slug='inv-already', sub='sub_already', status=Box.Status.SUSPENDED)
        event = _event('invoice.payment_failed', {'subscription': 'sub_already', 'customer': ''})

        route_payment_webhook_event(event)

        box.refresh_from_db()
        self.assertEqual(box.status, Box.Status.SUSPENDED)
        # nao deve registrar novo evento de suspensao
        self.assertFalse(
            PlatformAuditEvent.objects.filter(
                target_box=box, kind='box.suspended_payment_failed'
            ).exists()
        )


@pytest.mark.public_schema
class InvoicePaymentSucceededTests(TestCase):
    """_handle_invoice_payment_succeeded: reativa Box suspenso (retry Stripe)."""

    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user('rec_owner', 'rec_owner@test.com')

    def _box(self, *, slug, sub='', status):
        from control.models import Box
        return Box.objects.create(
            slug=slug,
            schema_name=f'box_{slug}',
            display_name=slug,
            owner_user=self.owner,
            status=status,
            stripe_subscription_id=sub,
        )

    def test_reactivates_suspended_box(self):
        from control.models import Box, PlatformAuditEvent
        box = self._box(slug='rec-sus', sub='sub_back', status=Box.Status.SUSPENDED)
        event = _event('invoice.payment_succeeded', {'subscription': 'sub_back', 'customer': ''})

        route_payment_webhook_event(event)

        box.refresh_from_db()
        self.assertEqual(box.status, Box.Status.ACTIVE)
        self.assertIsNone(box.suspended_at)
        self.assertTrue(
            PlatformAuditEvent.objects.filter(
                target_box=box, kind='box.reactivated_payment_recovered'
            ).exists()
        )

    def test_active_box_is_noop(self):
        from control.models import Box
        box = self._box(slug='rec-active', sub='sub_active', status=Box.Status.ACTIVE)
        event = _event('invoice.payment_succeeded', {'subscription': 'sub_active', 'customer': ''})

        route_payment_webhook_event(event)

        box.refresh_from_db()
        self.assertEqual(box.status, Box.Status.ACTIVE)

    def test_reactivates_box_found_by_customer_when_no_subscription(self):
        from control.models import Box
        box = self._box(slug='rec-cus', status=Box.Status.SUSPENDED)
        Box.objects.filter(pk=box.pk).update(stripe_customer_id='cus_back')
        event = _event('invoice.payment_succeeded', {'subscription': '', 'customer': 'cus_back'})

        route_payment_webhook_event(event)

        box.refresh_from_db()
        self.assertEqual(box.status, Box.Status.ACTIVE)

    def test_unknown_box_is_noop(self):
        event = _event('invoice.payment_succeeded', {'subscription': 'sub_ghost', 'customer': ''})
        route_payment_webhook_event(event)
        event.refresh_from_db()
        self.assertEqual(event.status, PaymentWebhookStatus.PROCESSED)


class ResolveMarketingSiteUrlTests(TestCase):
    """_resolve_marketing_site_url: precedencia setting > CSRF origins > fallback."""

    @override_settings(MARKETING_SITE_URL='https://meusite.com.br/')
    def test_explicit_setting_wins(self):
        self.assertEqual(_resolve_marketing_site_url(), 'https://meusite.com.br')

    @override_settings(
        MARKETING_SITE_URL='',
        CSRF_TRUSTED_ORIGINS=['https://app.octoboxfit.com.br', 'https://octoboxfit.com.br'],
    )
    def test_falls_back_to_non_app_octoboxfit_origin(self):
        self.assertEqual(_resolve_marketing_site_url(), 'https://octoboxfit.com.br')

    @override_settings(MARKETING_SITE_URL='', CSRF_TRUSTED_ORIGINS=[])
    def test_hardcoded_fallback(self):
        self.assertEqual(_resolve_marketing_site_url(), 'https://octoboxfit.com.br')
