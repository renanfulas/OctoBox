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

    def test_cardio_and_periodization_are_optional(self):
        # Aditivo ao contrato congelado: ausentes = cliente sem essas abas
        # no HTML legado (maioria dos programas ja publicados antes desta
        # fatia) -- payload continua valido sem elas.
        payload = build_example_payload()
        self.assertNotIn('cardio', payload)
        self.assertNotIn('periodization', payload)
        self.assertEqual(validate_payload(payload), [])

    def test_valid_cardio_passes(self):
        payload = build_example_payload()
        payload['cardio'] = {
            'sessions': [
                {
                    'title': 'LISS leve',
                    'badge': 'Quarta · pós-treino',
                    'details': [{'label': 'Duração', 'value': '20 min contínuos'}],
                    'note': 'Feito depois do treino de superior.',
                },
            ],
        }
        self.assertEqual(validate_payload(payload), [])

    def test_cardio_without_sessions_is_rejected(self):
        payload = build_example_payload()
        payload['cardio'] = {'sessions': []}
        errors = validate_payload(payload)
        self.assertTrue(any('cardio.sessions' in error for error in errors))

    def test_cardio_session_missing_title_is_rejected(self):
        payload = build_example_payload()
        payload['cardio'] = {'sessions': [{'badge': '', 'details': [], 'note': ''}]}
        errors = validate_payload(payload)
        self.assertTrue(any('title' in error for error in errors))

    def test_valid_periodization_passes(self):
        payload = build_example_payload()
        payload['periodization'] = {
            'weeks_table': [
                {'week': 'Semana 1', 'focus': 'Adaptação', 'reps': 'Teto da faixa', 'guidance': 'Carga base'},
            ],
            'volume_table': [
                {'muscle_group': 'Quadríceps', 'sets_per_week': '~22', 'frequency': '2x/sem', 'where': 'Terça + Quinta'},
            ],
            'note': 'Respeite o deload da última semana.',
            'chart': [
                {'label': 'S1', 'focus': 'Adaptação', 'reps': 'Teto', 'color': '#FB7185', 'bg': '#FFF1F2', 'fg': '#BE123C', 'h': 65},
            ],
        }
        self.assertEqual(validate_payload(payload), [])

    def test_periodization_without_weeks_table_is_rejected(self):
        payload = build_example_payload()
        payload['periodization'] = {'weeks_table': [], 'volume_table': [], 'note': '', 'chart': []}
        errors = validate_payload(payload)
        self.assertTrue(any('weeks_table' in error for error in errors))

    def test_periodization_chart_height_out_of_range_is_rejected(self):
        payload = build_example_payload()
        payload['periodization'] = {
            'weeks_table': [{'week': 'S1', 'focus': 'x', 'reps': 'x', 'guidance': 'x'}],
            'volume_table': [],
            'note': '',
            'chart': [{'label': 'S1', 'focus': 'x', 'reps': 'x', 'color': '#fff', 'bg': '#fff', 'fg': '#000', 'h': 150}],
        }
        errors = validate_payload(payload)
        self.assertTrue(any('chart[0].h' in error for error in errors))

    def test_movement_name_and_variations_are_optional(self):
        # Aditivo: movimento publicado antes desta fatia nao tem essas
        # chaves -- continua valido.
        payload = build_example_payload()
        self.assertNotIn('name', payload['days'][0]['blocks'][0]['movements'][0])
        self.assertEqual(validate_payload(payload), [])

    def test_movement_with_name_and_variations_passes(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['name'] = 'Agachamento livre'
        payload['days'][0]['blocks'][0]['movements'][0]['variations'] = [
            {'label': 'Hack squat', 'reference_url': 'https://musclewiki.com/exercise/machine-hack-squat'},
        ]
        self.assertEqual(validate_payload(payload), [])

    def test_movement_variation_missing_label_is_rejected(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['variations'] = [{'reference_url': 'https://x.com'}]
        errors = validate_payload(payload)
        self.assertTrue(any('variations[0]' in error for error in errors))

    def test_movement_variations_not_a_list_is_rejected(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['variations'] = 'nao e lista'
        errors = validate_payload(payload)
        self.assertTrue(any('variations' in error for error in errors))
