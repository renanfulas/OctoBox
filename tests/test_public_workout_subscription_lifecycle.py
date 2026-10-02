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

from django.core import mail
from django.test import TestCase, override_settings

from public_workouts.billing import (
    get_or_create_subscription,
    handle_failed_invoice_payment,
    link_stripe_ids,
    mark_subscription_canceled,
    record_successful_invoice_payment,
)
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutOutboxMessage,
    PublicWorkoutOutboxStatus,
    PublicWorkoutPaymentNotice,
    PublicWorkoutPaymentStatus,
    PublicWorkoutSubscription,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTier,
)
from public_workouts.notifications import notify_staff_new_subscription
from public_workouts.outbox import (
    TOPIC_CLIENT_SUBSCRIPTION_ACTIVE,
    TOPIC_CLIENT_SUBSCRIPTION_CANCELED,
    TOPIC_STAFF_NEW_SUBSCRIPTION,
    drain_public_workout_outbox,
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

    def test_pending_checkout_uses_the_customers_latest_tier_choice(self):
        account = PublicWorkoutAccount.objects.create(email='aluno@example.com')
        first = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='giovanna')

        second = get_or_create_subscription(account=account, tier=PublicWorkoutTier.PREMIUM, plan_slug='outro-slug')

        self.assertEqual(second.pk, first.pk)
        self.assertEqual(second.tier, PublicWorkoutTier.PREMIUM)
        self.assertEqual(second.plan_slug, 'giovanna')

    def test_active_subscription_never_changes_tier_from_landing_selection(self):
        account = PublicWorkoutAccount.objects.create(email='ativo@example.com')
        subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL)
        subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
        subscription.save(update_fields=['status'])

        same = get_or_create_subscription(account=account, tier=PublicWorkoutTier.PREMIUM)

        self.assertEqual(same.tier, PublicWorkoutTier.ESSENCIAL)

    def test_canceled_subscription_can_start_a_new_checkout_on_same_account(self):
        account = PublicWorkoutAccount.objects.create(email='volta@example.com')
        subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL)
        subscription.status = PublicWorkoutSubscriptionStatus.CANCELED
        subscription.stripe_subscription_id = 'sub_cancelada'
        subscription.save(update_fields=['status', 'stripe_subscription_id'])

        resumed = get_or_create_subscription(account=account, tier=PublicWorkoutTier.COMPLETO)

        self.assertEqual(resumed.pk, subscription.pk)
        self.assertEqual(resumed.status, PublicWorkoutSubscriptionStatus.PENDING_PAYMENT)
        self.assertEqual(resumed.tier, PublicWorkoutTier.COMPLETO)
        self.assertEqual(resumed.stripe_subscription_id, '')


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

    @override_settings(PUBLIC_WORKOUT_STAFF_ALERT_EMAILS=['renan@example.com', 'giovanna@example.com'])
    def test_activation_enqueues_a_staff_alert_without_sending_synchronously(self):
        # Isto roda dentro do request/response do webhook da Stripe
        # (stripe_handlers.py) — nao pode chamar o gateway de e-mail direto
        # aqui, ou uma falha/lentidao do provedor atrasaria (ou arriscaria
        # travar) a confirmacao do pagamento pra Stripe.
        record_successful_invoice_payment(
            self.subscription, stripe_invoice_id='in_1', gross_amount=Decimal('97.00'), due_date=date(2026, 3, 10)
        )

        self.assertEqual(len(mail.outbox), 0)
        message = PublicWorkoutOutboxMessage.objects.get(topic=TOPIC_STAFF_NEW_SUBSCRIPTION)
        self.assertEqual(message.status, PublicWorkoutOutboxStatus.PENDING)

        drain_public_workout_outbox()

        sent_to = [recipient for msg in mail.outbox for recipient in msg.to]
        self.assertEqual(sent_to, ['renan@example.com', 'giovanna@example.com'])

    @override_settings(PUBLIC_WORKOUT_STAFF_ALERT_EMAILS=['renan@example.com'])
    def test_alerts_staff_again_on_reactivation_after_suspension(self):
        self.subscription.status = PublicWorkoutSubscriptionStatus.SUSPENDED
        self.subscription.save(update_fields=['status'])

        record_successful_invoice_payment(
            self.subscription, stripe_invoice_id='in_1', gross_amount=Decimal('97.00'), due_date=date(2026, 3, 10)
        )
        drain_public_workout_outbox()

        self.assertEqual(len(mail.outbox), 1)

    @override_settings(PUBLIC_WORKOUT_STAFF_ALERT_EMAILS=['renan@example.com'])
    def test_does_not_alert_staff_again_on_a_recurring_renewal(self):
        # So a transicao pra ACTIVE avisa a equipe — renovacao mensal normal
        # (assinatura ja ACTIVE) nao pode inundar a caixa de entrada.
        self.subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
        self.subscription.save(update_fields=['status'])

        record_successful_invoice_payment(
            self.subscription, stripe_invoice_id='in_2', gross_amount=Decimal('97.00'), due_date=date(2026, 4, 10)
        )

        self.assertEqual(PublicWorkoutOutboxMessage.objects.filter(topic=TOPIC_STAFF_NEW_SUBSCRIPTION).count(), 0)
        drain_public_workout_outbox()
        self.assertEqual(len(mail.outbox), 0)

        self.assertEqual(len(mail.outbox), 0)

    @override_settings(PUBLIC_WORKOUT_PUBLIC_BASE_URL='https://app.example.com')
    def test_activation_enqueues_a_welcome_email_to_the_client(self):
        record_successful_invoice_payment(
            self.subscription, stripe_invoice_id='in_1', gross_amount=Decimal('97.00'), due_date=date(2026, 3, 10)
        )

        self.assertEqual(PublicWorkoutOutboxMessage.objects.filter(topic=TOPIC_CLIENT_SUBSCRIPTION_ACTIVE).count(), 1)
        drain_public_workout_outbox()

        client_messages = [msg for msg in mail.outbox if 'aluno@example.com' in msg.to]
        self.assertEqual(len(client_messages), 1)
        self.assertIn('Bem-vinda', client_messages[0].subject)

    @override_settings(PUBLIC_WORKOUT_PUBLIC_BASE_URL='https://app.example.com')
    def test_reactivation_sends_a_different_subject_to_the_client(self):
        self.subscription.status = PublicWorkoutSubscriptionStatus.SUSPENDED
        self.subscription.save(update_fields=['status'])

        record_successful_invoice_payment(
            self.subscription, stripe_invoice_id='in_1', gross_amount=Decimal('97.00'), due_date=date(2026, 3, 10)
        )
        drain_public_workout_outbox()

        client_messages = [msg for msg in mail.outbox if 'aluno@example.com' in msg.to]
        self.assertEqual(len(client_messages), 1)
        self.assertIn('reativado', client_messages[0].subject)

    def test_client_welcome_email_is_skipped_without_base_url_but_staff_still_hears(self):
        # Link de anamnese e' o UNICO conteudo acionavel do e-mail do
        # cliente — sem PUBLIC_WORKOUT_PUBLIC_BASE_URL nao ha como montar
        # ele, entao o envio fica retido na fila (nunca manda incompleto).
        # O aviso de staff e' independente dessa config (degrada sozinho).
        record_successful_invoice_payment(
            self.subscription, stripe_invoice_id='in_1', gross_amount=Decimal('97.00'), due_date=date(2026, 3, 10)
        )
        drain_public_workout_outbox()

        client_messages = [msg for msg in mail.outbox if 'aluno@example.com' in msg.to]
        self.assertEqual(client_messages, [])
        client_message_row = PublicWorkoutOutboxMessage.objects.get(topic=TOPIC_CLIENT_SUBSCRIPTION_ACTIVE)
        self.assertNotEqual(client_message_row.status, PublicWorkoutOutboxStatus.SENT)


class NotifyStaffNewSubscriptionAmountTests(TestCase):
    """notify_staff_new_subscription chamado direto (nao via o fluxo
    completo de billing) — cobre o valor no assunto/HTML do aviso (pedido
    original: "coloque no titulo o valor da assinatura") e o fallback pra
    custom_monthly_price quando ainda nao existe PublicWorkoutPayment PAID
    (ex.: ativacao manual, seed_legacy_workout_accounts)."""

    @override_settings(PUBLIC_WORKOUT_STAFF_ALERT_EMAILS=['renan@example.com'])
    def test_subject_and_html_include_the_amount_actually_charged(self):
        account = PublicWorkoutAccount.objects.create(email='aluno@example.com')
        subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='giovanna')
        record_successful_invoice_payment(
            subscription, stripe_invoice_id='in_1', gross_amount=Decimal('97.00'), due_date=date(2026, 3, 10),
        )

        notify_staff_new_subscription(subscription, previous_status=PublicWorkoutSubscriptionStatus.PENDING_PAYMENT)

        message = mail.outbox[-1]
        self.assertIn('R$97,00', message.subject)
        html_body = message.alternatives[0][0]
        self.assertIn('R$97,00', html_body)

    @override_settings(PUBLIC_WORKOUT_STAFF_ALERT_EMAILS=['renan@example.com'])
    def test_falls_back_to_custom_monthly_price_without_a_paid_payment_yet(self):
        account = PublicWorkoutAccount.objects.create(email='legado@example.com')
        subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='milene')
        subscription.custom_monthly_price = Decimal('150.00')
        subscription.save(update_fields=['custom_monthly_price'])

        notify_staff_new_subscription(subscription, previous_status=PublicWorkoutSubscriptionStatus.PENDING_PAYMENT)

        self.assertIn('R$150,00', mail.outbox[-1].subject)

    @override_settings(PUBLIC_WORKOUT_STAFF_ALERT_EMAILS=['renan@example.com'])
    def test_omits_the_amount_segment_when_none_is_known_yet(self):
        # Sem pagamento PAID e sem custom_monthly_price: nao pode quebrar
        # nem mandar "R$ " vazio/None no assunto.
        account = PublicWorkoutAccount.objects.create(email='sempagamento@example.com')
        subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='henrique')

        notify_staff_new_subscription(subscription, previous_status=PublicWorkoutSubscriptionStatus.PENDING_PAYMENT)

        subject = mail.outbox[-1].subject
        self.assertNotIn('R$', subject)
        self.assertIn('Essencial', subject)


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


class HandleFailedFirstInvoicePaymentTests(TestCase):
    """Primeira cobranca imediata falhando NAO
    passa pela regua de 9 dias pensada pra lembrar quem ja e' cliente de
    verdade — bloqueia na hora (status sai de ACTIVE aqui, e o gate de
    acesso em student_app/views/public_workout_views.py exige ACTIVE)."""

    def setUp(self):
        account = PublicWorkoutAccount.objects.create(email='first-charge@example.com')
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

    def test_first_ever_failure_event_reason_mentions_first_charge(self):
        from public_workouts.models import PublicWorkoutSubscriptionEvent

        handle_failed_invoice_payment(
            self.subscription, stripe_invoice_id='in_trial_1', gross_amount=Decimal('97.00'), due_date=date(2026, 3, 10)
        )

        event = PublicWorkoutSubscriptionEvent.objects.filter(subscription=self.subscription).latest('created_at')
        self.assertIn('primeira cobranca', event.reason)

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

    def test_enqueues_a_confirmation_email_to_the_client(self):
        mark_subscription_canceled(self.subscription, reason='teste')

        self.assertEqual(
            PublicWorkoutOutboxMessage.objects.filter(topic=TOPIC_CLIENT_SUBSCRIPTION_CANCELED).count(), 1,
        )
        drain_public_workout_outbox()

        client_messages = [msg for msg in mail.outbox if 'aluno@example.com' in msg.to]
        self.assertEqual(len(client_messages), 1)
        self.assertIn('cancelada', client_messages[0].subject)

    def test_cancellation_email_still_sends_without_base_url(self):
        # Diferente do aviso de ativacao: confirmar o cancelamento nao
        # depende de link nenhum, entao essa config faltando so' tira o
        # CTA de reativar, nunca impede o envio.
        mark_subscription_canceled(self.subscription, reason='teste')
        drain_public_workout_outbox()

        client_messages = [msg for msg in mail.outbox if 'aluno@example.com' in msg.to]
        self.assertEqual(len(client_messages), 1)
        self.assertNotIn('curva-precos', client_messages[0].body)

    def test_idempotent_cancellation_does_not_enqueue_a_second_email(self):
        mark_subscription_canceled(self.subscription, reason='primeira vez')
        mark_subscription_canceled(self.subscription, reason='segunda vez')

        self.assertEqual(
            PublicWorkoutOutboxMessage.objects.filter(topic=TOPIC_CLIENT_SUBSCRIPTION_CANCELED).count(), 1,
        )
