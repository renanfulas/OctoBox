"""
ARQUIVO: testes do parser do SmartPlan (BYOLLM).

POR QUE ELE EXISTE:
- protege o contrato de formato canonico entre o GPT customizado e o backend.
- garante que paste invalido nao passe silenciosamente para tier rico.

O QUE ESTE ARQUIVO FAZ:
1. cobre o caminho feliz com formato canonico completo.
2. cobre 4 falhas distintas (sem marcadores, JSON quebrado, sem blocks, blocks vazios).
3. valida que o JSON wrap em ```json``` e tolerado.

PONTOS CRITICOS:
- se estes testes quebrarem, a regra de tier (cru vs rico) pode aceitar input errado.
- mudancas no prompt do GPT exigem rever os fixtures aqui.
"""

from django.test import SimpleTestCase

from operations.services.wod_normalization.response_parser import (
    REASON_BLOCKS_EMPTY,
    REASON_BLOCKS_MISSING,
    REASON_JSON_INVALID,
    REASON_MARKERS_MISSING,
    detect_smartplan_format,
)


class DetectSmartplanFormatTests(SimpleTestCase):
    def _build_valid_paste(self, *, blocks_json: str) -> str:
        return (
            '=== WOD NORMALIZADO ===\n'
            'AMRAP 12 minutos\n'
            '\n'
            'Lorem ipsum.\n'
            '\n'
            '=== JSON ESTRUTURADO ===\n'
            '```json\n'
            f'{blocks_json}\n'
            '```\n'
            '\n'
            '=== FIM ==='
        )

    def test_returns_normalized_payload_for_canonical_paste(self):
        payload_json = (
            '{"version": "1.0", "blocks": ['
            '{"order": 1, "type": "amrap", "title": "AMRAP 12 minutos",'
            ' "duration_min": 12, "rounds": null, "is_partner": false,'
            ' "is_synchro": false, "scaling_notes": "",'
            ' "movements": ['
            '{"order": 1, "slug": "thruster", "label_pt": "Thruster",'
            ' "label_en": "Thruster", "reps": 30, "load_kg": null,'
            ' "load_note": "free", "load_pct_rm": null,'
            ' "load_pct_rm_exercise": null}'
            '], "warnings": []}'
            '], "session_warnings": []}'
        )
        result = detect_smartplan_format(self._build_valid_paste(blocks_json=payload_json))

        self.assertTrue(result['is_normalized'])
        self.assertIn('AMRAP 12 minutos', result['normalized_text'])
        payload = result['structured_payload']
        self.assertEqual(payload['version'], '1.0')
        self.assertEqual(len(payload['blocks']), 1)
        self.assertEqual(payload['blocks'][0]['type'], 'amrap')

    def test_returns_invalid_when_markers_missing(self):
        result = detect_smartplan_format('AMRAP 12: 8 BOB, 10 hspu, 30 thruster')
        self.assertFalse(result['is_normalized'])
        self.assertEqual(result['reason'], REASON_MARKERS_MISSING)

    def test_returns_invalid_when_json_unparseable(self):
        broken = (
            '=== WOD NORMALIZADO ===\n'
            'Texto valido\n'
            '=== JSON ESTRUTURADO ===\n'
            '```json\n'
            '{"blocks": [\n'  # JSON aberto sem fechar
            '```\n'
            '=== FIM ==='
        )
        result = detect_smartplan_format(broken)
        self.assertFalse(result['is_normalized'])
        self.assertEqual(result['reason'], REASON_JSON_INVALID)

    def test_returns_invalid_when_blocks_key_missing(self):
        payload_json = '{"version": "1.0", "session_warnings": []}'
        result = detect_smartplan_format(self._build_valid_paste(blocks_json=payload_json))
        self.assertFalse(result['is_normalized'])
        self.assertEqual(result['reason'], REASON_BLOCKS_MISSING)

    def test_returns_invalid_when_blocks_empty(self):
        payload_json = '{"version": "1.0", "blocks": [], "session_warnings": []}'
        result = detect_smartplan_format(self._build_valid_paste(blocks_json=payload_json))
        self.assertFalse(result['is_normalized'])
        self.assertEqual(result['reason'], REASON_BLOCKS_EMPTY)

    def test_returns_invalid_for_empty_string(self):
        result = detect_smartplan_format('')
        self.assertFalse(result['is_normalized'])
        self.assertEqual(result['reason'], REASON_MARKERS_MISSING)

    def test_tolerates_json_block_without_code_fence(self):
        payload_json_no_fence = (
            '{"version": "1.0", "blocks": ['
            '{"order": 1, "type": "free", "title": "Bloco", "duration_min": null,'
            ' "rounds": null, "is_partner": false, "is_synchro": false,'
            ' "scaling_notes": "", "movements": [], "warnings": []}'
            '], "session_warnings": []}'
        )
        paste = (
            '=== WOD NORMALIZADO ===\n'
            'Texto\n'
            '=== JSON ESTRUTURADO ===\n'
            f'{payload_json_no_fence}\n'
            '=== FIM ==='
        )
        result = detect_smartplan_format(paste)
        self.assertTrue(result['is_normalized'])
        self.assertEqual(len(result['structured_payload']['blocks']), 1)
