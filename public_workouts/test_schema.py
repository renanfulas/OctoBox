"""
ARQUIVO: testes do contrato de payload da Onda S0 do CORDA.

POR QUE ELE EXISTE:
- e o "pronto quando" da Onda S0 (docs/plans/public-workouts-produtizacao-corda.md):
  um payload de exemplo precisa validar contra o schema.

NOTA (Onda A1, Fatia B): este arquivo tinha uma `ServicesStubTests` que
testava `public_workouts/services_stub.py` (S1/S2/S3 fake, sem tocar
banco). Removida junto com o stub — S1 (Fatia A) e S2/S3 (Fatia B) agora
sao reais em `services.py`; testa-los la (`test_program.py`) e o lugar
certo, nao aqui.
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
