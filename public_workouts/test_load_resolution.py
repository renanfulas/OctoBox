"""L1: origem e fallback de kg sem banco ou template."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from public_workouts.load_resolution import resolve_movement_load


class LoadResolutionTest(SimpleTestCase):
    def test_fixed_kg_has_explicit_coach_origin(self):
        result = resolve_movement_load(
            movement={'movement_slug': 'agachamento', 'load_type': 'fixed_kg', 'load_value': 60},
            payload={}, phase=None, one_rep_max_by_movement={},
        )
        self.assertEqual((result.value_kg, result.reason_code), (60, 'coach_fixed'))
        self.assertEqual(result.as_template_dict(), {
            'kind': 'fixed_kg', 'value_kg': 60, 'percentage': None,
            'show_registration_hint': False,
        })

    def test_percent_without_rm_explains_missing_anchor(self):
        result = resolve_movement_load(
            movement={'movement_slug': 'agachamento', 'load_type': 'percentage_of_rm', 'load_value': 75},
            payload={}, phase=None, one_rep_max_by_movement={},
        )
        self.assertIsNone(result.value_kg)
        self.assertEqual(result.reason_code, 'rm_missing')
        self.assertTrue(result.editable)
        self.assertIn('carga alvo da Top', result.fallback_note)

    def test_last_top_is_reference_not_calculated_percent(self):
        top = SimpleNamespace(weight_kg=Decimal('50.00'), reps=8, rir=Decimal('2.0'),
                              performed_on=date(2026, 10, 1), program_id='prog')
        result = resolve_movement_load(
            movement={'movement_slug': 'agachamento', 'load_type': 'percentage_of_rm', 'load_value': 75},
            payload={}, phase=None, one_rep_max_by_movement={},
            progress_snapshots={'agachamento': SimpleNamespace(latest_top_set=top)},
        )
        self.assertEqual(result.kind, 'last_observed')
        self.assertEqual(result.reason_code, 'rm_missing_last_top_reference')
        self.assertEqual(result.value_kg, Decimal('50.00'))

    def test_no_usable_data_returns_manual_exit(self):
        result = resolve_movement_load(
            movement={'movement_slug': 'agachamento', 'load_type': 'free', 'load_value': None,
                      'reps_spec': 'texto aberto', 'rir_spec': ''},
            payload={}, phase=None, one_rep_max_by_movement={},
        )
        self.assertEqual(result.kind, 'free')
        self.assertEqual(result.reason_code, 'no_usable_anchor')
        self.assertIsNone(result.value_kg)

    def test_ambiguous_text_with_existing_rm_does_not_ask_for_first_reference(self):
        result = resolve_movement_load(
            movement={'movement_slug': 'agachamento', 'load_type': 'free', 'load_value': None,
                      'reps_spec': 'Top crescente', 'rir_spec': ''},
            payload={}, phase=None,
            one_rep_max_by_movement={'agachamento': {'value_kg': 100}},
        )
        self.assertFalse(result.show_registration_hint)
        self.assertIn('RM registrado', result.fallback_note)
