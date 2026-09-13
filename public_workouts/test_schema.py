"""
ARQUIVO: testes do contrato de payload da Onda S0 do CORDA.

POR QUE ELE EXISTE:
- e o "pronto quando" da Onda S0 (docs/plans/public-workouts-produtizacao-corda.md):
  um payload de exemplo precisa validar contra o schema, e o stub de S1/S2/S3
  precisa devolver algo utilizavel sem tocar banco nem a Frente A.
"""

from django.test import TestCase

from .schema import (
    ACCENT_VARIANTS,
    LOAD_TYPES,
    PayloadValidationError,
    assert_valid_payload,
    build_example_payload,
    validate_payload,
)
from .services_stub import build_student_package, get_active_program, record_load


class SchemaValidationTests(TestCase):
    def test_example_payload_is_valid(self):
        self.assertEqual(validate_payload(build_example_payload()), [])

    def test_assert_valid_payload_does_not_raise_for_example(self):
        assert_valid_payload(build_example_payload())  # nao levanta

    def test_missing_required_field_is_reported(self):
        payload = build_example_payload()
        del payload['program_id']
        errors = validate_payload(payload)
        self.assertTrue(any('program_id' in error for error in errors))

    def test_unknown_load_type_is_rejected(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['load_type'] = 'inventado'
        errors = validate_payload(payload)
        self.assertTrue(any('load_type' in error for error in errors))

    def test_empty_days_is_rejected(self):
        payload = build_example_payload()
        payload['days'] = []
        errors = validate_payload(payload)
        self.assertTrue(any('days' in error for error in errors))

    def test_assert_valid_payload_raises_for_broken_payload(self):
        payload = build_example_payload()
        payload['weeks'] = -1
        with self.assertRaises(PayloadValidationError):
            assert_valid_payload(payload)

    def test_accent_variants_match_documented_vocabulary(self):
        self.assertEqual(ACCENT_VARIANTS, ('F', 'M', None))

    def test_load_types_match_documented_vocabulary(self):
        self.assertEqual(LOAD_TYPES, ('free', 'fixed_kg', 'percentage_of_rm'))


class ServicesStubTests(TestCase):
    """A Frente B programa contra isto ate A1 entregar as funcoes de verdade."""

    def test_get_active_program_returns_payload_valid_by_schema(self):
        payload = get_active_program(slug='juliana')
        self.assertIsNotNone(payload)
        self.assertEqual(validate_payload(payload), [])
        self.assertIn('juliana', payload['program_id'])

    def test_build_student_package_has_the_s2_shape(self):
        package = build_student_package(student_identity_id=1, slug='juliana')
        self.assertEqual(
            set(package),
            {'last_load_by_movement', 'one_rep_max_by_movement', 'substitutions', 'access_until'},
        )

    def test_record_load_echoes_input_without_persisting(self):
        result = record_load(
            student_identity_id=1,
            movement_slug='agachamento-livre',
            weight_kg=100,
            reps=8,
            rir=2,
            performed_on='2026-01-05',
            idempotency_key='abc123',
        )
        self.assertEqual(result['movement_slug'], 'agachamento-livre')
        self.assertEqual(result['weight_kg'], 100)
        self.assertEqual(result['idempotency_key'], 'abc123')
