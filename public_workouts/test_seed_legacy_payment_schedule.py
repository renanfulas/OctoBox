"""Testes do management command seed_legacy_payment_schedule.

POR QUE ELE EXISTE: os 10 clientes legados (seed_legacy_workout_accounts.py)
nunca passaram pelo checkout Stripe deste corredor, entao nunca tiveram
nenhum PublicWorkoutPayment criado -- sem isso a regua de avisos +
suspensao automatica (drain_public_workout_notices) nao tem o que avaliar
pra eles. Este comando cria esse primeiro ciclo de cobranca de forma
explicita (nunca adivinha data nem valor).
"""

from datetime import date
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutPayment,
    PublicWorkoutSubscription,
)


class SeedLegacyPaymentScheduleTests(TestCase):
    def _make_subscription(self, *, email, plan_slug):
        account = PublicWorkoutAccount.objects.create(email=email)
        return PublicWorkoutSubscription.objects.create(account=account, plan_slug=plan_slug)

    def test_creates_payment_with_notice_schedule_for_existing_subscription(self):
        subscription = self._make_subscription(email='bruno@example.com', plan_slug='bruno')

        call_command(
            'seed_legacy_payment_schedule',
            '--payment', 'bruno:2026-10-05:97.00',
            stdout=StringIO(),
        )

        payment = PublicWorkoutPayment.objects.get(subscription=subscription)
        self.assertEqual(payment.due_date, date(2026, 10, 5))
        self.assertEqual(payment.gross_amount, Decimal('97.00'))
        self.assertEqual(payment.notices.count(), 5)

    def test_accepts_multiple_payments_with_different_due_dates(self):
        self._make_subscription(email='bruno@example.com', plan_slug='bruno')
        self._make_subscription(email='juliana@example.com', plan_slug='juliana')

        call_command(
            'seed_legacy_payment_schedule',
            '--payment', 'bruno:2026-10-05:97.00',
            '--payment', 'juliana:2026-10-20:97.00',
            stdout=StringIO(),
        )

        bruno_payment = PublicWorkoutPayment.objects.get(subscription__plan_slug='bruno')
        juliana_payment = PublicWorkoutPayment.objects.get(subscription__plan_slug='juliana')
        self.assertEqual(bruno_payment.due_date, date(2026, 10, 5))
        self.assertEqual(juliana_payment.due_date, date(2026, 10, 20))

    def test_dry_run_creates_nothing(self):
        self._make_subscription(email='bruno@example.com', plan_slug='bruno')

        call_command(
            'seed_legacy_payment_schedule',
            '--dry-run',
            '--payment', 'bruno:2026-10-05:97.00',
            stdout=StringIO(),
        )

        self.assertFalse(PublicWorkoutPayment.objects.exists())

    def test_is_idempotent_for_the_same_slug_and_due_date(self):
        self._make_subscription(email='bruno@example.com', plan_slug='bruno')
        call_command(
            'seed_legacy_payment_schedule',
            '--payment', 'bruno:2026-10-05:97.00',
            stdout=StringIO(),
        )

        call_command(
            'seed_legacy_payment_schedule',
            '--payment', 'bruno:2026-10-05:97.00',
            stdout=StringIO(),
        )

        self.assertEqual(PublicWorkoutPayment.objects.count(), 1)

    def test_raises_when_slug_has_no_subscription(self):
        with self.assertRaises(CommandError):
            call_command(
                'seed_legacy_payment_schedule',
                '--payment', 'inexistente:2026-10-05:97.00',
                stdout=StringIO(),
            )

    def test_raises_on_malformed_triple(self):
        with self.assertRaises(CommandError):
            call_command('seed_legacy_payment_schedule', '--payment', 'bruno:2026-10-05', stdout=StringIO())

    def test_raises_on_invalid_date(self):
        with self.assertRaises(CommandError):
            call_command(
                'seed_legacy_payment_schedule',
                '--payment', 'bruno:05-10-2026:97.00',
                stdout=StringIO(),
            )

    def test_raises_on_amount_out_of_range(self):
        self._make_subscription(email='bruno@example.com', plan_slug='bruno')

        with self.assertRaises(CommandError):
            call_command(
                'seed_legacy_payment_schedule',
                '--payment', 'bruno:2026-10-05:999999.00',
                stdout=StringIO(),
            )

    def test_raises_when_no_payment_given(self):
        with self.assertRaises(CommandError):
            call_command('seed_legacy_payment_schedule', stdout=StringIO())
