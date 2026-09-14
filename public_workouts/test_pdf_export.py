"""
ARQUIVO: testes de render_program_pdf (Entrega 4.6 do plano de produto —
"Exportar treino em PDF", docs/plans/public-workouts-produtizacao-plan.md).

POR QUE ELE EXISTE:
- prova que o payload de PublicWorkoutProgram (schema.py) renderiza um
  PDF valido e com o conteudo certo, sem depender de view/rota nem dos
  10 programas reais (Onda A2) — mesmo padrao de test_workout_template.py.
- nenhuma biblioteca de parsing de PDF esta instalada no projeto; os
  testes assertam direto nos bytes crus porque render_program_pdf desliga
  a compressao de pagina de proposito (ver docstring do modulo).
"""

import copy
import re

from django.test import SimpleTestCase

from public_workouts.pdf_export import render_program_pdf
from public_workouts.schema import build_example_payload


def _page_count(pdf_bytes: bytes) -> int:
    match = re.search(rb'/Count\s+(\d+)', pdf_bytes)
    return int(match.group(1)) if match else 0


class RenderProgramPdfTests(SimpleTestCase):
    def test_returns_bytes_starting_with_pdf_magic(self):
        data = render_program_pdf(build_example_payload())

        self.assertIsInstance(data, bytes)
        self.assertTrue(data.startswith(b'%PDF'))

    def test_includes_program_label(self):
        data = render_program_pdf(build_example_payload())

        self.assertIn(b'Programa de exemplo', data)

    def test_includes_day_label(self):
        data = render_program_pdf(build_example_payload())

        self.assertIn(b'Segunda', data)

    def test_includes_humanized_movement_reps_and_rir(self):
        data = render_program_pdf(build_example_payload())

        self.assertIn(b'Agachamento livre', data)
        self.assertIn(b'3x8-10', data)
        self.assertIn(b'RIR 2', data)

    def test_percentage_of_rm_load_renders_percent_rm(self):
        data = render_program_pdf(build_example_payload())  # load_type=percentage_of_rm, load_value=75.0

        self.assertIn(b'75.0% RM', data)

    def test_fixed_kg_load_renders_kg(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['load_type'] = 'fixed_kg'
        payload['days'][0]['blocks'][0]['movements'][0]['load_value'] = 40

        data = render_program_pdf(payload)

        self.assertIn(b'40 kg', data)

    def test_free_load_renders_livre(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['load_type'] = 'free'
        payload['days'][0]['blocks'][0]['movements'][0]['load_value'] = None

        data = render_program_pdf(payload)

        self.assertIn(b'Livre', data)

    def test_day_with_no_movements_shows_fallback_line(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'] = []

        data = render_program_pdf(payload)

        self.assertIn(b'Nenhum movimento neste dia.', data)

    def test_multi_day_payload_includes_each_day_label(self):
        payload = build_example_payload()
        second_day = copy.deepcopy(payload['days'][0])
        second_day['day_id'] = 'qua'
        second_day['label'] = 'Quarta'
        payload['days'].append(second_day)

        data = render_program_pdf(payload)

        self.assertIn(b'Segunda', data)
        self.assertIn(b'Quarta', data)

    def test_includes_weeks_and_started_on_summary_line(self):
        data = render_program_pdf(build_example_payload())  # weeks=4, started_on='2026-01-05'

        self.assertIn(b'4 semanas', data)
        self.assertIn(b'2026-01-05', data)

    def test_single_short_day_fits_on_one_page(self):
        data = render_program_pdf(build_example_payload())

        self.assertEqual(_page_count(data), 1)

    def test_long_program_spans_multiple_pages(self):
        payload = build_example_payload()
        base_day = payload['days'][0]
        base_block = base_day['blocks'][0]
        base_movement = base_block['movements'][0]

        many_days = []
        for index in range(20):
            day = copy.deepcopy(base_day)
            day['day_id'] = f'd{index}'
            day['label'] = f'Dia {index}'
            day['blocks'] = [copy.deepcopy(base_block) for _ in range(3)]
            for block in day['blocks']:
                block['movements'] = [copy.deepcopy(base_movement) for _ in range(5)]
            many_days.append(day)
        payload['days'] = many_days

        data = render_program_pdf(payload)

        self.assertGreater(_page_count(data), 1)

    def test_does_not_crash_on_payload_missing_optional_fields(self):
        # Defesa em profundidade, mesmo espirito de
        # test_block_with_no_movements_shows_empty_state_not_crash em
        # test_workout_template.py — nao confia so na validacao rio acima.
        minimal_payload = {'program_label': 'Sem tudo', 'days': []}

        data = render_program_pdf(minimal_payload)

        self.assertTrue(data.startswith(b'%PDF'))
        self.assertIn(b'Sem tudo', data)
