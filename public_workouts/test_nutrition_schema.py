"""
ARQUIVO: testes do contrato de payload de PublicWorkoutMealPlan (Entrega 6,
Fase 4 — docs/plans/public-workouts-escala-e-nutricao-corda.md, D.6).

POR QUE ELE EXISTE:
- Guardrails operacionais do plano: "nutrition_schema.py precisa de
  testes próprios (casos válidos e cada campo obrigatório faltando/
  malformado) antes de a Fase 4 ser considerada pronta" — mesmo padrão
  de cobertura que já existe para schema.py do treino.
"""

from django.test import TestCase

from .nutrition_schema import (
    MACRO_KEYS,
    NUTRITION_SCHEMA_VERSION,
    NutritionPayloadValidationError,
    assert_valid_payload,
    build_example_payload,
    validate_payload,
)


class NutritionSchemaValidationTests(TestCase):
    def test_example_payload_is_valid(self):
        self.assertEqual(validate_payload(build_example_payload()), [])

    def test_assert_valid_payload_does_not_raise_for_example(self):
        assert_valid_payload(build_example_payload())  # nao levanta

    def test_wrong_schema_version_is_rejected(self):
        payload = build_example_payload()
        payload['schema_version'] = 2
        errors = validate_payload(payload)
        self.assertTrue(any('schema_version' in error for error in errors))

    def test_missing_daily_targets_is_rejected(self):
        payload = build_example_payload()
        del payload['daily_targets']
        errors = validate_payload(payload)
        self.assertTrue(any('daily_targets' in error for error in errors))

    def test_daily_targets_missing_a_macro_key_is_rejected(self):
        payload = build_example_payload()
        del payload['daily_targets']['protein_g']
        errors = validate_payload(payload)
        self.assertTrue(any('daily_targets.protein_g' in error for error in errors))

    def test_negative_macro_value_is_rejected(self):
        payload = build_example_payload()
        payload['daily_targets']['kcal'] = -100
        errors = validate_payload(payload)
        self.assertTrue(any('daily_targets.kcal' in error for error in errors))

    def test_empty_meals_is_rejected(self):
        payload = build_example_payload()
        payload['meals'] = []
        errors = validate_payload(payload)
        self.assertTrue(any('meals' in error for error in errors))

    def test_meal_without_items_is_rejected(self):
        payload = build_example_payload()
        payload['meals'][0]['items'] = []
        errors = validate_payload(payload)
        self.assertTrue(any('items' in error for error in errors))

    def test_meal_missing_meal_id_is_rejected(self):
        payload = build_example_payload()
        del payload['meals'][0]['meal_id']
        errors = validate_payload(payload)
        self.assertTrue(any('meal_id' in error for error in errors))

    def test_duplicate_meal_id_is_rejected(self):
        payload = build_example_payload()
        second_meal = dict(payload['meals'][0])
        second_meal['label'] = 'Almoço'
        payload['meals'].append(second_meal)  # mesmo meal_id do primeiro
        errors = validate_payload(payload)
        self.assertTrue(any('duplicado' in error for error in errors))

    def test_item_without_food_or_quantity_is_rejected(self):
        payload = build_example_payload()
        del payload['meals'][0]['items'][0]['food']
        errors = validate_payload(payload)
        self.assertTrue(any('food' in error for error in errors))

    def test_item_macros_are_optional(self):
        payload = build_example_payload()
        payload['meals'][0]['items'][0] = {'food': 'Banana', 'quantity': '1 unidade'}
        self.assertEqual(validate_payload(payload), [])

    def test_item_with_partial_macros_is_rejected(self):
        # Se declarar macro por item, as 4 chaves precisam estar corretas —
        # nao aceita meio caminho (ex.: so kcal, sem os outros 3).
        payload = build_example_payload()
        payload['meals'][0]['items'][0] = {'food': 'Banana', 'quantity': '1 unidade', 'kcal': 90}
        errors = validate_payload(payload)
        self.assertTrue(len(errors) > 0)

    def test_substitutes_are_optional(self):
        payload = build_example_payload()
        del payload['meals'][0]['substitutes']
        self.assertEqual(validate_payload(payload), [])

    def test_malformed_substitute_is_rejected(self):
        payload = build_example_payload()
        payload['meals'][0]['substitutes'] = [{'food': 'Tapioca'}]  # sem quantity
        errors = validate_payload(payload)
        self.assertTrue(any('substitutes' in error for error in errors))

    def test_note_is_optional(self):
        payload = build_example_payload()
        del payload['meals'][0]['note']
        self.assertEqual(validate_payload(payload), [])

    def test_assert_valid_payload_raises_with_joined_message(self):
        payload = build_example_payload()
        del payload['daily_targets']
        with self.assertRaises(NutritionPayloadValidationError):
            assert_valid_payload(payload)

    def test_non_dict_payload_is_rejected_without_crashing(self):
        errors = validate_payload('nao e um dict')
        self.assertTrue(any('objeto' in error for error in errors))

    def test_macro_keys_and_version_are_stable(self):
        # Trava a forma publica do contrato — mudar isso e' mudanca de
        # schema, precisa de NUTRITION_SCHEMA_VERSION novo (D.6).
        self.assertEqual(MACRO_KEYS, ('kcal', 'protein_g', 'carbs_g', 'fat_g'))
        self.assertEqual(NUTRITION_SCHEMA_VERSION, 1)
