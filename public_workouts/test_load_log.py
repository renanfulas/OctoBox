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

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutLoadLog, PublicWorkoutLoadLogSetRole
from public_workouts.services import LoadValueError, build_student_package, list_load_history, record_load


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

    def test_weight_kg_above_the_ceiling_is_rejected(self):
        # Decisao do Renan: teto de 1000kg (1 tonelada) — R.N do CORDA,
        # numero de produto, nao um palpite de script.
        account = _make_account()

        with self.assertRaises(LoadValueError):
            record_load(
                account_id=account.pk,
                movement_slug='agachamento-livre',
                weight_kg=Decimal('1000.01'),
                performed_on=date(2026, 1, 5),
                idempotency_key='key-acima-do-teto',
            )
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 0)

    def test_weight_kg_exactly_at_the_ceiling_is_accepted(self):
        account = _make_account()

        result = record_load(
            account_id=account.pk,
            movement_slug='agachamento-livre',
            weight_kg=Decimal('1000'),
            performed_on=date(2026, 1, 5),
            idempotency_key='key-no-teto',
        )

        self.assertEqual(result['weight_kg'], 1000.0)
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 1)

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
            {'last_load_by_movement', 'last_top_set_by_movement', 'one_rep_max_by_movement', 'substitutions', 'access_until'},
        )
        self.assertEqual(package['last_load_by_movement'], {})
        self.assertEqual(package['last_top_set_by_movement'], {})
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
        self.assertEqual(package['last_top_set_by_movement']['agachamento-livre']['weight_kg'], 100.0)

    def test_last_top_set_hint_ignores_a_more_recent_warmup(self):
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre',
            weight_kg=Decimal('100'), performed_on=date(2026, 1, 5),
            set_role=PublicWorkoutLoadLogSetRole.TOP_SET, idempotency_key='top-set',
        )
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre',
            weight_kg=Decimal('40'), performed_on=date(2026, 1, 12),
            set_role=PublicWorkoutLoadLogSetRole.WARMUP, idempotency_key='warmup',
        )

        package = build_student_package(account_id=account.pk, slug='bruno')

        self.assertEqual(package['last_load_by_movement']['agachamento-livre']['weight_kg'], 40.0)
        self.assertEqual(package['last_top_set_by_movement']['agachamento-livre']['weight_kg'], 100.0)

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

    def test_one_rep_max_is_estimated_from_the_most_recent_valid_set(self):
        # Onda A3: build_student_package agora estima 1RM de verdade a
        # partir do ultimo set de cada movimento (mesmo recorte de
        # last_load_by_movement).
        account = _make_account()
        record_load(
            account_id=account.pk,
            movement_slug='agachamento-livre',
            weight_kg=Decimal('100'),
            reps=5,
            performed_on=date(2026, 1, 5),
            idempotency_key='key-1rm',
        )

        package = build_student_package(account_id=account.pk, slug='bruno')

        estimate = package['one_rep_max_by_movement']['agachamento-livre']
        self.assertEqual(estimate['formula'], 'brzycki')
        self.assertEqual(estimate['confidence'], 'high')
        self.assertAlmostEqual(estimate['value_kg'], 100 * 36 / 32, places=1)

    def test_movement_without_reps_gets_no_one_rep_max_entry(self):
        # record_load aceita reps=None (ex.: so peso corporal registrado) --
        # sem reps, estimate_one_rep_max nao tem o que calcular.
        account = _make_account()
        record_load(
            account_id=account.pk,
            movement_slug='prancha',
            weight_kg=None,
            performed_on=date(2026, 1, 5),
            idempotency_key='key-sem-reps',
        )

        package = build_student_package(account_id=account.pk, slug='bruno')

        self.assertNotIn('prancha', package['one_rep_max_by_movement'])

    def test_set_above_fifteen_effective_reps_gets_no_one_rep_max_entry(self):
        account = _make_account()
        record_load(
            account_id=account.pk,
            movement_slug='agachamento-livre',
            weight_kg=Decimal('40'),
            reps=20,
            performed_on=date(2026, 1, 5),
            idempotency_key='key-20-reps',
        )

        package = build_student_package(account_id=account.pk, slug='bruno')

        self.assertNotIn('agachamento-livre', package['one_rep_max_by_movement'])


class ListLoadHistoryTests(TestCase):
    def test_returns_empty_list_when_no_load_logged(self):
        account = _make_account()

        self.assertEqual(list_load_history(account_id=account.pk), [])

    def test_returns_entries_in_chronological_ascending_order(self):
        # Inverso do Meta.ordering do model (mais recente primeiro, pensado
        # pro caso de uso "ultimo valor") — grafico de evolucao precisa do
        # sentido contrario.
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('100'),
            performed_on=date(2026, 1, 12), idempotency_key='key-recente',
        )
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('90'),
            performed_on=date(2026, 1, 5), idempotency_key='key-antiga',
        )

        history = list_load_history(account_id=account.pk)

        self.assertEqual([entry['weight_kg'] for entry in history], [90.0, 100.0])

    def test_groups_by_movement_slug_ready_for_regroup(self):
        # Ordem (movement_slug, performed_on, created_at) — pre-requisito do
        # {% regroup %} do Django, que exige a lista ja agrupada.
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='supino-reto', weight_kg=Decimal('60'),
            performed_on=date(2026, 1, 5), idempotency_key='key-supino',
        )
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('100'),
            performed_on=date(2026, 1, 5), idempotency_key='key-agachamento',
        )

        history = list_load_history(account_id=account.pk)

        self.assertEqual([entry['movement_slug'] for entry in history], ['agachamento-livre', 'supino-reto'])

    def test_filters_by_movement_slug_when_given(self):
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('100'),
            performed_on=date(2026, 1, 5), idempotency_key='key-agachamento',
        )
        record_load(
            account_id=account.pk, movement_slug='supino-reto', weight_kg=Decimal('60'),
            performed_on=date(2026, 1, 5), idempotency_key='key-supino',
        )

        history = list_load_history(account_id=account.pk, movement_slug='supino-reto')

        self.assertEqual([entry['movement_slug'] for entry in history], ['supino-reto'])

    def test_does_not_leak_between_accounts(self):
        account_a = _make_account(email='a@example.com')
        account_b = _make_account(email='b@example.com')
        record_load(
            account_id=account_a.pk, movement_slug='agachamento-livre', weight_kg=Decimal('100'),
            performed_on=date(2026, 1, 5), idempotency_key='key-a',
        )

        self.assertEqual(list_load_history(account_id=account_b.pk), [])

    def test_does_not_reset_across_program_republish(self):
        # Decisao de produto: progressao de carga e' continuidade do atleta,
        # nao do programa ativo.
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('90'),
            performed_on=date(2026, 1, 5), program_id='bruno-2026-q1', idempotency_key='key-v1',
        )
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('100'),
            performed_on=date(2026, 1, 12), program_id='bruno-2026-q2', idempotency_key='key-v2',
        )

        history = list_load_history(account_id=account.pk)

        self.assertEqual(len(history), 2)
