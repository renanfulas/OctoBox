"""
ARQUIVO: teste de renderizacao do prototipo do template unico
(Onda B3 do CORDA — fundacao visual, docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- prova que templates/public_workouts/workout.html renderiza QUALQUER
  payload valido pelo contrato de schema.py sem view nem dado publicado de
  verdade — usa o mesmo payload de exemplo que services_stub.py devolve
  (build_example_payload), disponivel desde a Onda S0.
- NAO e teste de view/URL: este template ainda nao esta ligado a nenhuma
  rota (a Onda B3 real decide fase de acesso e corte de producao depois).
"""

import copy

from django.template.loader import render_to_string
from django.test import TestCase

from public_workouts.schema import build_example_payload
from public_workouts.templatetags.public_workouts_extras import humanize_movement_slug


def _render(payload: dict, accent_variant=None) -> str:
    return render_to_string('public_workouts/workout.html', {'program': payload, 'accent_variant': accent_variant})


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


class HumanizeMovementSlugFilterTests(TestCase):
    def test_replaces_hyphens_and_capitalizes(self):
        self.assertEqual(humanize_movement_slug('agachamento-livre'), 'Agachamento livre')

    def test_empty_string_stays_empty(self):
        self.assertEqual(humanize_movement_slug(''), '')

    def test_none_stays_empty(self):
        self.assertEqual(humanize_movement_slug(None), '')
