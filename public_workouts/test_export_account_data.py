"""
ARQUIVO: testes de export_account_data (Onda A3 — export de dados do
titular, LGPD/GDPR, docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- prova o escopo deliberado do export: inclui o que e' dado PESSOAL do
  titular (conta, assinatura, cobranca que ele pagou, avaliacoes, carga)
  e exclui o que e' conteudo autoral do personal (payload do programa) ou
  operacional do servico (IDs internos da Stripe, split de receita).
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from django.test import TestCase

from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutPayment,
    PublicWorkoutPaymentStatus,
    PublicWorkoutSubscription,
)
from public_workouts.services import export_account_data, record_assessment, record_load


def _make_account(email='atleta@example.com') -> PublicWorkoutAccount:
    return PublicWorkoutAccount.objects.create(email=email)


class ExportAccountDataTests(TestCase):
    def test_account_without_subscription_has_empty_billing_and_assessments(self):
        account = _make_account()

        data = export_account_data(account_id=account.pk)

        self.assertEqual(data['account']['email'], 'atleta@example.com')
        self.assertIsNone(data['subscription'])
        self.assertEqual(data['payments'], [])
        self.assertEqual(data['assessments'], [])
        self.assertEqual(data['load_history'], [])

    def test_includes_subscription_fields(self):
        account = _make_account()
        PublicWorkoutSubscription.objects.create(account=account, plan_slug='bruno')

        data = export_account_data(account_id=account.pk)

        self.assertEqual(data['subscription']['plan_slug'], 'bruno')
        self.assertEqual(data['subscription']['status'], 'active')

    def test_includes_payments_the_titular_was_charged_without_internal_stripe_ids(self):
        account = _make_account()
        subscription = PublicWorkoutSubscription.objects.create(account=account, plan_slug='bruno')
        PublicWorkoutPayment.objects.create(
            subscription=subscription,
            due_date=date(2026, 1, 5),
            paid_at=datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc),
            gross_amount=Decimal('199.90'),
            net_amount=Decimal('179.90'),
            status=PublicWorkoutPaymentStatus.PAID,
            stripe_invoice_id='in_123',
            stripe_payment_intent_id='pi_123',
            stripe_charge_id='ch_123',
        )

        data = export_account_data(account_id=account.pk)

        self.assertEqual(len(data['payments']), 1)
        payment = data['payments'][0]
        self.assertEqual(payment['amount'], 199.90)
        self.assertEqual(payment['status'], 'paid')
        # escopo deliberado: nada de IDs internos da Stripe nem net_amount
        # (split de receita plataforma<->personal, nao dado do titular).
        self.assertNotIn('stripe_invoice_id', payment)
        self.assertNotIn('stripe_payment_intent_id', payment)
        self.assertNotIn('stripe_charge_id', payment)
        self.assertNotIn('net_amount', payment)
        self.assertNotIn('application_fee_amount', payment)

    def test_includes_assessments_of_the_subscribed_plan_slug(self):
        account = _make_account()
        PublicWorkoutSubscription.objects.create(account=account, plan_slug='bruno')
        record_assessment(plan_slug='bruno', measured_at=date(2026, 1, 5), weight_kg=Decimal('80'))

        data = export_account_data(account_id=account.pk)

        self.assertEqual(len(data['assessments']), 1)
        self.assertEqual(data['assessments'][0]['weight_kg'], 80.0)

    def test_includes_full_load_history_not_just_latest(self):
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('90'),
            performed_on=date(2026, 1, 5), idempotency_key='k1',
        )
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('100'),
            performed_on=date(2026, 1, 12), idempotency_key='k2',
        )

        data = export_account_data(account_id=account.pk)

        self.assertEqual(len(data['load_history']), 2)

    def test_does_not_include_program_payload(self):
        # Conteudo autoral do personal (o QUE foi prescrito) nao e' dado
        # pessoal do titular (o QUE ele fez/e') — fica de fora de proposito.
        account = _make_account()
        PublicWorkoutSubscription.objects.create(account=account, plan_slug='bruno')

        data = export_account_data(account_id=account.pk)

        self.assertNotIn('program_versions', data)
        self.assertNotIn('program', data)

    def test_does_not_leak_data_between_accounts(self):
        account_a = _make_account(email='a@example.com')
        account_b = _make_account(email='b@example.com')
        PublicWorkoutSubscription.objects.create(account=account_a, plan_slug='bruno')
        record_load(
            account_id=account_a.pk, movement_slug='agachamento-livre', weight_kg=Decimal('100'),
            performed_on=date(2026, 1, 5), idempotency_key='k-a',
        )

        data_b = export_account_data(account_id=account_b.pk)

        self.assertEqual(data_b['load_history'], [])
        self.assertIsNone(data_b['subscription'])

    def test_unknown_account_raises_does_not_exist(self):
        with self.assertRaises(PublicWorkoutAccount.DoesNotExist):
            export_account_data(account_id=999999)
