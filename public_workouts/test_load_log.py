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
from public_workouts.services import (
    LoadCorrectionConflictError,
    LoadCorrectionNotFoundError,
    LoadValueError,
    build_student_package,
    correct_load,
    list_load_history,
    record_load,
)

_TOP_SET = 'top_set'
_WARMUP = 'warmup'
_MAX_SET = 'max_set'
_LEGACY_UNKNOWN = 'legacy_unknown'


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

    def test_rir_above_the_ceiling_is_rejected(self):
        # Plano curva-carga-completa-reps-rir-recorde §1.3: RIR finito de 0
        # a 99,9 -- teto amplo de sanidade, nao meta de treino.
        account = _make_account()

        with self.assertRaises(LoadValueError):
            record_load(
                account_id=account.pk,
                movement_slug='agachamento-livre',
                weight_kg=Decimal('100'),
                rir=Decimal('100'),
                performed_on=date(2026, 1, 5),
                idempotency_key='key-rir-acima-do-teto',
            )
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 0)

    def test_rir_accepts_half_point(self):
        # rir_spec do schema do programa ja usa meio-ponto (ex. "RIR 1.5")
        # -- o modelo (Decimal 3,1) ja aceitava, so nao havia teste
        # confirmando que a validacao nao rejeita.
        account = _make_account()

        result = record_load(
            account_id=account.pk,
            movement_slug='agachamento-livre',
            weight_kg=Decimal('100'),
            rir=Decimal('1.5'),
            performed_on=date(2026, 1, 5),
            idempotency_key='key-rir-meio-ponto',
        )

        self.assertEqual(result['rir'], 1.5)

    def test_non_finite_rir_is_rejected(self):
        # json.loads aceita o literal NaN; sem o cheque .is_finite() em
        # _validate_load_values isso levantaria decimal.InvalidOperation
        # (500), nao LoadValueError (400).
        account = _make_account()

        with self.assertRaises(LoadValueError):
            record_load(
                account_id=account.pk,
                movement_slug='agachamento-livre',
                weight_kg=Decimal('100'),
                rir=Decimal('NaN'),
                performed_on=date(2026, 1, 5),
                idempotency_key='key-rir-nan',
            )
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 0)

    def test_non_finite_weight_kg_is_rejected(self):
        account = _make_account()

        with self.assertRaises(LoadValueError):
            record_load(
                account_id=account.pk,
                movement_slug='agachamento-livre',
                weight_kg=Decimal('Infinity'),
                performed_on=date(2026, 1, 5),
                idempotency_key='key-peso-infinito',
            )
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 0)

    def test_reps_zero_is_rejected(self):
        # Plano §1.3: "reps zero nao representa serie concluida nesta UI"
        # -- reps, quando informado, e inteiro de 1 a 999, nunca 0.
        account = _make_account()

        with self.assertRaises(LoadValueError):
            record_load(
                account_id=account.pk,
                movement_slug='agachamento-livre',
                weight_kg=Decimal('100'),
                reps=0,
                performed_on=date(2026, 1, 5),
                idempotency_key='key-reps-zero',
            )
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 0)

    def test_reps_above_the_ceiling_is_rejected(self):
        account = _make_account()

        with self.assertRaises(LoadValueError):
            record_load(
                account_id=account.pk,
                movement_slug='agachamento-livre',
                weight_kg=Decimal('100'),
                reps=1000,
                performed_on=date(2026, 1, 5),
                idempotency_key='key-reps-acima-do-teto',
            )
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 0)

    def test_boolean_reps_is_rejected(self):
        # bool e subclasse de int em Python -- sem o cheque explicito,
        # reps=True passaria como reps=1 silenciosamente.
        account = _make_account()

        with self.assertRaises(LoadValueError):
            record_load(
                account_id=account.pk,
                movement_slug='agachamento-livre',
                weight_kg=Decimal('100'),
                reps=True,
                performed_on=date(2026, 1, 5),
                idempotency_key='key-reps-bool',
            )
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 0)

    def test_movement_without_weight_or_reps_still_records(self):
        # Caso real preservado (ver comentario em _validate_load_values):
        # movimento isometrico tipo prancha, sem peso nem repeticao
        # quantificavel -- so a existencia do registro na data importa.
        # Este teste documenta que essa combinacao continua aceita de
        # proposito, nao e uma lacuna esquecida.
        account = _make_account()

        result = record_load(
            account_id=account.pk,
            movement_slug='prancha',
            weight_kg=None,
            reps=None,
            performed_on=date(2026, 1, 5),
            idempotency_key='key-isometrico',
        )

        self.assertEqual(result['weight_kg'], None)
        self.assertEqual(result['reps'], None)
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 1)

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

    def test_only_active_excludes_corrected_records(self):
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('900'),
            performed_on=date(2026, 1, 5), idempotency_key='key-original',
        )
        correct_load(
            account_id=account.pk, supersedes_idempotency_key='key-original', idempotency_key='key-correcao',
            weight_kg=Decimal('90'),
        )

        only_active = list_load_history(account_id=account.pk, only_active=True)
        everything = list_load_history(account_id=account.pk)

        self.assertEqual([e['weight_kg'] for e in only_active], [90.0])
        self.assertEqual(sorted(e['weight_kg'] for e in everything), [90.0, 900.0])


class CorrectLoadTests(TestCase):
    # Fase 3 do plano curva-carga-completa-reps-rir-recorde (§4.1).

    def test_creates_new_log_and_deactivates_target(self):
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('900'),
            performed_on=date(2026, 1, 5), idempotency_key='key-original',
        )

        result = correct_load(
            account_id=account.pk, supersedes_idempotency_key='key-original', idempotency_key='key-correcao',
            weight_kg=Decimal('90'), reps=8, rir=Decimal('2'),
        )

        self.assertEqual(result['weight_kg'], 90.0)
        self.assertTrue(result['is_active'])
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 2)
        original = PublicWorkoutLoadLog.objects.get(idempotency_key='key-original')
        self.assertFalse(original.is_active)
        correction = PublicWorkoutLoadLog.objects.get(idempotency_key='key-correcao')
        self.assertEqual(correction.supersedes_id, original.pk)

    def test_correction_inherits_movement_and_date_from_target(self):
        # movement_slug/performed_on NUNCA vem do payload da correcao --
        # sempre do alvo, mesmo que o chamador passe outra coisa por engano.
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('900'),
            performed_on=date(2026, 1, 5), program_id='bruno-2026-q1', week_in_program=3,
            idempotency_key='key-original',
        )

        result = correct_load(
            account_id=account.pk, supersedes_idempotency_key='key-original', idempotency_key='key-correcao',
            weight_kg=Decimal('90'),
        )

        self.assertEqual(result['movement_slug'], 'agachamento-livre')
        self.assertEqual(result['performed_on'], '2026-01-05')
        self.assertEqual(result['program_id'], 'bruno-2026-q1')
        self.assertEqual(result['week_in_program'], 3)

    def test_target_not_found_in_this_account_raises(self):
        account_a = _make_account(email='a@example.com')
        account_b = _make_account(email='b@example.com')
        record_load(
            account_id=account_a.pk, movement_slug='agachamento-livre', weight_kg=Decimal('900'),
            performed_on=date(2026, 1, 5), idempotency_key='key-de-a',
        )

        # b tentando corrigir o registro de a -- nunca acha, nunca corrige
        # carga de outra conta.
        with self.assertRaises(LoadCorrectionNotFoundError):
            correct_load(
                account_id=account_b.pk, supersedes_idempotency_key='key-de-a', idempotency_key='key-tentativa',
                weight_kg=Decimal('90'),
            )
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 1)

    def test_correcting_an_already_corrected_target_raises_conflict(self):
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('900'),
            performed_on=date(2026, 1, 5), idempotency_key='key-original',
        )
        correct_load(
            account_id=account.pk, supersedes_idempotency_key='key-original', idempotency_key='key-correcao-1',
            weight_kg=Decimal('90'),
        )

        with self.assertRaises(LoadCorrectionConflictError):
            correct_load(
                account_id=account.pk, supersedes_idempotency_key='key-original', idempotency_key='key-correcao-2',
                weight_kg=Decimal('91'),
            )
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 2)

    def test_resending_the_same_correction_idempotency_key_does_not_duplicate(self):
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('900'),
            performed_on=date(2026, 1, 5), idempotency_key='key-original',
        )
        kwargs = dict(
            account_id=account.pk, supersedes_idempotency_key='key-original', idempotency_key='key-correcao',
            weight_kg=Decimal('90'),
        )

        first = correct_load(**kwargs)
        second = correct_load(**{**kwargs, 'weight_kg': Decimal('99')})  # tentativa de reenvio "diferente"

        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 2)
        self.assertEqual(first['weight_kg'], second['weight_kg'])

    def test_invalid_correction_value_is_rejected_without_deactivating_target(self):
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('900'),
            performed_on=date(2026, 1, 5), idempotency_key='key-original',
        )

        with self.assertRaises(LoadValueError):
            correct_load(
                account_id=account.pk, supersedes_idempotency_key='key-original', idempotency_key='key-correcao',
                weight_kg=Decimal('-90'),
            )

        original = PublicWorkoutLoadLog.objects.get(idempotency_key='key-original')
        self.assertTrue(original.is_active)
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 1)

    def test_corrected_record_disappears_from_current_state_consumers(self):
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('900'),
            performed_on=date(2026, 1, 5), idempotency_key='key-original',
        )
        correct_load(
            account_id=account.pk, supersedes_idempotency_key='key-original', idempotency_key='key-correcao',
            weight_kg=Decimal('90'),
        )

        package = build_student_package(account_id=account.pk, slug='bruno')

        self.assertEqual(package['last_load_by_movement']['agachamento-livre']['weight_kg'], 90.0)


class AchievementTests(TestCase):
    # Fase 4 do plano curva-carga-completa-reps-rir-recorde (§6.1/§6.2).

    def test_first_eligible_log_gets_no_achievement(self):
        # "Primeiro elegivel: Primeiro registro salvo, sem trofeu de
        # recorde" -- nao ha "anterior" pra superar.
        account = _make_account()

        result = record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('90'),
            performed_on=date(2026, 1, 5), idempotency_key='key-1', set_role=_TOP_SET,
        )

        self.assertIsNone(result['achievement'])

    def test_strictly_higher_weight_gets_an_achievement(self):
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('90'),
            performed_on=date(2026, 1, 5), idempotency_key='key-1', set_role=_TOP_SET,
        )

        result = record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('92.5'),
            performed_on=date(2026, 1, 12), idempotency_key='key-2', set_role=_TOP_SET,
        )

        self.assertEqual(
            result['achievement'],
            {'kind': 'load_record', 'previous_weight_kg': 90.0, 'delta_kg': 2.5},
        )

    def test_tied_weight_gets_no_achievement(self):
        # "Empate ... nao dispara. Mesma carga com mais reps recebe
        # confirmacao normal nesta versao."
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('90'),
            performed_on=date(2026, 1, 5), idempotency_key='key-1', set_role=_TOP_SET,
        )

        result = record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('90'), reps=20,
            performed_on=date(2026, 1, 12), idempotency_key='key-2', set_role=_TOP_SET,
        )

        self.assertIsNone(result['achievement'])

    def test_lower_weight_gets_no_achievement(self):
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('100'),
            performed_on=date(2026, 1, 5), idempotency_key='key-1', set_role=_TOP_SET,
        )

        result = record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('90'),
            performed_on=date(2026, 1, 12), idempotency_key='key-2', set_role=_TOP_SET,
        )

        self.assertIsNone(result['achievement'])

    def test_warmup_never_gets_an_achievement_even_when_heavier(self):
        # Aquecimento nunca e' elegivel, mesmo levantando mais peso que
        # qualquer serie principal -- nao e' comparavel.
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('90'),
            performed_on=date(2026, 1, 5), idempotency_key='key-1', set_role=_TOP_SET,
        )

        result = record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('120'),
            performed_on=date(2026, 1, 12), idempotency_key='key-2', set_role=_WARMUP,
        )

        self.assertIsNone(result['achievement'])

    def test_legacy_unknown_never_gets_an_achievement(self):
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('90'),
            performed_on=date(2026, 1, 5), idempotency_key='key-1', set_role=_TOP_SET,
        )

        result = record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('120'),
            performed_on=date(2026, 1, 12), idempotency_key='key-2', set_role=_LEGACY_UNKNOWN,
        )

        self.assertIsNone(result['achievement'])

    def test_without_weight_never_gets_an_achievement(self):
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='flexao-de-braco', weight_kg=None, reps=20,
            performed_on=date(2026, 1, 5), idempotency_key='key-1', set_role=_TOP_SET,
        )

        result = record_load(
            account_id=account.pk, movement_slug='flexao-de-braco', weight_kg=None, reps=30,
            performed_on=date(2026, 1, 12), idempotency_key='key-2', set_role=_TOP_SET,
        )

        self.assertIsNone(result['achievement'])

    def test_max_set_competes_for_personal_record_alongside_top_set(self):
        # eligible_for_personal_record aceita top_set E max_set (diferente
        # de eligible_for_progress_curve, que so' aceita top_set) --
        # "abranger todo historico elegivel, inclusive max_set".
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('90'),
            performed_on=date(2026, 1, 5), idempotency_key='key-top', set_role=_TOP_SET,
        )
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('110'),
            performed_on=date(2026, 1, 8), idempotency_key='key-max', set_role=_MAX_SET,
        )

        # Uma serie principal comum, mais leve que o max_set anterior, NAO
        # e' recorde -- max_set conta como concorrente mesmo nao sendo
        # top_set.
        result = record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('105'),
            performed_on=date(2026, 1, 15), idempotency_key='key-top-2', set_role=_TOP_SET,
        )

        self.assertIsNone(result['achievement'])

    def test_does_not_compare_across_movements(self):
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('200'),
            performed_on=date(2026, 1, 5), idempotency_key='key-1', set_role=_TOP_SET,
        )

        # Primeiro registro de um movimento DIFERENTE -- 60kg no supino nao
        # compete contra 200kg no agachamento.
        result = record_load(
            account_id=account.pk, movement_slug='supino-reto', weight_kg=Decimal('60'),
            performed_on=date(2026, 1, 5), idempotency_key='key-2', set_role=_TOP_SET,
        )

        self.assertIsNone(result['achievement'])

    def test_does_not_leak_achievement_between_accounts(self):
        account_a = _make_account(email='a@example.com')
        account_b = _make_account(email='b@example.com')
        record_load(
            account_id=account_a.pk, movement_slug='agachamento-livre', weight_kg=Decimal('200'),
            performed_on=date(2026, 1, 5), idempotency_key='key-a', set_role=_TOP_SET,
        )

        # Primeiro registro de b -- nao ve o 200kg de a.
        result = record_load(
            account_id=account_b.pk, movement_slug='agachamento-livre', weight_kg=Decimal('60'),
            performed_on=date(2026, 1, 5), idempotency_key='key-b', set_role=_TOP_SET,
        )

        self.assertIsNone(result['achievement'])

    def test_achievement_is_replayed_identically_on_idempotent_retry(self):
        # "Persistir resultado da conquista ... pra replay estavel apos
        # resposta perdida" -- reenvio da MESMA idempotency_key devolve o
        # resultado ORIGINAL, nunca recalcula contra o estado atual.
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('90'),
            performed_on=date(2026, 1, 5), idempotency_key='key-1', set_role=_TOP_SET,
        )
        first = record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('100'),
            performed_on=date(2026, 1, 12), idempotency_key='key-2', set_role=_TOP_SET,
        )

        # "Retentativa" com a MESMA chave mas peso totalmente diferente --
        # o servico ignora o peso do reenvio e devolve a linha original.
        retry = record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('5000'),
            performed_on=date(2026, 1, 12), idempotency_key='key-2', set_role=_TOP_SET,
        )

        self.assertEqual(first['achievement'], {'kind': 'load_record', 'previous_weight_kg': 90.0, 'delta_kg': 10.0})
        self.assertEqual(retry['achievement'], first['achievement'])

    def test_correcting_up_past_other_active_logs_gets_an_achievement(self):
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('100'),
            performed_on=date(2026, 1, 5), idempotency_key='key-dia-1', set_role=_TOP_SET,
        )
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('90'),
            performed_on=date(2026, 1, 12), idempotency_key='key-dia-2', set_role=_TOP_SET,
        )

        # 90 -> 95 ainda fica ABAIXO do 100kg do dia 1 -- nao e' recorde.
        under = correct_load(
            account_id=account.pk, supersedes_idempotency_key='key-dia-2', idempotency_key='key-correcao-1',
            weight_kg=Decimal('95'),
        )
        self.assertIsNone(under['achievement'])

        # Corrigindo de novo (a correcao anterior, agora inativa, e' o novo
        # alvo) pra 105 -- ai sim supera o 100kg do dia 1.
        over = correct_load(
            account_id=account.pk, supersedes_idempotency_key='key-correcao-1', idempotency_key='key-correcao-2',
            weight_kg=Decimal('105'),
        )
        self.assertEqual(over['achievement'], {'kind': 'load_record', 'previous_weight_kg': 100.0, 'delta_kg': 5.0})

    def test_correcting_the_only_log_down_creates_no_compensatory_achievement(self):
        # "Correcao para baixo nao cria celebracao compensatoria."
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('900'),
            performed_on=date(2026, 1, 5), idempotency_key='key-original', set_role=_TOP_SET,
        )

        result = correct_load(
            account_id=account.pk, supersedes_idempotency_key='key-original', idempotency_key='key-correcao',
            weight_kg=Decimal('90'),
        )

        self.assertIsNone(result['achievement'])

    def test_correcting_the_only_log_up_is_not_a_record_against_its_own_typo(self):
        # O UNICO registro do movimento (90kg, sem trofeu por ser o
        # primeiro) sendo corrigido pra 95kg (typo) nao pode "virar
        # recorde" so' por diferir do proprio valor errado -- excluido da
        # comparacao, nao ha NENHUM concorrente ativo.
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('90'),
            performed_on=date(2026, 1, 5), idempotency_key='key-original', set_role=_TOP_SET,
        )

        result = correct_load(
            account_id=account.pk, supersedes_idempotency_key='key-original', idempotency_key='key-correcao',
            weight_kg=Decimal('95'),
        )

        self.assertIsNone(result['achievement'])

    def test_corrected_away_log_no_longer_counts_as_the_competitor(self):
        # Corrigir 100 (dia 1) pra 80 e depois registrar 90 (dia 2, novo)
        # deve contar como recorde -- o 100 antigo esta INATIVO, 80 e' o
        # concorrente real.
        account = _make_account()
        record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('100'),
            performed_on=date(2026, 1, 5), idempotency_key='key-original', set_role=_TOP_SET,
        )
        correct_load(
            account_id=account.pk, supersedes_idempotency_key='key-original', idempotency_key='key-correcao',
            weight_kg=Decimal('80'),
        )

        result = record_load(
            account_id=account.pk, movement_slug='agachamento-livre', weight_kg=Decimal('90'),
            performed_on=date(2026, 1, 12), idempotency_key='key-dia-2', set_role=_TOP_SET,
        )

        self.assertEqual(result['achievement'], {'kind': 'load_record', 'previous_weight_kg': 80.0, 'delta_kg': 10.0})
