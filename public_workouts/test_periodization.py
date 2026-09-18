"""
ARQUIVO: testes de public_workouts/periodization.py (modelo canônico +
progressão de carga, Onda B3+ do CORDA).
"""

from datetime import date

from django.test import SimpleTestCase

from public_workouts.periodization import (
    PHASE_PROFILES,
    build_chart_points_from_weeks,
    current_phase_profile,
    current_week_number,
    suggest_progressive_load_kg,
)


def _payload_with_weeks(weeks, *, started_on='2026-01-05', program_id='juliana-2026-q1'):
    return {
        'program_id': program_id,
        'started_on': started_on,
        'periodization': {'weeks': weeks},
    }


_SIX_WEEKS = [
    {'week_number': 1, 'phase_type': 'adaptation'},
    {'week_number': 2, 'phase_type': 'volume'},
    {'week_number': 3, 'phase_type': 'strength_hypertrophy'},
    {'week_number': 4, 'phase_type': 'intensity'},
    {'week_number': 5, 'phase_type': 'peak'},
    {'week_number': 6, 'phase_type': 'deload'},
]


class CurrentWeekNumberTests(SimpleTestCase):
    def test_week_one_on_start_date(self):
        payload = _payload_with_weeks(_SIX_WEEKS, started_on='2026-01-05')

        self.assertEqual(current_week_number(payload, today=date(2026, 1, 5)), 1)
        self.assertEqual(current_week_number(payload, today=date(2026, 1, 11)), 1)

    def test_advances_one_week_per_seven_days(self):
        payload = _payload_with_weeks(_SIX_WEEKS, started_on='2026-01-05')

        self.assertEqual(current_week_number(payload, today=date(2026, 1, 12)), 2)
        self.assertEqual(current_week_number(payload, today=date(2026, 2, 2)), 5)  # +4 semanas

    def test_cycles_after_len_weeks(self):
        payload = _payload_with_weeks(_SIX_WEEKS, started_on='2026-01-05')

        # 6 semanas depois do inicio -> volta pra semana 1 (novo ciclo)
        self.assertEqual(current_week_number(payload, today=date(2026, 2, 16)), 1)

    def test_none_before_start_date(self):
        payload = _payload_with_weeks(_SIX_WEEKS, started_on='2026-01-05')

        self.assertIsNone(current_week_number(payload, today=date(2026, 1, 1)))

    def test_none_without_weeks(self):
        payload = {'program_id': 'x', 'started_on': '2026-01-05', 'periodization': {}}

        self.assertIsNone(current_week_number(payload, today=date(2026, 1, 10)))

    def test_none_without_periodization_at_all(self):
        payload = {'program_id': 'x', 'started_on': '2026-01-05'}

        self.assertIsNone(current_week_number(payload, today=date(2026, 1, 10)))

    def test_none_without_started_on(self):
        payload = {'program_id': 'x', 'periodization': {'weeks': _SIX_WEEKS}}

        self.assertIsNone(current_week_number(payload, today=date(2026, 1, 10)))


class CurrentPhaseProfileTests(SimpleTestCase):
    def test_returns_matching_phase_profile(self):
        payload = _payload_with_weeks(_SIX_WEEKS, started_on='2026-01-05')

        phase = current_phase_profile(payload, today=date(2026, 1, 19))  # semana 3

        self.assertEqual(phase.key, 'strength_hypertrophy')

    def test_none_when_week_number_has_no_matching_row(self):
        # 2 linhas (len=2, entao current_week_number pede semana 1 no dia do
        # inicio) mas nenhuma delas e' a semana 1 -- lista com buraco real.
        gapped_weeks = [{'week_number': 2, 'phase_type': 'volume'}, {'week_number': 3, 'phase_type': 'peak'}]
        payload = _payload_with_weeks(gapped_weeks, started_on='2026-01-05')

        self.assertIsNone(current_phase_profile(payload, today=date(2026, 1, 5)))

    def test_none_without_weeks(self):
        payload = {'program_id': 'x', 'started_on': '2026-01-05'}

        self.assertIsNone(current_phase_profile(payload, today=date(2026, 1, 10)))


class BuildChartPointsFromWeeksTests(SimpleTestCase):
    def test_produces_one_point_per_week_with_legacy_compatible_shape(self):
        points = build_chart_points_from_weeks(_SIX_WEEKS)

        self.assertEqual(len(points), 6)
        for point in points:
            self.assertIn('label', point)
            self.assertIn('focus', point)
            self.assertIn('reps', point)
            self.assertIn('color', point)
            self.assertIn('bg', point)
            self.assertIn('fg', point)
            self.assertIn('h', point)
            self.assertTrue(0 <= point['h'] <= 100)

    def test_labels_are_sequential_week_numbers(self):
        points = build_chart_points_from_weeks(_SIX_WEEKS)

        self.assertEqual([p['label'] for p in points], ['S1', 'S2', 'S3', 'S4', 'S5', 'S6'])

    def test_peak_has_the_tallest_bar(self):
        points = build_chart_points_from_weeks(_SIX_WEEKS)

        peak_point = next(p for p in points if p['focus'] == PHASE_PROFILES['peak'].label)
        self.assertEqual(peak_point['h'], 100)
        for point in points:
            self.assertLessEqual(point['h'], peak_point['h'])

    def test_unknown_phase_type_is_skipped_not_crashed(self):
        weeks = [{'week_number': 1, 'phase_type': 'nao-existe'}]

        self.assertEqual(build_chart_points_from_weeks(weeks), [])

    def test_empty_weeks_returns_empty_list(self):
        self.assertEqual(build_chart_points_from_weeks([]), [])


class SuggestProgressiveLoadKgTests(SimpleTestCase):
    def _payload(self, **overrides):
        payload = _payload_with_weeks(_SIX_WEEKS, started_on='2026-01-05', program_id='juliana-2026-q1')
        payload.update(overrides)
        return payload

    def test_none_without_any_log(self):
        payload = self._payload()

        result = suggest_progressive_load_kg(
            payload=payload, current_phase=PHASE_PROFILES['volume'], last_log=None,
        )

        self.assertIsNone(result)

    def test_none_when_log_weight_is_missing(self):
        payload = self._payload()
        log = {'weight_kg': None, 'performed_on': '2026-01-05', 'program_id': 'juliana-2026-q1'}

        result = suggest_progressive_load_kg(payload=payload, current_phase=PHASE_PROFILES['volume'], last_log=log)

        self.assertIsNone(result)

    def test_none_when_log_is_from_a_different_program(self):
        payload = self._payload()
        log = {'weight_kg': 80.0, 'performed_on': '2026-01-05', 'program_id': 'juliana-2025-q4'}

        result = suggest_progressive_load_kg(payload=payload, current_phase=PHASE_PROFILES['volume'], last_log=log)

        self.assertIsNone(result)

    def test_scales_by_ratio_of_phase_midpoints(self):
        payload = self._payload()
        # log feito na semana 1 (Adaptacao, mid=56%), sugestao pra semana 2 (Volume, mid=67%)
        log = {'weight_kg': 80.0, 'performed_on': '2026-01-05', 'program_id': 'juliana-2026-q1'}

        result = suggest_progressive_load_kg(payload=payload, current_phase=PHASE_PROFILES['volume'], last_log=log)

        expected_raw = 80.0 * (67 / 56)
        expected_rounded = round(expected_raw / 2.5) * 2.5
        self.assertEqual(result, expected_rounded)
        self.assertGreater(result, 80.0)  # Volume > Adaptacao em intensidade -> sugere mais peso

    def test_deload_scales_load_down(self):
        payload = self._payload()
        # log feito na semana 5 (Pico, mid=93.5%), sugestao pra semana 6 (Deload, mid=57.5%)
        log = {'weight_kg': 100.0, 'performed_on': '2026-02-02', 'program_id': 'juliana-2026-q1'}

        result = suggest_progressive_load_kg(payload=payload, current_phase=PHASE_PROFILES['deload'], last_log=log)

        self.assertLess(result, 100.0)

    def test_same_phase_as_log_returns_same_weight_rounded(self):
        payload = self._payload()
        log = {'weight_kg': 82.5, 'performed_on': '2026-01-12', 'program_id': 'juliana-2026-q1'}  # semana 2, Volume

        result = suggest_progressive_load_kg(payload=payload, current_phase=PHASE_PROFILES['volume'], last_log=log)

        self.assertEqual(result, 82.5)

    def test_never_exceeds_one_rep_max_ceiling(self):
        payload = self._payload()
        # log MUITO baixo numa fase de intensidade baixa, mas 1RM baixo tambem --
        # razao pura sugeriria mais que o teto seguro da fase atual.
        log = {'weight_kg': 90.0, 'performed_on': '2026-01-05', 'program_id': 'juliana-2026-q1'}  # Adaptacao

        result = suggest_progressive_load_kg(
            payload=payload, current_phase=PHASE_PROFILES['peak'], last_log=log, one_rep_max_kg=100.0,
        )

        # tetp da fase Pico e' 97% do 1RM estimado
        ceiling = round((97 / 100) * 100.0 / 2.5) * 2.5
        self.assertLessEqual(result, ceiling)

    def test_none_when_log_predates_periodization_weeks(self):
        payload = self._payload()
        log = {'weight_kg': 80.0, 'performed_on': '2025-01-01', 'program_id': 'juliana-2026-q1'}

        result = suggest_progressive_load_kg(payload=payload, current_phase=PHASE_PROFILES['volume'], last_log=log)

        self.assertIsNone(result)

    def test_rounds_to_nearest_two_point_five(self):
        payload = self._payload()
        log = {'weight_kg': 77.0, 'performed_on': '2026-01-05', 'program_id': 'juliana-2026-q1'}

        result = suggest_progressive_load_kg(payload=payload, current_phase=PHASE_PROFILES['volume'], last_log=log)

        self.assertEqual(result % 2.5, 0)


class HoldLoadPhaseTests(SimpleTestCase):
    """Bloco de corte do Bruno: `maintenance`/`test` tem `hold_load=True`
    -- a meta real é "não progredir carga, segurar a carga" (vnote real
    dele), então NUNCA escala pela razão de %RM entre fases, mesmo quando
    a fase de agora tem %RM-meio bem maior que a fase de quando o log foi
    feito (o que aconteceria erroneamente se caísse no caminho normal)."""

    _BRUNO_WEEKS = [
        {'week_number': 1, 'phase_type': 'adaptation'},
        {'week_number': 2, 'phase_type': 'maintenance'},
        {'week_number': 3, 'phase_type': 'maintenance'},
        {'week_number': 4, 'phase_type': 'maintenance'},
        {'week_number': 5, 'phase_type': 'test'},
        {'week_number': 6, 'phase_type': 'deload'},
    ]

    def _payload(self, **overrides):
        payload = _payload_with_weeks(self._BRUNO_WEEKS, started_on='2026-01-05', program_id='bruno-2026-q1')
        payload.update(overrides)
        return payload

    def test_maintenance_holds_the_last_logged_weight_unchanged(self):
        payload = self._payload()
        # log feito na semana 1 (Adaptacao, mid=56%) -- se escalasse pela
        # razao normal pra Manutencao (mid=73.5%), sugeriria ~105kg. Com
        # hold_load, tem que devolver os mesmos 80kg.
        log = {'weight_kg': 80.0, 'performed_on': '2026-01-05', 'program_id': 'bruno-2026-q1'}

        result = suggest_progressive_load_kg(payload=payload, current_phase=PHASE_PROFILES['maintenance'], last_log=log)

        self.assertEqual(result, 80.0)

    def test_maintenance_to_maintenance_also_holds(self):
        payload = self._payload()
        log = {'weight_kg': 80.0, 'performed_on': '2026-01-12', 'program_id': 'bruno-2026-q1'}  # semana 2, Manutencao

        result = suggest_progressive_load_kg(payload=payload, current_phase=PHASE_PROFILES['maintenance'], last_log=log)

        self.assertEqual(result, 80.0)

    def test_test_phase_also_holds_the_same_weight(self):
        payload = self._payload()
        log = {'weight_kg': 80.0, 'performed_on': '2026-01-05', 'program_id': 'bruno-2026-q1'}  # semana 1, Adaptacao

        result = suggest_progressive_load_kg(payload=payload, current_phase=PHASE_PROFILES['test'], last_log=log)

        self.assertEqual(result, 80.0)

    def test_hold_load_never_needs_to_resolve_the_logged_phase(self):
        # Log de ANTES de periodization.weeks existir (fase nao resolvivel)
        # -- caminho normal devolveria None aqui (ver
        # test_none_when_log_predates_periodization_weeks acima), mas
        # hold_load nem precisa saber a fase de quando o log foi feito.
        payload = self._payload()
        log = {'weight_kg': 80.0, 'performed_on': '2025-01-01', 'program_id': 'bruno-2026-q1'}

        result = suggest_progressive_load_kg(payload=payload, current_phase=PHASE_PROFILES['maintenance'], last_log=log)

        self.assertEqual(result, 80.0)

    def test_hold_load_still_respects_one_rep_max_ceiling(self):
        payload = self._payload()
        log = {'weight_kg': 95.0, 'performed_on': '2026-01-05', 'program_id': 'bruno-2026-q1'}

        result = suggest_progressive_load_kg(
            payload=payload, current_phase=PHASE_PROFILES['maintenance'], last_log=log, one_rep_max_kg=100.0,
        )

        # teto da fase Manutencao e' 80% do 1RM estimado -- abaixo do log de 95kg
        ceiling = round((80 / 100) * 100.0 / 2.5) * 2.5
        self.assertEqual(result, ceiling)
        self.assertLess(result, 95.0)

    def test_maintenance_and_test_are_the_only_hold_load_phases(self):
        hold_load_keys = {key for key, phase in PHASE_PROFILES.items() if phase.hold_load}

        self.assertEqual(hold_load_keys, {'maintenance', 'test'})
