"""
ARQUIVO: testes da regua de avisos do corredor de treinos (Onda B2 do
CORDA — critério de entrada da onda, per R.P).

POR QUE ELE EXISTE:
- as 5 linhas (D-7,-3,-1,0,+2) precisam nascer certas, com a data
  empurrada pro proximo dia util quando cai em fim de semana/feriado —
  sem isso um aviso pode chegar (ou uma trava acontecer) num domingo.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from public_workouts.billing import (
    PUBLIC_WORKOUT_NOTICE_OFFSET_DAYS,
    PublicWorkoutPaymentAmountError,
    create_payment_with_notice_schedule,
)
from public_workouts.models import PublicWorkoutAccount, PublicWorkoutPaymentNotice, PublicWorkoutSubscription


def _make_subscription(email='aluno@example.com', plan_slug='giovanna'):
    account = PublicWorkoutAccount.objects.create(email=email)
    return PublicWorkoutSubscription.objects.create(account=account, plan_slug=plan_slug)


class PaymentNoticeScheduleTests(TestCase):
    def test_creates_payment_and_five_notice_rows(self):
        subscription = _make_subscription()
        due_date = date(2026, 3, 10)  # terca-feira, sem feriado por perto

        payment = create_payment_with_notice_schedule(
            subscription=subscription, due_date=due_date, gross_amount=Decimal('89.90')
        )

        notices = list(payment.notices.order_by('offset_days'))
        self.assertEqual(len(notices), 5)
        self.assertEqual({n.offset_days for n in notices}, set(PUBLIC_WORKOUT_NOTICE_OFFSET_DAYS))
        self.assertTrue(all(n.sent_at is None for n in notices))

    def test_scheduled_for_matches_offset_when_business_day(self):
        subscription = _make_subscription()
        due_date = date(2026, 3, 10)  # terca

        payment = create_payment_with_notice_schedule(
            subscription=subscription, due_date=due_date, gross_amount=Decimal('89.90')
        )

        by_offset = {n.offset_days: n.scheduled_for for n in payment.notices.all()}
        self.assertEqual(by_offset[0], due_date)
        self.assertEqual(by_offset[-1], date(2026, 3, 9))  # segunda
        self.assertEqual(by_offset[2], date(2026, 3, 12))  # quinta

    def test_scheduled_for_shifts_past_weekend(self):
        subscription = _make_subscription()
        # D0 cai num domingo (2026-03-08) -> deve empurrar pra segunda 2026-03-09.
        due_date = date(2026, 3, 8)

        payment = create_payment_with_notice_schedule(
            subscription=subscription, due_date=due_date, gross_amount=Decimal('89.90')
        )

        notice_d0 = payment.notices.get(offset_days=0)
        self.assertEqual(notice_d0.scheduled_for, date(2026, 3, 9))
        self.assertNotEqual(notice_d0.scheduled_for.weekday(), 5)
        self.assertNotEqual(notice_d0.scheduled_for.weekday(), 6)

    def test_scheduled_for_shifts_past_holiday(self):
        subscription = _make_subscription()
        # D-1 de 2026-04-22 cai em 2026-04-21 (Tiradentes) -> empurra pro dia 22.
        due_date = date(2026, 4, 22)

        payment = create_payment_with_notice_schedule(
            subscription=subscription, due_date=due_date, gross_amount=Decimal('89.90')
        )

        notice_d_minus_1 = payment.notices.get(offset_days=-1)
        self.assertEqual(notice_d_minus_1.scheduled_for, date(2026, 4, 22))

    def test_unique_constraint_rejects_duplicate_offset_for_same_payment(self):
        subscription = _make_subscription()
        payment = create_payment_with_notice_schedule(
            subscription=subscription, due_date=date(2026, 3, 10), gross_amount=Decimal('89.90')
        )

        with self.assertRaises(Exception):
            PublicWorkoutPaymentNotice.objects.create(payment=payment, offset_days=0, scheduled_for=date(2026, 3, 10))

    def test_amount_out_of_range_is_rejected_before_creating_rows(self):
        subscription = _make_subscription()

        with self.assertRaises(PublicWorkoutPaymentAmountError):
            create_payment_with_notice_schedule(
                subscription=subscription, due_date=date(2026, 3, 10), gross_amount=Decimal('0.00')
            )

        self.assertEqual(PublicWorkoutPaymentNotice.objects.count(), 0)
