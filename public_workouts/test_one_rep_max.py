"""
ARQUIVO: testes de estimate_one_rep_max e detect_one_rep_max_trend
(Onda A3 do CORDA — docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- a formula (Brzycki/Epley/blend, faixa de confianca) vem de uma
  especificacao ja escrita (docs/plans/public-workouts-produtizacao-plan.md,
  secao 4.4) — cada limiar de decisao (6/10/15 reps efetivas) precisa do
  teste que prova que o codigo implementa exatamente o que foi
  especificado, nao uma aproximacao.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutLoadLog
from public_workouts.one_rep_max import (
    MAX_EFFECTIVE_REPS,
    detect_one_rep_max_trend,
    estimate_one_rep_max,
    estimate_working_weight_kg,
)


class EstimateOneRepMaxTests(TestCase):
    def test_low_reps_uses_brzycki_with_high_confidence(self):
        result = estimate_one_rep_max(weight_kg=100, reps=6, rir=0)

        self.assertEqual(result.formula, 'brzycki')
        self.assertEqual(result.confidence, 'high')
        self.assertEqual(result.effective_reps, 6)
        self.assertAlmostEqual(result.value_kg, 100 * 36 / 31, places=1)

    def test_moderate_reps_uses_blend_with_moderate_confidence(self):
        result = estimate_one_rep_max(weight_kg=100, reps=7, rir=0)

        self.assertEqual(result.formula, 'blend')
        self.assertEqual(result.confidence, 'moderate')
        brzycki = 100 * 36 / 30
        epley = 100 * (1 + 7 / 30)
        self.assertAlmostEqual(result.value_kg, (brzycki + epley) / 2, places=1)

    def test_high_reps_uses_epley_with_low_confidence(self):
        result = estimate_one_rep_max(weight_kg=100, reps=15, rir=0)

        self.assertEqual(result.formula, 'epley')
        self.assertEqual(result.confidence, 'low')
        self.assertAlmostEqual(result.value_kg, 100 * (1 + 15 / 30), places=1)

    def test_above_fifteen_effective_reps_returns_none(self):
        self.assertIsNone(estimate_one_rep_max(weight_kg=100, reps=16, rir=0))
        self.assertIsNone(estimate_one_rep_max(weight_kg=100, reps=MAX_EFFECTIVE_REPS + 1, rir=0))

    def test_exactly_fifteen_effective_reps_still_returns_a_value(self):
        self.assertIsNotNone(estimate_one_rep_max(weight_kg=100, reps=MAX_EFFECTIVE_REPS, rir=0))

    def test_rir_is_added_to_reps_before_choosing_the_tier(self):
        # 4 reps + RIR 2 = 6 reps efetivas -> ainda Brzycki (alta confianca),
        # nao Epley que um reps=4 cru sugeriria.
        result = estimate_one_rep_max(weight_kg=100, reps=4, rir=2)

        self.assertEqual(result.effective_reps, 6)
        self.assertEqual(result.formula, 'brzycki')

    def test_raw_reps_without_rir_underestimates_relative_to_effective(self):
        # Prova a decisao #1 do plano: ignorar RIR subestima sistematicamente.
        with_rir = estimate_one_rep_max(weight_kg=100, reps=4, rir=2)
        without_rir = estimate_one_rep_max(weight_kg=100, reps=4, rir=0)

        self.assertGreater(with_rir.value_kg, without_rir.value_kg)

    def test_accepts_decimal_inputs_from_the_database(self):
        result = estimate_one_rep_max(weight_kg=Decimal('100.00'), reps=6, rir=Decimal('0'))

        self.assertIsNotNone(result)
        self.assertIsInstance(result.value_kg, float)

    def test_none_weight_kg_returns_none(self):
        self.assertIsNone(estimate_one_rep_max(weight_kg=None, reps=8, rir=0))

    def test_none_reps_returns_none(self):
        self.assertIsNone(estimate_one_rep_max(weight_kg=100, reps=None, rir=0))

    def test_never_compares_across_different_movements_by_construction(self):
        # A funcao nao recebe movement_slug nenhum -- e uma garantia
        # estrutural, nao um comportamento a assertar num teste unico;
        # este teste documenta a intencao (ver docstring do modulo).
        import inspect

        params = inspect.signature(estimate_one_rep_max).parameters
        self.assertNotIn('movement_slug', params)


def _make_account(email='atleta@example.com') -> PublicWorkoutAccount:
    return PublicWorkoutAccount.objects.create(email=email)


def _log(account, *, movement_slug, weight_kg, reps, performed_on, rir=Decimal('0')):
    return PublicWorkoutLoadLog.objects.create(
        account=account,
        movement_slug=movement_slug,
        weight_kg=Decimal(str(weight_kg)),
        reps=reps,
        rir=rir,
        performed_on=performed_on,
        idempotency_key=f'{movement_slug}-{performed_on.isoformat()}-{weight_kg}',
    )


class EstimateWorkingWeightKgTests(TestCase):
    """Inverso de estimate_one_rep_max -- Caminho 4 de load_suggestion.py
    (exercicio sem fase canonica de periodizacao)."""

    def test_is_the_inverse_of_estimate_one_rep_max_low_reps(self):
        one_rm = estimate_one_rep_max(weight_kg=100, reps=5, rir=0)

        working_weight = estimate_working_weight_kg(one_rep_max_kg=one_rm.value_kg, target_reps=5, target_rir=0)

        self.assertAlmostEqual(working_weight, 100, delta=2.5)

    def test_is_the_inverse_of_estimate_one_rep_max_blend_range(self):
        one_rm = estimate_one_rep_max(weight_kg=80, reps=8, rir=0)

        working_weight = estimate_working_weight_kg(one_rep_max_kg=one_rm.value_kg, target_reps=8, target_rir=0)

        self.assertAlmostEqual(working_weight, 80, delta=2.5)

    def test_is_the_inverse_of_estimate_one_rep_max_epley_range(self):
        one_rm = estimate_one_rep_max(weight_kg=60, reps=12, rir=0)

        working_weight = estimate_working_weight_kg(one_rep_max_kg=one_rm.value_kg, target_reps=12, target_rir=0)

        self.assertAlmostEqual(working_weight, 60, delta=2.5)

    def test_more_rir_in_reserve_suggests_lighter_weight(self):
        heavy = estimate_working_weight_kg(one_rep_max_kg=100, target_reps=8, target_rir=0)
        light = estimate_working_weight_kg(one_rep_max_kg=100, target_reps=8, target_rir=3)

        self.assertGreater(heavy, light)

    def test_none_above_max_effective_reps(self):
        result = estimate_working_weight_kg(one_rep_max_kg=100, target_reps=14, target_rir=2)  # 16 efetivas

        self.assertIsNone(result)

    def test_none_without_one_rep_max(self):
        self.assertIsNone(estimate_working_weight_kg(one_rep_max_kg=None, target_reps=8, target_rir=1))

    def test_none_without_target_reps(self):
        self.assertIsNone(estimate_working_weight_kg(one_rep_max_kg=100, target_reps=None, target_rir=1))

    def test_result_rounds_to_nearest_two_point_five(self):
        result = estimate_working_weight_kg(one_rep_max_kg=101, target_reps=7, target_rir=1)

        self.assertEqual(result % 2.5, 0)


class DetectOneRepMaxTrendTests(TestCase):
    def test_insufficient_data_with_fewer_than_three_weeks(self):
        account = _make_account()
        _log(account, movement_slug='agachamento-livre', weight_kg=100, reps=5, performed_on=date(2026, 1, 5))
        _log(account, movement_slug='agachamento-livre', weight_kg=102, reps=5, performed_on=date(2026, 1, 12))

        trend = detect_one_rep_max_trend(account_id=account.pk, movement_slug='agachamento-livre')

        self.assertEqual(trend.label, 'insufficient_data')
        self.assertEqual(trend.weekly_estimates_kg, ())

    def test_insufficient_data_when_no_load_logged_at_all(self):
        account = _make_account()

        trend = detect_one_rep_max_trend(account_id=account.pk, movement_slug='agachamento-livre')

        self.assertEqual(trend.label, 'insufficient_data')

    def test_plateau_when_three_weeks_stay_within_the_band(self):
        account = _make_account()
        # Mesmo peso x reps toda semana -> 1RM estimado identico -> plato.
        for week_offset in (0, 7, 14):
            _log(
                account,
                movement_slug='agachamento-livre',
                weight_kg=100,
                reps=5,
                performed_on=date(2026, 1, 5) + timedelta(days=week_offset),
            )

        trend = detect_one_rep_max_trend(account_id=account.pk, movement_slug='agachamento-livre')

        self.assertEqual(trend.label, 'plateau')
        self.assertEqual(len(trend.weekly_estimates_kg), 3)

    def test_improving_when_estimate_climbs_meaningfully_each_week(self):
        account = _make_account()
        for week_offset, weight in ((0, 90), (7, 100), (14, 112)):
            _log(
                account,
                movement_slug='agachamento-livre',
                weight_kg=weight,
                reps=5,
                performed_on=date(2026, 1, 5) + timedelta(days=week_offset),
            )

        trend = detect_one_rep_max_trend(account_id=account.pk, movement_slug='agachamento-livre')

        self.assertEqual(trend.label, 'improving')

    def test_declining_when_latest_week_drops_from_the_windows_peak(self):
        account = _make_account()
        for week_offset, weight in ((0, 110), (7, 108), (14, 95)):
            _log(
                account,
                movement_slug='agachamento-livre',
                weight_kg=weight,
                reps=5,
                performed_on=date(2026, 1, 5) + timedelta(days=week_offset),
            )

        trend = detect_one_rep_max_trend(account_id=account.pk, movement_slug='agachamento-livre')

        self.assertEqual(trend.label, 'declining')

    def test_only_the_best_estimate_of_each_week_counts(self):
        account = _make_account()
        # Duas sessoes na mesma semana (segunda e quinta) -- so a melhor
        # estimativa daquela semana entra na janela.
        _log(account, movement_slug='agachamento-livre', weight_kg=90, reps=5, performed_on=date(2026, 1, 5))
        _log(account, movement_slug='agachamento-livre', weight_kg=110, reps=5, performed_on=date(2026, 1, 8))
        for week_offset in (7, 14):
            _log(
                account,
                movement_slug='agachamento-livre',
                weight_kg=110,
                reps=5,
                performed_on=date(2026, 1, 5) + timedelta(days=week_offset),
            )

        trend = detect_one_rep_max_trend(account_id=account.pk, movement_slug='agachamento-livre')

        # As tres semanas ficam no mesmo patamar (110) -> plato, nao
        # "melhorando" por causa do set fraco de 90kg na primeira semana.
        self.assertEqual(trend.label, 'plateau')

    def test_sets_above_fifteen_effective_reps_are_excluded_from_the_trend(self):
        account = _make_account()
        # 20 reps nao gera estimativa valida -- semana fica sem dado, entao
        # so ha 2 semanas com estimativa -> insufficient_data mesmo com 3
        # semanas de registros.
        _log(account, movement_slug='agachamento-livre', weight_kg=50, reps=20, performed_on=date(2026, 1, 5))
        _log(account, movement_slug='agachamento-livre', weight_kg=100, reps=5, performed_on=date(2026, 1, 12))
        _log(account, movement_slug='agachamento-livre', weight_kg=100, reps=5, performed_on=date(2026, 1, 19))

        trend = detect_one_rep_max_trend(account_id=account.pk, movement_slug='agachamento-livre')

        self.assertEqual(trend.label, 'insufficient_data')

    def test_does_not_mix_different_movement_slugs(self):
        account = _make_account()
        for week_offset in (0, 7, 14):
            _log(
                account,
                movement_slug='hip-thrust-barbell',
                weight_kg=100,
                reps=5,
                performed_on=date(2026, 1, 5) + timedelta(days=week_offset),
            )
        # Variacao "irma" com carga bem diferente -- nunca deve entrar na
        # janela do slug acima (F-D do plano).
        _log(account, movement_slug='hip-thrust-machine', weight_kg=180, reps=5, performed_on=date(2026, 1, 19))

        trend = detect_one_rep_max_trend(account_id=account.pk, movement_slug='hip-thrust-barbell')

        self.assertEqual(trend.label, 'plateau')
        self.assertTrue(all(value < 150 for value in trend.weekly_estimates_kg))

    def test_does_not_leak_between_accounts(self):
        account_a = _make_account(email='a@example.com')
        account_b = _make_account(email='b@example.com')
        for week_offset in (0, 7, 14):
            _log(
                account_a,
                movement_slug='agachamento-livre',
                weight_kg=100,
                reps=5,
                performed_on=date(2026, 1, 5) + timedelta(days=week_offset),
            )

        trend_b = detect_one_rep_max_trend(account_id=account_b.pk, movement_slug='agachamento-livre')

        self.assertEqual(trend_b.label, 'insufficient_data')
