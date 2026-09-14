"""
ARQUIVO: teste de renderizacao do prototipo do template unico
(Onda B3 do CORDA — fundacao visual, docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- prova que templates/public_workouts/workout.html renderiza QUALQUER
  payload valido pelo contrato de schema.py sem view nem dado publicado de
  verdade — usa `schema.build_example_payload()`, disponivel desde a
  Onda S0.
- NAO e teste de view/URL: este template ainda nao esta ligado a nenhuma
  rota (a Onda B3 real decide fase de acesso e corte de producao depois).
"""

import copy

from django.template.loader import render_to_string
from django.test import TestCase

from public_workouts.schema import build_example_payload
from public_workouts.templatetags.public_workouts_extras import humanize_movement_slug, load_chart_points


def _render(payload: dict, accent_variant=None, program_versions=None, load_history=None) -> str:
    return render_to_string('public_workouts/workout.html', {
        'program': payload,
        'accent_variant': accent_variant,
        'program_versions': program_versions or [],
        'load_history': load_history or [],
    })


class WorkoutTemplateRenderTests(TestCase):
    def test_renders_example_payload_without_error(self):
        html = _render(build_example_payload())

        self.assertIn('<html', html)
        self.assertIn('Programa de exemplo', html)

    def test_renders_day_label_and_tab_structure(self):
        html = _render(build_example_payload())

        self.assertIn('Segunda', html)
        self.assertIn('workout-day-seg', html)
        self.assertIn('is-tab-active', html)
        self.assertIn('interactive-tab-container', html)

    def test_renders_movement_with_humanized_label_and_wiki_link(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['reference_url'] = 'https://musclewiki.com/exercise/agachamento-livre'

        html = _render(payload)

        self.assertIn('Agachamento livre', html)
        self.assertIn('href="https://musclewiki.com/exercise/agachamento-livre"', html)

    def test_movement_without_reference_url_renders_plain_label_not_link(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['reference_url'] = None

        html = _render(payload)

        self.assertIn('Agachamento livre', html)
        self.assertNotIn('href="None"', html)

    def test_renders_reps_and_rir_spec(self):
        html = _render(build_example_payload())

        self.assertIn('3x8-10', html)
        self.assertIn('RIR 2', html)

    def test_percentage_of_rm_load_renders_percentage(self):
        html = _render(build_example_payload())  # load_type=percentage_of_rm, load_value=75.0

        # Django formata numero com separador decimal pt-BR (USE_L10N) — "," nao ".".
        self.assertIn('75,0% RM', html)

    def test_fixed_kg_load_renders_kg(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['load_type'] = 'fixed_kg'
        payload['days'][0]['blocks'][0]['movements'][0]['load_value'] = 40

        html = _render(payload)

        self.assertIn('40 kg', html)

    def test_free_load_renders_livre(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['load_type'] = 'free'
        payload['days'][0]['blocks'][0]['movements'][0]['load_value'] = None

        html = _render(payload)

        self.assertIn('Livre', html)

    def test_is_tracked_shows_chip(self):
        html = _render(build_example_payload())  # is_tracked=True no exemplo

        self.assertIn('workout-tracked-chip', html)
        self.assertIn('rastreado', html)

    def test_block_with_no_movements_shows_empty_state_not_crash(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'] = []
        # Nao passa por assert_valid_payload aqui de proposito — o template
        # tem que sobreviver a um payload vazio mesmo que o schema recuse
        # publica-lo (defesa em profundidade, nao confia so na validacao rio acima).

        html = _render(payload)

        self.assertIn('Nenhum movimento neste bloco', html)

    def test_accent_variant_premium_sets_data_attribute(self):
        html = _render(build_example_payload(), accent_variant='F')
        self.assertIn('data-accent-variant="premium"', html)

    def test_accent_variant_support_sets_data_attribute(self):
        html = _render(build_example_payload(), accent_variant='M')
        self.assertIn('data-accent-variant="support"', html)

    def test_accent_variant_none_sets_no_data_attribute(self):
        html = _render(build_example_payload(), accent_variant=None)
        self.assertNotIn('data-accent-variant', html)

    def test_multi_day_multi_block_payload_renders_each_once(self):
        payload = build_example_payload()
        second_day = copy.deepcopy(payload['days'][0])
        second_day['day_id'] = 'qua'
        second_day['label'] = 'Quarta'
        payload['days'].append(second_day)

        html = _render(payload)

        self.assertEqual(html.count('class="workout-day-panel'), 2)
        self.assertIn('workout-day-seg', html)
        self.assertIn('workout-day-qua', html)

    def test_history_tab_renders_without_data(self):
        html = _render(build_example_payload())

        self.assertIn('Histórico', html)
        self.assertIn('Nenhuma versão publicada ainda.', html)
        self.assertIn('Nenhuma carga registrada ainda.', html)
        # nao pode inflar a contagem que test_multi_day_multi_block_payload_renders_each_once faz
        self.assertNotIn('class="workout-day-panel workout-history-panel', html)

    def test_history_tab_renders_program_version_list_with_active_badge(self):
        html = _render(build_example_payload(), program_versions=[
            {'version': 2, 'program_id': 'bruno-2026-q1', 'program_label': 'Bruno Q1', 'started_on': '2026-04-01', 'weeks': 6, 'is_active': True, 'created_at': '2026-04-01T00:00:00'},
            {'version': 1, 'program_id': 'bruno-2026-q1', 'program_label': 'Bruno Q1', 'started_on': '2026-01-01', 'weeks': 4, 'is_active': False, 'created_at': '2026-01-01T00:00:00'},
        ])

        self.assertIn('v2', html)
        self.assertIn('v1', html)
        self.assertIn('ativa', html)
        self.assertIn('inativa', html)

    def test_history_tab_renders_load_chart_with_two_or_more_points(self):
        html = _render(build_example_payload(), load_history=[
            {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-05', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1'},
            {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-12', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k2'},
        ])

        self.assertIn('Agachamento livre', html)
        self.assertIn('workout-load-chart-line', html)
        self.assertIn('workout-load-chart-trend--up', html)
        # Texto visivel usa separador decimal pt-BR (USE_L10N, mesma
        # convencao de "75,0% RM" ja testada acima); coordenadas do SVG
        # abaixo tem que ficar de FORA disso (SVG so aceita ponto).
        self.assertIn('100,0 kg', html)
        self.assertIn('cx="10.0" cy="90.0"', html)
        self.assertNotIn('Ainda não há carga suficiente', html)

    def test_history_tab_shows_fallback_with_fewer_than_two_points(self):
        html = _render(build_example_payload(), load_history=[
            {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-05', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1'},
        ])

        self.assertIn('Ainda não há carga suficiente registrada para montar o gráfico.', html)
        self.assertNotIn('workout-load-chart-line', html)


class HumanizeMovementSlugFilterTests(TestCase):
    def test_replaces_hyphens_and_capitalizes(self):
        self.assertEqual(humanize_movement_slug('agachamento-livre'), 'Agachamento livre')

    def test_empty_string_stays_empty(self):
        self.assertEqual(humanize_movement_slug(''), '')

    def test_none_stays_empty(self):
        self.assertEqual(humanize_movement_slug(None), '')


class LoadChartPointsFilterTests(TestCase):
    def test_no_entries_has_no_data(self):
        result = load_chart_points([])

        self.assertFalse(result['has_data'])
        self.assertEqual(result['points'], [])
        self.assertEqual(result['points_attr'], '')

    def test_single_point_has_no_data(self):
        # Mesma supressao de assessments.js::buildWeightChart — 1 ponto so
        # nao mostra tendencia nenhuma.
        entries = [{'weight_kg': 100.0, 'performed_on': '2026-01-05'}]

        result = load_chart_points(entries)

        self.assertFalse(result['has_data'])

    def test_entries_with_weight_kg_none_are_ignored(self):
        # Movimento so de peso corporal (weight_kg=None) nunca deveria
        # contar como ponto de grafico de carga.
        entries = [
            {'weight_kg': None, 'performed_on': '2026-01-01'},
            {'weight_kg': None, 'performed_on': '2026-01-02'},
        ]

        result = load_chart_points(entries)

        self.assertFalse(result['has_data'])

    def test_two_points_normalizes_between_pad_and_width_minus_pad(self):
        entries = [
            {'weight_kg': 90.0, 'performed_on': '2026-01-05'},
            {'weight_kg': 100.0, 'performed_on': '2026-01-12'},
        ]

        result = load_chart_points(entries)

        self.assertTrue(result['has_data'])
        self.assertEqual(len(result['points']), 2)
        # menor carga fica embaixo (y maior), maior carga fica em cima (y menor)
        self.assertGreater(result['points'][0]['y'], result['points'][1]['y'])
        self.assertEqual(result['points'][0]['x'], 10)
        self.assertEqual(result['points'][1]['x'], 590)
        self.assertEqual(result['points_attr'], '10.0,90.0 590.0,10.0')

    def test_flat_series_does_not_divide_by_zero(self):
        # min == max -> span seria 0; a funcao usa `span or 1` pra nao
        # levantar ZeroDivisionError.
        entries = [
            {'weight_kg': 100.0, 'performed_on': '2026-01-05'},
            {'weight_kg': 100.0, 'performed_on': '2026-01-12'},
        ]

        result = load_chart_points(entries)

        self.assertTrue(result['has_data'])
        self.assertEqual(result['points'][0]['y'], result['points'][1]['y'])

    def test_labels_are_short_dates(self):
        entries = [
            {'weight_kg': 90.0, 'performed_on': '2026-01-05'},
            {'weight_kg': 100.0, 'performed_on': '2026-01-12'},
        ]

        result = load_chart_points(entries)

        self.assertEqual(result['points'][0]['label'], '05/01')
        self.assertEqual(result['points'][1]['label'], '12/01')

    def test_upward_trend_reports_positive_delta(self):
        entries = [
            {'weight_kg': 90.0, 'performed_on': '2026-01-05'},
            {'weight_kg': 100.0, 'performed_on': '2026-01-12'},
        ]

        result = load_chart_points(entries)

        self.assertEqual(result['trend'], 'up')
        self.assertEqual(result['delta_weight_kg'], 10.0)
        self.assertEqual(result['latest_weight_kg'], 100.0)

    def test_downward_trend_reports_negative_delta(self):
        entries = [
            {'weight_kg': 100.0, 'performed_on': '2026-01-05'},
            {'weight_kg': 90.0, 'performed_on': '2026-01-12'},
        ]

        result = load_chart_points(entries)

        self.assertEqual(result['trend'], 'down')
        self.assertEqual(result['delta_weight_kg'], -10.0)

    def test_flat_trend_reports_zero_delta(self):
        entries = [
            {'weight_kg': 100.0, 'performed_on': '2026-01-05'},
            {'weight_kg': 100.0, 'performed_on': '2026-01-12'},
        ]

        result = load_chart_points(entries)

        self.assertEqual(result['trend'], 'flat')
        self.assertEqual(result['delta_weight_kg'], 0.0)

    def test_area_points_closes_polygon_at_baseline(self):
        entries = [
            {'weight_kg': 90.0, 'performed_on': '2026-01-05'},
            {'weight_kg': 100.0, 'performed_on': '2026-01-12'},
        ]

        result = load_chart_points(entries)

        self.assertEqual(
            result['area_points_attr'],
            f"{result['points_attr']} 590.0,{result['baseline_y']} 10.0,{result['baseline_y']}",
        )

    def test_no_data_still_has_zeroed_trend_fields(self):
        # O template usa chart.trend/latest_weight_kg so dentro de
        # {% if chart.has_data %}, mas as chaves precisam existir mesmo
        # assim pra nao quebrar caso alguem itere fora desse guard.
        result = load_chart_points([])

        self.assertIsNone(result['latest_weight_kg'])
        self.assertIsNone(result['delta_weight_kg'])
        self.assertEqual(result['trend'], 'flat')
        self.assertEqual(result['area_points_attr'], '')
