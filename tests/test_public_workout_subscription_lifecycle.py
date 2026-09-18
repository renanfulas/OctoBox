"""
ARQUIVO: testes do ciclo de vida da assinatura do corredor via Stripe
(Onda B2, Fatia B do CORDA).

POR QUE ELE EXISTE:
- P3 (aluno travado tendo pago) e P4 (aluno pago que nao destrava) sao os
  dois piores bugs silenciosos de cobranca — o pagamento pode confirmar
  DEPOIS da trava de D+2, e e o webhook (nao so a reconciliacao periodica)
  que precisa devolver o acesso.
- P6 (assinatura duplicada): duplo clique em "assinar" nao pode criar duas
  PublicWorkoutSubscription pra mesma conta.
- Cobranca bem-sucedida nunca passa pela regua de avisos — so a que falhou.
  Sem teste disso, um refactor futuro podia fazer todo ciclo (inclusive o
  que deu certo) mandar e-mail de aviso pro aluno.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.test import TestCase

from public_workouts.billing import (
    get_or_create_subscription,
    handle_failed_invoice_payment,
    link_stripe_ids,
    mark_subscription_canceled,
    record_successful_invoice_payment,
)
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutPaymentNotice,
    PublicWorkoutPaymentStatus,
    PublicWorkoutSubscription,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTier,
)


class GetOrCreateSubscriptionTests(TestCase):
    def test_second_call_returns_same_row_never_creates_a_second_one(self):
        account = PublicWorkoutAccount.objects.create(email='aluno@example.com')

        first = get_or_create_subscription(account=account, plan_slug='giovanna')
        second = get_or_create_subscription(account=account, plan_slug='giovanna')

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(PublicWorkoutSubscription.objects.filter(account=account).count(), 1)

    def test_new_subscription_defaults_to_essencial_tier(self):
        # Fase 1 (tier plumbing): a migration nao muda quem ja existe, e
        # quem nasce sem tier explicito continua ESSENCIAL — mesmo Price ID
        # de sempre pros 10 alunos legados, nenhuma regressao visivel.
        account = PublicWorkoutAccount.objects.create(email='aluno@example.com')

        subscription = get_or_create_subscription(account=account, plan_slug='giovanna')

        self.assertEqual(subscription.tier, PublicWorkoutTier.ESSENCIAL)


class LinkStripeIdsTests(TestCase):
    def test_sets_customer_and_subscription_id(self):
        account = PublicWorkoutAccount.objects.create(email='aluno@example.com')
        subscription = get_or_create_subscription(account=account, plan_slug='giovanna')

        link_stripe_ids(subscription, customer_id='cus_123', stripe_subscription_id='sub_123')

        subscription.refresh_from_db()
        self.assertEqual(subscription.stripe_customer_id, 'cus_123')
        self.assertEqual(subscription.stripe_subscription_id, 'sub_123')


class RecordSuccessfulInvoicePaymentTests(TestCase):
    def setUp(self):
        account = PublicWorkoutAccount.objects.create(email='aluno@example.com')
        self.subscription = get_or_create_subscription(account=account, plan_slug='giovanna')

    def test_creates_paid_payment_with_zero_application_fee(self):
        payment = record_successful_invoice_payment(
            self.subscription, stripe_invoice_id='in_1', gross_amount=Decimal('89.90'), due_date=date(2026, 3, 10)
        )

        self.assertEqual(payment.status, PublicWorkoutPaymentStatus.PAID)
        self.assertIsNotNone(payment.paid_at)
        # Sem Connect Express (C5): gross == net, fee sempre 0.
        self.assertEqual(payment.net_amount, Decimal('89.90'))
        self.assertEqual(payment.application_fee_amount, Decimal('0'))

    def test_is_idempotent_by_invoice_id(self):
        record_successful_invoice_payment(
            self.subscription, stripe_invoice_id='in_1', gross_amount=Decimal('89.90'), due_date=date(2026, 3, 10)
        )
        record_successful_invoice_payment(
            self.subscription, stripe_invoice_id='in_1', gross_amount=Decimal('89.90'), due_date=date(2026, 3, 10)
        )

        self.assertEqual(self.subscription.payments.filter(stripe_invoice_id='in_1').count(), 1)

    def test_never_schedules_notice_reminders_for_a_successful_cycle(self):
        payment = record_successful_invoice_payment(
            self.subscription, stripe_invoice_id='in_1', gross_amount=Decimal('89.90'), due_date=date(2026, 3, 10)
        )
        self.assertEqual(PublicWorkoutPaymentNotice.objects.filter(payment=payment).count(), 0)

    def test_reactivates_a_suspended_subscription(self):
        # P4 do CORDA: o pagamento pode confirmar DEPOIS da trava de D+2 —
        # e o webhook, nao so a reconciliacao periodica, que devolve o acesso.
        self.subscription.status = PublicWorkoutSubscriptionStatus.SUSPENDED
        self.subscription.save(update_fields=['status'])

        record_successful_invoice_payment(
            self.subscription, stripe_invoice_id='in_1', gross_amount=Decimal('89.90'), due_date=date(2026, 3, 10)
        )

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, PublicWorkoutSubscriptionStatus.ACTIVE)


class HandleFailedInvoicePaymentTests(TestCase):
    def setUp(self):
        account = PublicWorkoutAccount.objects.create(email='aluno@example.com')
        self.subscription = get_or_create_subscription(account=account, plan_slug='giovanna')

    def test_creates_payment_with_full_notice_schedule(self):
        payment = handle_failed_invoice_payment(
            self.subscription, stripe_invoice_id='in_2', gross_amount=Decimal('89.90'), due_date=date(2026, 3, 10)
        )

        self.assertEqual(payment.status, PublicWorkoutPaymentStatus.PENDING)
        self.assertEqual(PublicWorkoutPaymentNotice.objects.filter(payment=payment).count(), 5)

    def test_marks_active_subscription_as_past_due(self):
        handle_failed_invoice_payment(
            self.subscription, stripe_invoice_id='in_2', gross_amount=Decimal('89.90'), due_date=date(2026, 3, 10)
        )

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, PublicWorkoutSubscriptionStatus.PAST_DUE)

    def test_is_idempotent_by_invoice_id(self):
        handle_failed_invoice_payment(
            self.subscription, stripe_invoice_id='in_2', gross_amount=Decimal('89.90'), due_date=date(2026, 3, 10)
        )
        handle_failed_invoice_payment(
            self.subscription, stripe_invoice_id='in_2', gross_amount=Decimal('89.90'), due_date=date(2026, 3, 10)
        )

        self.assertEqual(self.subscription.payments.filter(stripe_invoice_id='in_2').count(), 1)
        self.assertEqual(PublicWorkoutPaymentNotice.objects.filter(payment__subscription=self.subscription).count(), 5)

    def test_does_not_downgrade_a_subscription_that_is_not_active(self):
        self.subscription.status = PublicWorkoutSubscriptionStatus.SUSPENDED
        self.subscription.save(update_fields=['status'])

        handle_failed_invoice_payment(
            self.subscription, stripe_invoice_id='in_2', gross_amount=Decimal('89.90'), due_date=date(2026, 3, 10)
        )

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, PublicWorkoutSubscriptionStatus.SUSPENDED)


class MarkSubscriptionCanceledTests(TestCase):
    def setUp(self):
        account = PublicWorkoutAccount.objects.create(email='aluno@example.com')
        self.subscription = get_or_create_subscription(account=account, plan_slug='giovanna')

    def test_sets_status_and_canceled_at(self):
        changed = mark_subscription_canceled(self.subscription, reason='teste')

        self.assertTrue(changed)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, PublicWorkoutSubscriptionStatus.CANCELED)
        self.assertIsNotNone(self.subscription.canceled_at)

    def test_is_idempotent(self):
        mark_subscription_canceled(self.subscription, reason='primeira vez')
        changed_again = mark_subscription_canceled(self.subscription, reason='segunda vez')

        self.assertFalse(changed_again)
