"""
ARQUIVO: testes de S2 (build_student_package) e S3 (record_load) do
corredor (Onda A1, Fatia B do CORDA —
docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- Fatia B re-congelou S2/S3 trocando `student_identity_id` por `account_id`
  (decisao escrita entre as duas frentes, D.5) — cada garantia do "Pronto
  quando (Fatia B)" precisa do teste que prova que ela segura, nao so que
  o codigo roda.
- record_load idempotente por idempotency_key e a UNICA garantia herdada
  do "Pronto quando" original da Onda A1 (o resto ja valia pra Fatia A).
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutLoadLog
from public_workouts.services import LoadValueError, build_student_package, record_load


def _make_account(email='atleta@example.com') -> PublicWorkoutAccount:
    return PublicWorkoutAccount.objects.create(email=email)


class RecordLoadTests(TestCase):
    def test_creates_a_load_log_row(self):
        account = _make_account()

        result = record_load(
            account_id=account.pk,
            movement_slug='agachamento-livre',
            weight_kg=Decimal('100.00'),
            reps=8,
            rir=Decimal('2'),
            performed_on=date(2026, 1, 5),
            program_id='bruno-2026-q1',
            week_in_program=1,
            idempotency_key='key-1',
        )

        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 1)
        self.assertEqual(result['movement_slug'], 'agachamento-livre')
        self.assertEqual(result['weight_kg'], 100.0)
        self.assertEqual(result['reps'], 8)
        self.assertEqual(result['rir'], 2.0)
        self.assertEqual(result['program_id'], 'bruno-2026-q1')
        self.assertEqual(result['week_in_program'], 1)
        self.assertEqual(result['idempotency_key'], 'key-1')

    def test_accepts_iso_string_for_performed_on(self):
        account = _make_account()

        result = record_load(
            account_id=account.pk,
            movement_slug='agachamento-livre',
            weight_kg=Decimal('100'),
            performed_on='2026-01-05',
            idempotency_key='key-iso',
        )

        self.assertEqual(result['performed_on'], '2026-01-05')

    def test_resending_the_same_idempotency_key_does_not_duplicate(self):
        # Pronto quando (Fatia B) #1 — a garantia herdada do "Pronto quando"
        # original da Onda A1: reenvio da outbox (Onda B3) nunca duplica.
        account = _make_account()
        kwargs = dict(
            account_id=account.pk,
            movement_slug='agachamento-livre',
            weight_kg=Decimal('100'),
            performed_on=date(2026, 1, 5),
            idempotency_key='key-duplicado',
        )

        first = record_load(**kwargs)
        second = record_load(**{**kwargs, 'weight_kg': Decimal('999')})  # tentativa de reenvio "diferente"

        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 1)
        self.assertEqual(first['weight_kg'], second['weight_kg'])  # devolve o registro ORIGINAL, nao o novo

    def test_negative_weight_kg_is_rejected(self):
        # Pronto quando (Fatia B) #2 — guardrail estrutural no servico.
        account = _make_account()

        with self.assertRaises(LoadValueError):
            record_load(
                account_id=account.pk,
                movement_slug='agachamento-livre',
                weight_kg=Decimal('-10'),
                performed_on=date(2026, 1, 5),
                idempotency_key='key-negativo',
            )
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 0)

    def test_negative_rir_is_rejected(self):
        account = _make_account()

        with self.assertRaises(LoadValueError):
            record_load(
                account_id=account.pk,
                movement_slug='agachamento-livre',
                weight_kg=Decimal('100'),
                rir=Decimal('-1'),
                performed_on=date(2026, 1, 5),
                idempotency_key='key-rir-negativo',
            )
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 0)

    def test_none_weight_kg_is_accepted_for_bodyweight_movements(self):
        account = _make_account()

        result = record_load(
            account_id=account.pk,
            movement_slug='flexao-de-braco',
            weight_kg=None,
            reps=20,
            performed_on=date(2026, 1, 5),
            idempotency_key='key-peso-corporal',
        )

        self.assertIsNone(result['weight_kg'])
        self.assertEqual(result['reps'], 20)


class BuildStudentPackageTests(TestCase):
    def test_has_the_s2_shape_even_with_no_load_logged_yet(self):
        # Pronto quando (Fatia B) #3.
        account = _make_account()

        package = build_student_package(account_id=account.pk, slug='bruno')

        self.assertEqual(
            set(package),
            {'last_load_by_movement', 'one_rep_max_by_movement', 'substitutions', 'access_until'},
        )
        self.assertEqual(package['last_load_by_movement'], {})
        self.assertEqual(package['one_rep_max_by_movement'], {})
        self.assertEqual(package['substitutions'], {})
        self.assertIsNone(package['access_until'])

    def test_returns_the_most_recent_load_per_movement(self):
        account = _make_account()
        record_load(
            account_id=account.pk,
            movement_slug='agachamento-livre',
            weight_kg=Decimal('90'),
            performed_on=date(2026, 1, 5),
            idempotency_key='key-antiga',
        )
        record_load(
            account_id=account.pk,
            movement_slug='agachamento-livre',
            weight_kg=Decimal('100'),
            performed_on=date(2026, 1, 12),
            idempotency_key='key-recente',
        )

        package = build_student_package(account_id=account.pk, slug='bruno')

        self.assertEqual(package['last_load_by_movement']['agachamento-livre']['weight_kg'], 100.0)
        self.assertEqual(package['last_load_by_movement']['agachamento-livre']['idempotency_key'], 'key-recente')

    def test_one_row_per_movement_even_with_several_movements_logged(self):
        account = _make_account()
        record_load(
            account_id=account.pk,
            movement_slug='agachamento-livre',
            weight_kg=Decimal('100'),
            performed_on=date(2026, 1, 5),
            idempotency_key='key-agachamento',
        )
        record_load(
            account_id=account.pk,
            movement_slug='supino-reto',
            weight_kg=Decimal('60'),
            performed_on=date(2026, 1, 5),
            idempotency_key='key-supino',
        )

        package = build_student_package(account_id=account.pk, slug='bruno')

        self.assertEqual(set(package['last_load_by_movement']), {'agachamento-livre', 'supino-reto'})

    def test_does_not_leak_load_between_accounts(self):
        account_a = _make_account(email='a@example.com')
        account_b = _make_account(email='b@example.com')
        record_load(
            account_id=account_a.pk,
            movement_slug='agachamento-livre',
            weight_kg=Decimal('100'),
            performed_on=date(2026, 1, 5),
            idempotency_key='key-a',
        )

        package_b = build_student_package(account_id=account_b.pk, slug='bruno')

        self.assertEqual(package_b['last_load_by_movement'], {})
