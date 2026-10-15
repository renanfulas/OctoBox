"""
ARQUIVO: testes de load_suggestion.py (Caminho 4 — exercício sem fase
canônica de periodização, Onda B3+ do CORDA).

POR QUE ELE EXISTE:
- os textos testados aqui vêm literalmente dos 10 HTMLs reais (grep feito
  durante o planejamento desta fatia) — cobrem os formatos reais de
  reps_spec/rir_spec, não casos hipotéticos.
"""

from django.test import SimpleTestCase

from public_workouts.load_suggestion import (
    extract_rir_target,
    extract_top_set_reps_target,
    suggest_movement_load,
)


class ExtractTopSetRepsTargetTests(SimpleTestCase):
    def test_single_phase_with_parenthesized_range(self):
        self.assertEqual(extract_top_set_reps_target('3× Top (8-10)'), (8.0, 10.0))

    def test_multi_phase_picks_the_top_segment(self):
        self.assertEqual(extract_top_set_reps_target('2-3× Prep → 1× Feeder → 3× Top (6-8)'), (6.0, 8.0))

    def test_bare_setsx_range_without_top_word(self):
        # johnespanha.html: "3× (12-15)" -- sem a palavra "Top", 1 fase so'
        self.assertEqual(extract_top_set_reps_target('3× (12-15)'), (12.0, 15.0))

    def test_trailing_note_after_parens_is_ignored(self):
        self.assertEqual(extract_top_set_reps_target('3× Top (8-10) · pausa 1s'), (8.0, 10.0))

    def test_ramping_top_set_without_a_number_returns_none(self):
        # henrique.html: "Top (crescente)" -- carga em rampa, sem alvo fixo
        self.assertIsNone(extract_top_set_reps_target('Feeder → 3× Top (crescente) → 1× Max'))

    def test_prose_dialect_without_arrow_never_guesses_first_number(self):
        # john.html: "1" antes do alvo de verdade (6-10) -- sem parenteses
        # nem "x" claro delimitando, tem que devolver None, nunca 1.
        self.assertIsNone(extract_top_set_reps_target('1 preparatória + 1 feeder + 3 top sets · 6-10 reps'))

    def test_multi_phase_without_any_top_labeled_segment_returns_none(self):
        # juliana.html: "2× 8 pesado → 2× 20 leve" -- nenhum segmento diz "Top"
        self.assertIsNone(extract_top_set_reps_target('2× 8 pesado → 2× 20 leve'))

    def test_empty_string_returns_none(self):
        self.assertIsNone(extract_top_set_reps_target(''))

    def test_single_value_in_parens_returns_same_value_twice(self):
        self.assertEqual(extract_top_set_reps_target('3× Top (10)'), (10.0, 10.0))

    def test_amrap_segment_is_never_picked_over_top(self):
        # thaislima.html: top vem antes do amrap -- so' o Top conta.
        self.assertEqual(
            extract_top_set_reps_target('2× Prep → 1× Feeder → 3× Top (8-10) → 1× AMRAP'), (8.0, 10.0),
        )


class ExtractRirTargetTests(SimpleTestCase):
    def test_single_value(self):
        self.assertEqual(extract_rir_target('RIR 2'), 2.0)

    def test_range_averages(self):
        self.assertEqual(extract_rir_target('RIR 1-2'), 1.5)

    def test_trailing_note_after_rir_is_ignored(self):
        self.assertEqual(extract_rir_target('RIR 1 · carga mais pesada'), 1.0)

    def test_non_rir_text_returns_none_never_assumes_zero(self):
        self.assertIsNone(extract_rir_target('Isometria'))

    def test_empty_string_returns_none(self):
        self.assertIsNone(extract_rir_target(''))


class SuggestMovementLoadTests(SimpleTestCase):
    def test_computes_kg_when_everything_is_available(self):
        movement = {'reps_spec': '3× Top (6-8)', 'rir_spec': 'RIR 1-2'}

        result = suggest_movement_load(movement=movement, one_rep_max_kg=100.0)

        self.assertIsNotNone(result)
        self.assertGreater(result['value_kg'], 0)
        self.assertEqual(result['value_kg'] % 2.5, 0)

    def test_none_without_one_rep_max(self):
        movement = {'reps_spec': '3× Top (6-8)', 'rir_spec': 'RIR 2'}

        self.assertIsNone(suggest_movement_load(movement=movement, one_rep_max_kg=None))

    def test_none_when_reps_target_is_ambiguous(self):
        movement = {'reps_spec': 'Feeder → 3× Top (crescente) → 1× Max', 'rir_spec': 'RIR 2'}

        self.assertIsNone(suggest_movement_load(movement=movement, one_rep_max_kg=100.0))

    def test_none_when_rir_is_not_extractable(self):
        movement = {'reps_spec': '3× Top (6-8)', 'rir_spec': 'Isometria'}

        self.assertIsNone(suggest_movement_load(movement=movement, one_rep_max_kg=100.0))

    def test_none_when_reps_spec_missing_entirely(self):
        movement = {'rir_spec': 'RIR 2'}

        self.assertIsNone(suggest_movement_load(movement=movement, one_rep_max_kg=100.0))
