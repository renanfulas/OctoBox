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

        first = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='giovanna')
        second = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='giovanna')

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(PublicWorkoutSubscription.objects.filter(account=account).count(), 1)

    def test_new_subscription_stores_the_given_tier(self):
        account = PublicWorkoutAccount.objects.create(email='aluno@example.com')

        subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.COMPLETO, plan_slug='giovanna')

        self.assertEqual(subscription.tier, PublicWorkoutTier.COMPLETO)

    def test_new_subscription_starts_pending_payment_never_active(self):
        # RT7/D.2b/ADR-7 (Entrega 5, Fase 2): antes desta fase, nada setava
        # status explicitamente — quem criava a linha ganhava o default
        # ACTIVE do model mesmo sem pagar. O webhook (stripe_handlers.py,
        # apos confirmar tier/price real na Stripe) e' o unico caminho que
        # promove pra ACTIVE agora.
        account = PublicWorkoutAccount.objects.create(email='aluno@example.com')

        subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='giovanna')

        self.assertEqual(subscription.status, PublicWorkoutSubscriptionStatus.PENDING_PAYMENT)

    def test_plan_slug_is_optional(self):
        # Cadastro a frio (D.2): a assinatura existe ANTES de ter slug —
        # quem atribui e' Renan/esposa, manualmente, na fila de ativacao.
        account = PublicWorkoutAccount.objects.create(email='aluno@example.com')

        subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL)

        self.assertIsNone(subscription.plan_slug)

    def test_second_call_ignores_new_defaults_when_subscription_already_exists(self):
        # Comportamento preexistente (docstring de get_or_create_subscription):
        # so os `defaults` da PRIMEIRA chamada valem.
        account = PublicWorkoutAccount.objects.create(email='aluno@example.com')
        first = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='giovanna')

        second = get_or_create_subscription(account=account, tier=PublicWorkoutTier.PREMIUM, plan_slug='outro-slug')

        self.assertEqual(second.pk, first.pk)
        self.assertEqual(second.tier, PublicWorkoutTier.ESSENCIAL)
        self.assertEqual(second.plan_slug, 'giovanna')


class LinkStripeIdsTests(TestCase):
    def test_sets_customer_and_subscription_id(self):
        account = PublicWorkoutAccount.objects.create(email='aluno@example.com')
        subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='giovanna')

        link_stripe_ids(subscription, customer_id='cus_123', stripe_subscription_id='sub_123')

        subscription.refresh_from_db()
        self.assertEqual(subscription.stripe_customer_id, 'cus_123')
        self.assertEqual(subscription.stripe_subscription_id, 'sub_123')


class RecordSuccessfulInvoicePaymentTests(TestCase):
    def setUp(self):
        account = PublicWorkoutAccount.objects.create(email='aluno@example.com')
        self.subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='giovanna')

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
        self.subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='giovanna')

    def _give_subscription_a_prior_successful_payment(self):
        # Torna a proxima falha NAO ser a primeira cobranca de verdade da
        # assinatura — precondicao pros testes de "renovacao recorrente
        # falhou" abaixo, que precisam da regua de 9 dias (diferente da
        # falha do trial, ver HandleFailedInvoicePaymentTrialTests).
        record_successful_invoice_payment(
            self.subscription, stripe_invoice_id='in_1_ok', gross_amount=Decimal('89.90'), due_date=date(2026, 2, 10)
        )

    def test_recurring_failure_creates_payment_with_full_notice_schedule(self):
        self._give_subscription_a_prior_successful_payment()

        payment = handle_failed_invoice_payment(
            self.subscription, stripe_invoice_id='in_2', gross_amount=Decimal('89.90'), due_date=date(2026, 3, 10)
        )

        self.assertEqual(payment.status, PublicWorkoutPaymentStatus.PENDING)
        self.assertEqual(PublicWorkoutPaymentNotice.objects.filter(payment=payment).count(), 5)

    def test_marks_active_subscription_as_past_due(self):
        # so' downgrade de ACTIVE (billing.py:323) — precondicao explicita
        # desde a Fase 2 (D.2b), ja que get_or_create_subscription nao
        # nasce mais ACTIVE por default.
        self.subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
        self.subscription.save(update_fields=['status'])

        handle_failed_invoice_payment(
            self.subscription, stripe_invoice_id='in_2', gross_amount=Decimal('89.90'), due_date=date(2026, 3, 10)
        )

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, PublicWorkoutSubscriptionStatus.PAST_DUE)

    def test_is_idempotent_by_invoice_id(self):
        self._give_subscription_a_prior_successful_payment()

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


class HandleFailedInvoicePaymentTrialTests(TestCase):
    """Decisao do Renan: cobranca de conversao do trial de 2 dias
    (PUBLIC_WORKOUT_TRIAL_PERIOD_DAYS, stripe_checkout.py) falhando NAO
    passa pela regua de 9 dias pensada pra lembrar quem ja e' cliente de
    verdade — bloqueia na hora (status sai de ACTIVE aqui, e o gate de
    acesso em student_app/views/public_workout_views.py exige ACTIVE)."""

    def setUp(self):
        account = PublicWorkoutAccount.objects.create(email='trial@example.com')
        self.subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='novoaluno')
        self.subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
        self.subscription.save(update_fields=['status'])

    def test_first_ever_failure_creates_no_notice_ladder(self):
        payment = handle_failed_invoice_payment(
            self.subscription, stripe_invoice_id='in_trial_1', gross_amount=Decimal('97.00'), due_date=date(2026, 3, 10)
        )

        self.assertEqual(PublicWorkoutPaymentNotice.objects.filter(payment=payment).count(), 0)

    def test_first_ever_failure_still_marks_past_due(self):
        # Acesso ja bloqueia (gate exige ACTIVE) mesmo sem a regua de
        # avisos — nao ha' "PAST_DUE mas ainda ve o treino" neste produto.
        handle_failed_invoice_payment(
            self.subscription, stripe_invoice_id='in_trial_1', gross_amount=Decimal('97.00'), due_date=date(2026, 3, 10)
        )

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, PublicWorkoutSubscriptionStatus.PAST_DUE)

    def test_first_ever_failure_event_reason_mentions_trial(self):
        from public_workouts.models import PublicWorkoutSubscriptionEvent

        handle_failed_invoice_payment(
            self.subscription, stripe_invoice_id='in_trial_1', gross_amount=Decimal('97.00'), due_date=date(2026, 3, 10)
        )

        event = PublicWorkoutSubscriptionEvent.objects.filter(subscription=self.subscription).latest('created_at')
        self.assertIn('trial', event.reason)

    def test_second_failed_invoice_for_same_subscription_is_no_longer_first_payment(self):
        # Depois que UM PublicWorkoutPayment ja existe (mesmo sem sucesso),
        # a proxima falha de um invoice DIFERENTE ja conta como renovacao
        # normal, com regua completa.
        handle_failed_invoice_payment(
            self.subscription, stripe_invoice_id='in_trial_1', gross_amount=Decimal('97.00'), due_date=date(2026, 3, 10)
        )
        self.subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
        self.subscription.save(update_fields=['status'])

        second_payment = handle_failed_invoice_payment(
            self.subscription, stripe_invoice_id='in_trial_2', gross_amount=Decimal('97.00'), due_date=date(2026, 4, 10)
        )

        self.assertEqual(PublicWorkoutPaymentNotice.objects.filter(payment=second_payment).count(), 5)


class MarkSubscriptionCanceledTests(TestCase):
    def setUp(self):
        account = PublicWorkoutAccount.objects.create(email='aluno@example.com')
        self.subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='giovanna')

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
