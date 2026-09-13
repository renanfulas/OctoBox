"""
ARQUIVO: testes do drain de avisos + trava de D+2 do corredor de treinos
(Onda B2 do CORDA — critério de entrada da onda, per R.P).

POR QUE ELE EXISTE:
- P1 (aviso duplicado), P2 (aviso nunca enviado), P3 (aluno travado tendo
  pago) sao os tres piores bugs silenciosos de cobranca do CORDA. Cada um
  tem que ter um teste que prova que NAO acontece.
"""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from freezegun import freeze_time

from django.core import mail
from django.test import TestCase
from django.utils import timezone

from public_workouts.billing import create_payment_with_notice_schedule, drain_due_notices
from public_workouts.models import (
    PublicWorkoutPaymentStatus,
    PublicWorkoutSubscription,
    PublicWorkoutSubscriptionEvent,
    PublicWorkoutSubscriptionStatus,
)
from student_identity.delivery_gateways import StudentEmailDeliveryError
from student_identity.models import PublicWorkoutAccount


def _make_subscription(email='aluno@example.com', plan_slug='giovanna'):
    account = PublicWorkoutAccount.objects.create(email=email)
    return PublicWorkoutSubscription.objects.create(account=account, plan_slug=plan_slug)


def _make_payment_due_in(subscription, *, days_until_due):
    """days_until_due negativo = due_date no passado (ja vencido)."""
    due_date = timezone.localdate() + timedelta(days=days_until_due)
    return create_payment_with_notice_schedule(subscription=subscription, due_date=due_date, gross_amount=Decimal('89.90'))


@freeze_time('2026-03-10')  # terca-feira, sem feriado por perto — datas relativas ficam deterministicas
class DrainDueNoticesSendingTests(TestCase):
    def test_draining_twice_same_day_sends_only_once(self):
        subscription = _make_subscription()
        # due_date daqui a 7 dias -> a linha D-7 (offset -7) vence HOJE;
        # as outras 4 (D-3,-1,0,+2) ainda estao no futuro.
        _make_payment_due_in(subscription, days_until_due=7)

        first = drain_due_notices()
        second = drain_due_notices()

        self.assertEqual(first['sent'], 1)
        self.assertEqual(second['sent'], 0)
        self.assertEqual(len(mail.outbox), 1)

    def test_channel_failure_does_not_mark_sent_at(self):
        subscription = _make_subscription()
        payment = _make_payment_due_in(subscription, days_until_due=7)

        with patch('public_workouts.notifications.get_student_email_gateway') as get_gateway:
            gateway = Mock()
            gateway.send.side_effect = StudentEmailDeliveryError('smtp-down')
            get_gateway.return_value = gateway
            result = drain_due_notices()

        self.assertEqual(result['sent'], 0)
        self.assertEqual(result['skipped'], 1)
        notice = payment.notices.get(offset_days=-7)
        self.assertIsNone(notice.sent_at)

        # Sem o canal caido, o proximo drain envia normalmente (retry).
        second = drain_due_notices()
        self.assertEqual(second['sent'], 1)

    def test_notice_not_yet_due_is_not_sent(self):
        subscription = _make_subscription()
        _make_payment_due_in(subscription, days_until_due=30)  # nada vence hoje

        result = drain_due_notices()

        self.assertEqual(result['sent'], 0)
        self.assertEqual(len(mail.outbox), 0)


@freeze_time('2026-03-10')  # terca-feira, sem feriado por perto — datas relativas ficam deterministicas
class DrainDueNoticesSuspensionTests(TestCase):
    def test_payment_confirmed_one_minute_ago_is_not_suspended(self):
        subscription = _make_subscription()
        payment = _make_payment_due_in(subscription, days_until_due=-2)  # D+2 = hoje
        payment.status = PublicWorkoutPaymentStatus.PAID
        payment.paid_at = timezone.now() - timedelta(minutes=1)
        payment.save(update_fields=['status', 'paid_at'])

        result = drain_due_notices()

        self.assertEqual(result['suspended'], 0)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, PublicWorkoutSubscriptionStatus.ACTIVE)

    def test_unpaid_payment_two_days_overdue_suspends_subscription_with_reason(self):
        subscription = _make_subscription()
        _make_payment_due_in(subscription, days_until_due=-2)

        result = drain_due_notices()

        self.assertEqual(result['suspended'], 1)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, PublicWorkoutSubscriptionStatus.SUSPENDED)
        self.assertIsNotNone(subscription.suspended_at)

        event = PublicWorkoutSubscriptionEvent.objects.get(subscription=subscription)
        self.assertEqual(event.from_status, PublicWorkoutSubscriptionStatus.ACTIVE)
        self.assertEqual(event.to_status, PublicWorkoutSubscriptionStatus.SUSPENDED)
        self.assertIn('D+2', event.reason)

    def test_suspending_twice_does_not_duplicate_the_event(self):
        subscription = _make_subscription()
        _make_payment_due_in(subscription, days_until_due=-2)

        drain_due_notices()
        drain_due_notices()

        self.assertEqual(PublicWorkoutSubscriptionEvent.objects.filter(subscription=subscription).count(), 1)

    def test_unpaid_payment_not_yet_two_days_overdue_is_not_suspended(self):
        subscription = _make_subscription()
        _make_payment_due_in(subscription, days_until_due=-1)

        result = drain_due_notices()

        self.assertEqual(result['suspended'], 0)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, PublicWorkoutSubscriptionStatus.ACTIVE)
