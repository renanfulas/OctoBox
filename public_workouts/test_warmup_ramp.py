"""
ARQUIVO: testes de public_workouts/warmup_ramp.py (ramp de Prep/Feeder em
kg, relativo ao Top set — Onda B3+ do CORDA).
"""

from django.test import SimpleTestCase

from public_workouts.warmup_ramp import extract_leading_set_count, stage_ramp_kg


class ExtractLeadingSetCountTests(SimpleTestCase):
    def test_single_number_prefix(self):
        self.assertEqual(extract_leading_set_count('1× Feeder'), 1)
        self.assertEqual(extract_leading_set_count('4× Top (6-8)'), 4)

    def test_range_prefix_averages(self):
        self.assertEqual(extract_leading_set_count('2-3× Prep'), 2)  # round(2.5) -> 2 (banker's rounding)

    def test_ascii_x_is_also_recognized(self):
        self.assertEqual(extract_leading_set_count('3x Top (8-10)'), 3)

    def test_no_recognizable_prefix_defaults_to_one(self):
        self.assertEqual(extract_leading_set_count('Top (crescente)'), 1)

    def test_never_returns_zero(self):
        self.assertGreaterEqual(extract_leading_set_count(''), 1)


class StageRampKgTests(SimpleTestCase):
    def test_top_stage_is_always_the_reference_weight(self):
        self.assertEqual(stage_ramp_kg(stage='top', set_count=3, top_weight_kg=100.0), [100.0, 100.0, 100.0])

    def test_max_stage_uses_same_weight_as_top(self):
        self.assertEqual(stage_ramp_kg(stage='max', set_count=1, top_weight_kg=100.0), [100.0])

    def test_prep_single_set_uses_range_midpoint(self):
        # faixa 40-55% -> meio = 47.5% de 100 = 47.5, ja e multiplo de 2.5
        self.assertEqual(stage_ramp_kg(stage='prep', set_count=1, top_weight_kg=100.0), [47.5])

    def test_feeder_single_set_uses_range_midpoint(self):
        # faixa 60-80% -> meio = 70% de 100 = 70.0
        self.assertEqual(stage_ramp_kg(stage='feeder', set_count=1, top_weight_kg=100.0), [70.0])

    def test_prep_with_multiple_sets_ramps_from_low_to_high(self):
        weights = stage_ramp_kg(stage='prep', set_count=2, top_weight_kg=100.0)

        self.assertEqual(len(weights), 2)
        self.assertEqual(weights[0], 40.0)  # piso da faixa
        self.assertEqual(weights[1], 55.0)  # teto da faixa
        self.assertLess(weights[0], weights[1])

    def test_feeder_stays_below_working_set_threshold(self):
        # fonte (BarBend/StrongFirst): qualquer set >=85-90% ja conta como
        # working set -- o Feeder nunca pode chegar la.
        weights = stage_ramp_kg(stage='feeder', set_count=3, top_weight_kg=100.0)

        self.assertTrue(all(w < 85.0 for w in weights))

    def test_prep_always_lighter_than_feeder(self):
        prep = stage_ramp_kg(stage='prep', set_count=1, top_weight_kg=100.0)
        feeder = stage_ramp_kg(stage='feeder', set_count=1, top_weight_kg=100.0)

        self.assertLess(prep[0], feeder[0])

    def test_unknown_stage_returns_empty_list(self):
        self.assertEqual(stage_ramp_kg(stage='plain', set_count=2, top_weight_kg=100.0), [])

    def test_without_top_weight_returns_empty_list(self):
        self.assertEqual(stage_ramp_kg(stage='prep', set_count=2, top_weight_kg=None), [])
        self.assertEqual(stage_ramp_kg(stage='prep', set_count=2, top_weight_kg=0), [])

    def test_results_are_rounded_to_nearest_two_point_five(self):
        weights = stage_ramp_kg(stage='prep', set_count=3, top_weight_kg=83.0)

        for weight in weights:
            self.assertEqual(weight % 2.5, 0)

    def test_zero_or_negative_set_count_still_produces_at_least_one_weight(self):
        self.assertEqual(len(stage_ramp_kg(stage='feeder', set_count=0, top_weight_kg=100.0)), 1)
