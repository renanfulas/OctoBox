"""
Testes para wod_smartplan_weekly_parser — conversão de saída SmartPlan semanal.
"""

import json
from unittest import TestCase

from operations.services.wod_smartplan_weekly_parser import detect_and_convert_smartplan_weekly


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_smartplan_text(blocks: list[dict], session_warnings: list[str] | None = None) -> str:
    payload = {'version': '1.0', 'blocks': blocks}
    if session_warnings:
        payload['session_warnings'] = session_warnings
    json_body = json.dumps(payload, ensure_ascii=False, indent=2)
    return (
        '=== WOD NORMALIZADO ===\n'
        'Semana de treino\n'
        '=== JSON ESTRUTURADO ===\n'
        + json_body
        + '\n=== FIM ==='
    )


FULL_WEEK_SAMPLE = _make_smartplan_text([
    {
        'order': 1,
        'type': 'strength',
        'title': 'SEGUNDA-FEIRA — Força',
        'duration_min': None,
        'rounds': 5,
        'movements': [
            {
                'order': 1,
                'slug': 'back_squat',
                'label_pt': 'Back Squat',
                'label_en': 'Back Squat',
                'reps': 5,
                'load_kg': None,
                'load_note': None,
                'load_pct_rm': 75,
                'load_pct_rm_exercise': 'back_squat',
            }
        ],
        'warnings': [],
    },
    {
        'order': 2,
        'type': 'amrap',
        'title': 'SEGUNDA-FEIRA — AMRAP 12 minutos',
        'duration_min': 12,
        'rounds': None,
        'movements': [
            {
                'order': 1,
                'slug': 'pull_up',
                'label_pt': 'Pull-Up',
                'label_en': 'Pull-Up',
                'reps': 10,
                'load_kg': None,
                'load_note': None,
                'load_pct_rm': None,
                'load_pct_rm_exercise': None,
            },
        ],
        'warnings': [],
    },
    {
        'order': 3,
        'type': 'emom',
        'title': 'TERÇA-FEIRA — EMOM 10 minutos',
        'duration_min': 10,
        'rounds': None,
        'movements': [
            {
                'order': 1,
                'slug': 'burpee',
                'label_pt': 'Burpee',
                'label_en': 'Burpee',
                'reps': 12,
                'load_kg': None,
                'load_note': None,
                'load_pct_rm': None,
                'load_pct_rm_exercise': None,
            }
        ],
        'warnings': [],
    },
])


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

class DetectAndConvertSmartplanWeeklyTests(TestCase):

    def test_returns_none_for_plain_text(self):
        result = detect_and_convert_smartplan_weekly('Segunda\nWod\n10 pull-ups')
        self.assertIsNone(result)

    def test_returns_none_for_empty_string(self):
        result = detect_and_convert_smartplan_weekly('')
        self.assertIsNone(result)

    def test_blocks_text_only_smartplan_when_markers_incomplete(self):
        text = '=== WOD NORMALIZADO ===\nAlgum treino\n(sem JSON)'
        result = detect_and_convert_smartplan_weekly(text)
        self.assertIsNotNone(result)
        self.assertEqual(result['source_format'], 'smartplan_text_v2')
        self.assertTrue(result['parse_errors'])

    def test_detects_text_only_v2_wrapped_in_code_fence_and_extracts_content(self):
        text = (
            '```\n=== WOD NORMALIZADO ===\n'
            'SEGUNDA-FEIRA\n[MOBILIDADE]\n[AQUECIMENTO]\n3 séries\n'
            '▸ 15x Sit-Up\n=== FIM ===\n```'
        )

        result = detect_and_convert_smartplan_weekly(text)

        self.assertEqual(result['source_format'], 'smartplan_text_v2')
        self.assertEqual(result['normalized_text'], 'SEGUNDA-FEIRA\n[MOBILIDADE]\n[AQUECIMENTO]\n3 séries\n▸ 15x Sit-Up')
        self.assertEqual(result['parse_errors'], [])

    def test_detects_text_only_v2_markers_on_same_line(self):
        text = '=== WOD NORMALIZADO === SEGUNDA-FEIRA [WOD] ▸ 10x Burpee === FIM ==='

        result = detect_and_convert_smartplan_weekly(text)

        self.assertEqual(result['source_format'], 'smartplan_text_v2')
        self.assertEqual(result['normalized_text'], 'SEGUNDA-FEIRA [WOD] ▸ 10x Burpee')
        self.assertEqual(result['parse_errors'], [])

    def test_malformed_structured_json_returns_blocking_parse_error(self):
        text = (
            '=== WOD NORMALIZADO ===\nSegunda\nWOD\n10 push up\n'
            '=== JSON ESTRUTURADO ===\n{not valid json\n=== FIM ==='
        )

        result = detect_and_convert_smartplan_weekly(text)

        self.assertIsNotNone(result)
        self.assertEqual(result['days'], [])
        self.assertIn('JSON estruturado está malformado', result['parse_errors'][0])

    def test_detects_smartplan_format_and_returns_payload(self):
        result = detect_and_convert_smartplan_weekly(FULL_WEEK_SAMPLE)
        self.assertIsNotNone(result)
        self.assertIn('days', result)
        self.assertEqual(result.get('source_format'), 'smartplan_json')

    def test_groups_blocks_by_day(self):
        result = detect_and_convert_smartplan_weekly(FULL_WEEK_SAMPLE)
        days = result['days']
        # Segunda (0) tem 2 blocos, Terça (1) tem 1 bloco
        self.assertEqual(len(days), 2)
        segunda = next(d for d in days if d['weekday'] == 0)
        terca = next(d for d in days if d['weekday'] == 1)
        self.assertEqual(len(segunda['blocks']), 2)
        self.assertEqual(len(terca['blocks']), 1)

    def test_day_labels_are_correct(self):
        result = detect_and_convert_smartplan_weekly(FULL_WEEK_SAMPLE)
        labels = {d['weekday']: d['weekday_label'] for d in result['days']}
        self.assertEqual(labels[0], 'Segunda')
        self.assertEqual(labels[1], 'Terca')

    def test_block_titles_strip_day_prefix(self):
        result = detect_and_convert_smartplan_weekly(FULL_WEEK_SAMPLE)
        segunda = next(d for d in result['days'] if d['weekday'] == 0)
        titles = [b['title'] for b in segunda['blocks']]
        self.assertIn('Força', titles)
        self.assertIn('AMRAP 12 minutos', titles)
        # Prefixo de dia removido
        for title in titles:
            self.assertNotIn('SEGUNDA-FEIRA', title)

    def test_movements_have_correct_slugs(self):
        result = detect_and_convert_smartplan_weekly(FULL_WEEK_SAMPLE)
        segunda = next(d for d in result['days'] if d['weekday'] == 0)
        strength_block = segunda['blocks'][0]
        movement = strength_block['movements'][0]
        self.assertEqual(movement['movement_slug'], 'back_squat')
        self.assertEqual(movement['movement_label_raw'], 'Back Squat')
        self.assertEqual(movement['reps_spec'], '5')

    def test_load_pct_rm_converted_to_load_spec(self):
        result = detect_and_convert_smartplan_weekly(FULL_WEEK_SAMPLE)
        segunda = next(d for d in result['days'] if d['weekday'] == 0)
        movement = segunda['blocks'][0]['movements'][0]
        self.assertEqual(movement['load_spec'], '75% RM')

    def test_format_spec_amrap(self):
        result = detect_and_convert_smartplan_weekly(FULL_WEEK_SAMPLE)
        segunda = next(d for d in result['days'] if d['weekday'] == 0)
        amrap_block = segunda['blocks'][1]
        self.assertEqual(amrap_block['format_spec'], 'AMRAP 12 min')
        self.assertEqual(amrap_block['timecap_min'], 12)

    def test_format_spec_emom(self):
        result = detect_and_convert_smartplan_weekly(FULL_WEEK_SAMPLE)
        terca = next(d for d in result['days'] if d['weekday'] == 1)
        self.assertEqual(terca['blocks'][0]['format_spec'], 'EMOM 10 min')

    def test_all_movements_have_slugs_when_gpt_provides_them(self):
        """Quando o GPT fornece slugs, todos os movimentos chegam com movement_slug preenchido."""
        result = detect_and_convert_smartplan_weekly(FULL_WEEK_SAMPLE)
        for day in result['days']:
            for block in day['blocks']:
                for movement in block['movements']:
                    self.assertTrue(
                        movement['movement_slug'],
                        f"movement_slug vazio para '{movement['movement_label_raw']}'",
                    )

    def test_load_free_note_not_copied_to_load_spec(self):
        """'free'/'carga livre' no load_note não deve virar load_spec."""
        text = _make_smartplan_text([
            {
                'order': 1,
                'type': 'for_time',
                'title': 'SEGUNDA-FEIRA — For Time',
                'duration_min': None,
                'rounds': None,
                'movements': [
                    {
                        'order': 1,
                        'slug': 'thruster',
                        'label_pt': 'Thruster',
                        'label_en': 'Thruster',
                        'reps': 21,
                        'load_kg': None,
                        'load_note': 'free',
                        'load_pct_rm': None,
                        'load_pct_rm_exercise': None,
                    }
                ],
                'warnings': [],
            }
        ])
        result = detect_and_convert_smartplan_weekly(text)
        movement = result['days'][0]['blocks'][0]['movements'][0]
        self.assertIsNone(movement['load_spec'])

    def test_blocks_without_day_prefix_are_blocked_instead_of_assigned_to_monday(self):
        text = _make_smartplan_text([
            {
                'order': 1,
                'type': 'metcon',
                'title': 'WOD Genérico',
                'duration_min': None,
                'rounds': None,
                'movements': [
                    {
                        'order': 1, 'slug': 'run', 'label_pt': 'Run', 'label_en': 'Run',
                        'reps': None, 'load_kg': None, 'load_note': '400m',
                        'load_pct_rm': None, 'load_pct_rm_exercise': None,
                    }
                ],
                'warnings': [],
            }
        ])
        result = detect_and_convert_smartplan_weekly(text)
        self.assertEqual(result['days'], [])
        self.assertEqual(len(result['parse_errors']), 1)
        self.assertIn('WOD Genérico', result['parse_errors'][0])

    def test_block_title_with_multiple_days_is_blocked_as_ambiguous(self):
        blocks = [{
            'order': 1,
            'type': 'metcon',
            'title': 'SEGUNDA-FEIRA + TERÇA-FEIRA — WOD',
            'duration_min': None,
            'rounds': None,
            'movements': [],
        }]

        result = detect_and_convert_smartplan_weekly(_make_smartplan_text(blocks))

        self.assertIsNotNone(result)
        self.assertEqual(result['days'], [])
        self.assertEqual(len(result['parse_errors']), 1)
        self.assertIn('único dia', result['parse_errors'][0])

    def test_session_warnings_propagated(self):
        text = _make_smartplan_text(
            blocks=[
                {
                    'order': 1, 'type': 'for_time', 'title': 'SEGUNDA-FEIRA — For Time',
                    'duration_min': None, 'rounds': None, 'movements': [], 'warnings': [],
                }
            ],
            session_warnings=['aviso de exemplo'],
        )
        result = detect_and_convert_smartplan_weekly(text)
        self.assertIn('aviso de exemplo', result['parse_warnings'])

    def test_movement_prescription_metadata_is_preserved(self):
        text = _make_smartplan_text([{
            'order': 1,
            'type': 'strength',
            'title': 'SEGUNDA-FEIRA — Força',
            'duration_min': None,
            'rounds': 4,
            'movements': [{
                'order': 1,
                'slug': 'front_squat',
                'label_pt': 'Agachamento frontal',
                'reps': '5-5-5',
                'sets': 3,
                'load_kg': None,
                'load_note': None,
                'load_pct_rm': 75,
                'load_pct_rm_exercise': 'front_squat',
                'is_scaled_alternative': True,
                'notes': 'Manter a técnica em todas as séries.',
            }],
        }])

        result = detect_and_convert_smartplan_weekly(text)
        movement = result['days'][0]['blocks'][0]['movements'][0]

        self.assertEqual(movement['sets'], 3)
        self.assertEqual(movement['reps_spec'], '5-5-5')
        self.assertEqual(movement['load_spec'], '75% RM')
        self.assertTrue(movement['is_scaled_alternative'])
        self.assertEqual(movement['notes'], 'Manter a técnica em todas as séries.')
