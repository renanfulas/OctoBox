"""L1: contrato guiado sem banco, HTTP ou efeitos externos."""

from copy import deepcopy
from decimal import Decimal

from django.test import SimpleTestCase

from public_workouts.guided_prescription import (
    expand_guided_prescription, propose_guided_prescription, validate_guided_prescription,
)
from public_workouts.guided_workout import build_guided_series
from public_workouts.schema import build_example_payload, validate_payload


def _guided():
    return {'version': 1, 'stages': [
        {'stage_id': 'prep', 'role': 'warmup', 'min_sets': 1, 'max_sets': 2,
         'reps_min': 6, 'reps_max': 8, 'rest_seconds': 60,
         'load_rule': {'kind': 'percent_of_top', 'start_percent': 40, 'end_percent': 55}},
        {'stage_id': 'top', 'role': 'top_set', 'min_sets': 2, 'max_sets': 3,
         'reps_min': 6, 'reps_max': 8, 'rest_seconds': 120,
         'load_rule': {'kind': 'suggested_top'}},
    ]}


class GuidedPrescriptionContractTest(SimpleTestCase):
    def test_valid_contract_expands_required_optional_and_rest(self):
        rows = expand_guided_prescription(_guided(), top_weight_kg=100)
        self.assertEqual(len(rows), 5)
        self.assertEqual([row['required'] for row in rows], [True, False, True, True, False])
        self.assertEqual([row['weight_kg'] for row in rows], [40, 55, 100, 100, 100])
        self.assertEqual(rows[2]['stage_id'], 'top')
        self.assertEqual(rows[2]['rest_seconds'], 120)

    def test_missing_anchor_leaves_kg_editable_and_empty(self):
        rows = expand_guided_prescription(_guided())
        self.assertTrue(all(row['weight_kg'] is None for row in rows))
        self.assertEqual([row['top_factor'] for row in rows], [.4, .55, 1.0, 1.0, 1.0])

    def test_fixed_load_is_not_recalculated_from_student_top_target(self):
        guided = _guided()
        guided['stages'][0]['load_rule'] = {'kind': 'fixed_kg', 'value_kg': 20}
        rows = expand_guided_prescription(guided, top_weight_kg=100)
        self.assertEqual(rows[0]['weight_kg'], 20)
        self.assertIsNone(rows[0]['top_factor'])

    def test_legacy_ramp_exposes_same_factors_without_an_anchor(self):
        rows = build_guided_series({'reps_spec': '2× Prep → 1× Feeder → 2× Top (6-8)'})
        self.assertEqual([row['top_factor'] for row in rows], [.4, .55, .7, 1.0, 1.0])
        self.assertTrue(all(row['weight_kg'] is None for row in rows))

    def test_decimal_last_top_is_usable_anchor(self):
        rows = expand_guided_prescription(_guided(), top_weight_kg=Decimal('100.00'))
        self.assertEqual(rows[0]['weight_kg'], 40.0)

    def test_invalid_and_duplicate_stages_are_rejected_by_schema(self):
        payload = build_example_payload()
        guided = _guided()
        guided['stages'][1]['stage_id'] = 'prep'
        guided['stages'][1]['load_rule'] = {'kind': 'percent_of_top', 'start_percent': 80, 'end_percent': 60}
        payload['days'][0]['blocks'][0]['movements'][0]['guided_prescription'] = guided
        errors = validate_payload(payload)
        self.assertTrue(any('identificador repetido' in error for error in errors))
        self.assertTrue(any('faixa percentual inválida' in error for error in errors))

    def test_structured_is_source_even_if_legacy_text_is_ambiguous(self):
        movement = {'reps_spec': 'texto aberto', 'guided_prescription': _guided()}
        self.assertEqual(len(build_guided_series(movement)), 5)
        self.assertEqual(build_guided_series(movement)[0]['role'], 'warmup')

    def test_legacy_text_keeps_freeform_exit(self):
        self.assertEqual(build_guided_series({'reps_spec': 'texto aberto'})[0]['role'], 'legacy_unknown')
        self.assertIsNone(propose_guided_prescription({'reps_spec': 'texto aberto'}))

    def test_proposal_preserves_range_but_never_changes_input(self):
        movement = {'reps_spec': '2–3× Top (6–8)'}
        original = deepcopy(movement)
        proposal = propose_guided_prescription(movement)
        self.assertEqual(movement, original)
        self.assertEqual((proposal['stages'][0]['min_sets'], proposal['stages'][0]['max_sets']), (2, 3))
        self.assertEqual(validate_guided_prescription(proposal), [])

    def test_stage_first_pilot_preserves_split_prep_and_optional_amrap(self):
        movement = {'reps_spec': 'Preparat. 2x 10 / 6 → Feeder 1x 10 → Top Set 3x 8-12 → AMRAP 1x Opcional'}
        original = deepcopy(movement)
        proposal = propose_guided_prescription(movement)
        self.assertEqual(movement, original)
        self.assertEqual(validate_guided_prescription(proposal), [])
        rows = expand_guided_prescription(proposal, top_weight_kg=100)
        self.assertEqual([row['role'] for row in rows],
                         ['warmup', 'warmup', 'feeder', 'top_set', 'top_set', 'top_set', 'max_set'])
        self.assertEqual([row['reps'] for row in rows], [10, 6, 10, 8, 8, 8, None])
        self.assertEqual([row['required'] for row in rows], [True] * 6 + [False])
        self.assertEqual([row['weight_kg'] for row in rows], [40.0, 55.0, 70.0, 100, 100, 100, 100])

    def test_stage_first_range_and_progressive_prep_are_reviewable(self):
        movement = {'reps_spec': 'Preparat. 2x Progressivo → Feeder 1x 8-10 → Top Set 2-3x 8-12'}
        proposal = propose_guided_prescription(movement)
        self.assertEqual(validate_guided_prescription(proposal), [])
        self.assertEqual([(stage['min_sets'], stage['max_sets']) for stage in proposal['stages']],
                         [(2, 2), (1, 1), (2, 3)])
        self.assertIsNone(proposal['stages'][0]['reps_min'])

    def test_stage_first_duration_and_extra_instructions_stay_freeform(self):
        for spec in ('Top Set 2-3x 30-45 s', 'Top Set 3x 8-12 → 1x dropset',
                     'Feeder 1x 8-10 Opcional'):
            self.assertIsNone(propose_guided_prescription({'reps_spec': spec}))

    def test_non_scalar_payload_does_not_crash_validator(self):
        guided = _guided()
        guided['stages'][0]['role'] = []
        guided['stages'][0]['load_rule']['kind'] = []
        errors = validate_guided_prescription(guided)
        self.assertTrue(any('.role:' in error for error in errors))
        self.assertTrue(any('.load_rule.kind:' in error for error in errors))
