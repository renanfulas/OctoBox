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
import re

from django.template.loader import render_to_string
from django.test import TestCase

from public_workouts.periodization import PHASE_PROFILES
from public_workouts.schema import build_example_payload
from public_workouts.templatetags.public_workouts_extras import (
    current_period_week_number,
    dict_get,
    glossary_highlight,
    humanize_movement_slug,
    load_chart_points,
    movement_load_display,
    periodization_chart_points,
    periodization_phase_banner,
    reps_phases,
)


def _render(
    payload: dict,
    accent_variant=None,
    program_versions=None,
    load_history=None,
    one_rep_max_by_movement=None,
    trends_by_movement=None,
    plan_slug='bruno',
    student_name='',
    student_photo_url=None,
    customer_portal_url=None,
    account_email=None,
) -> str:
    return render_to_string('public_workouts/workout.html', {
        'program': payload,
        'accent_variant': accent_variant,
        'program_versions': program_versions or [],
        'load_history': load_history or [],
        'one_rep_max_by_movement': one_rep_max_by_movement or {},
        'trends_by_movement': trends_by_movement or {},
        'plan_slug': plan_slug,
        'student_name': student_name,
        'student_photo_url': student_photo_url,
        'customer_portal_url': customer_portal_url,
        'account_email': account_email,
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

    def test_is_tracked_shows_load_input_row(self):
        # Item 8 da Onda B3: movimento rastreado ganha a caixinha de
        # "registrar carga de hoje" (queue pro outbox em load_tracker.js).
        # Colapsada por padrao (item 4 do pedido do Renan) -- so' abre no
        # clique do card, ver test_load_input_widget_starts_hidden.
        html = _render(build_example_payload())  # is_tracked=True no exemplo

        self.assertIn('data-workout-load-input', html)
        self.assertIn('data-workout-load-field', html)
        self.assertIn('data-workout-load-save', html)
        self.assertIn(f"data-movement-slug=\"{build_example_payload()['days'][0]['blocks'][0]['movements'][0]['movement_slug']}\"", html)

    def test_load_input_widget_starts_hidden_and_card_is_clickable(self):
        html = _render(build_example_payload())  # is_tracked=True no exemplo

        self.assertIn('<div class="workout-load-input" data-workout-load-input', html)
        self.assertIn('data-workout-load-input data-movement-slug="agachamento-livre" data-program-id="exemplo-2026-q1" hidden', html)
        self.assertIn('data-workout-load-toggle', html)

    def test_load_input_widget_is_always_the_immediate_next_sibling_of_the_card(self):
        # Regressao real: o JS de toggle (workout.html, [data-workout-load-toggle])
        # acha o widget via `card.nextElementSibling`, nao querySelector -- se
        # QUALQUER elemento (ex.: o hint de "Registre sua carga") for inserido
        # entre </article> e .workout-load-input, o clique para de reabrir o
        # widget silenciosamente. Movimento sem 1RM (o caso mais comum) sempre
        # renderiza o hint, entao esse regex tem que casar mesmo nesse caso.
        html = _render(build_example_payload())

        card_count = html.count('workout-movement-card')
        sibling_count = len(re.findall(r'</article>\s*<div class="workout-load-input"', html))

        self.assertGreater(card_count, 0)
        self.assertEqual(sibling_count, card_count)

    def test_movement_not_tracked_still_has_load_input_row(self):
        # Pedido do Renan: "clica expande em todos os exercicios" -- o
        # registro de carga (load_tracker.js/services.record_load, que
        # nunca validou is_tracked) fica disponivel pra QUALQUER movimento,
        # nao so' os curados como "rastreado". is_tracked continua so'
        # controlando a badge "rastreado" (curadoria do treinador), nunca
        # se o card e clicavel.
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['is_tracked'] = False

        html = _render(payload)

        self.assertIn('<div class="workout-load-input"', html)
        self.assertIn('data-workout-load-toggle tabindex="0" role="button" aria-expanded', html)
        self.assertNotIn('workout-tracked-chip', html)

    def test_body_carries_plan_slug_for_load_tracker_js(self):
        html = _render(build_example_payload(), plan_slug='giovanna')

        self.assertIn('data-plan-slug="giovanna"', html)

    def test_loads_load_tracker_script(self):
        html = _render(build_example_payload())

        self.assertIn('js/public_workouts/load_tracker.js', html)

    def test_movement_with_reference_url_gets_wiki_link_class(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['reference_url'] = 'https://musclewiki.com/exercise/agachamento-livre'

        html = _render(payload)

        self.assertIn('class="workout-wiki-link"', html)

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

    def test_day_tab_splits_prefixed_label_into_short_day_and_keyword(self):
        payload = build_example_payload()
        payload['days'][0]['label'] = 'Segunda - Pernas Quadríceps'

        html = _render(payload)

        self.assertIn('<span class="workout-day-tab__day">Seg</span>', html)
        self.assertIn('<span class="workout-day-tab__keyword">Pernas Quadríceps</span>', html)

    def test_day_tab_keeps_label_unchanged_when_no_weekday_prefix(self):
        # juliana/henrique: label real e' so' a palavra-chave, sem "Segunda -".
        payload = build_example_payload()
        payload['days'][0]['label'] = 'Superior A'

        html = _render(payload)

        self.assertIn('<span class="workout-day-tab__day">Seg</span>', html)
        self.assertIn('<span class="workout-day-tab__keyword">Superior A</span>', html)

    def test_all_movements_are_clickable_regardless_of_is_tracked(self):
        # Pedido do Renan: registrar carga disponivel em TODO exercicio, nao
        # so' nos curados como "rastreado" pelo treinador.
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'].append({
            **payload['days'][0]['blocks'][0]['movements'][0],
            'movement_slug': 'outro-movimento',
            'is_tracked': False,
        })

        html = _render(payload)

        # 'data-workout-load-toggle' sozinho tambem aparece 1x no <script>
        # inline (querySelectorAll) -- conta o cluster de atributos da tag
        # de verdade, mesmo padrao ja usado nos outros testes deste arquivo.
        self.assertEqual(html.count('data-workout-load-toggle tabindex="0" role="button" aria-expanded'), 2)
        self.assertEqual(html.count('<div class="workout-load-input"'), 2)
        self.assertEqual(html.count('workout-tracked-chip'), 1)

    def test_history_tab_renders_without_data(self):
        # "Histórico" (nome antigo do tab combinado) virou dois paineis de
        # nivel superior: Cargas (evolucao de carga) e Perfil (versoes do
        # programa) — pedido do Renan pra estrutura de bottom nav.
        html = _render(build_example_payload())

        self.assertIn('id="workout-panel-cargas"', html)
        self.assertIn('id="workout-panel-perfil"', html)
        self.assertIn('Nenhuma versão publicada ainda.', html)
        self.assertIn('Nenhuma carga registrada ainda.', html)
        # nao pode inflar a contagem que test_multi_day_multi_block_payload_renders_each_once faz
        self.assertNotIn('class="workout-day-panel workout-panel-cargas', html)

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

    def test_history_tab_shows_one_rep_max_estimate_when_provided(self):
        html = _render(
            build_example_payload(),
            load_history=[
                {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-05', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1'},
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-12', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k2'},
            ],
            one_rep_max_by_movement={
                'agachamento-livre': {'value_kg': 128.6, 'formula': 'brzycki', 'confidence': 'high', 'effective_reps': 10},
            },
        )

        self.assertIn('workout-load-chart-1rm', html)
        self.assertIn('128,6 kg', html)
        self.assertIn('confiança high', html)

    def test_history_tab_hides_one_rep_max_badge_when_movement_has_no_estimate(self):
        html = _render(
            build_example_payload(),
            load_history=[
                {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-05', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1'},
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-12', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k2'},
            ],
            one_rep_max_by_movement={'outro-movimento': {'value_kg': 50.0, 'formula': 'epley', 'confidence': 'low', 'effective_reps': 14}},
        )

        self.assertNotIn('workout-load-chart-1rm', html)

    def test_history_tab_shows_declining_signal_badge(self):
        html = _render(
            build_example_payload(),
            load_history=[
                {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-05', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1'},
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-12', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k2'},
            ],
            trends_by_movement={'agachamento-livre': {'label': 'declining', 'weekly_estimates_kg': [130.0, 125.0, 118.0]}},
        )

        self.assertIn('workout-load-chart-signal--declining', html)
        self.assertIn('Em queda', html)

    def test_history_tab_shows_plateau_signal_badge(self):
        html = _render(
            build_example_payload(),
            load_history=[
                {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-05', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1'},
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-12', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k2'},
            ],
            trends_by_movement={'agachamento-livre': {'label': 'plateau', 'weekly_estimates_kg': [128.0, 129.0, 127.5]}},
        )

        self.assertIn('workout-load-chart-signal--plateau', html)
        self.assertIn('Platô', html)

    def test_history_tab_shows_improving_signal_badge(self):
        html = _render(
            build_example_payload(),
            load_history=[
                {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-05', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1'},
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-12', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k2'},
            ],
            trends_by_movement={'agachamento-livre': {'label': 'improving', 'weekly_estimates_kg': [118.0, 124.0, 130.0]}},
        )

        self.assertIn('workout-load-chart-signal--improving', html)
        self.assertIn('Em evolução', html)

    def test_history_tab_marks_program_version_change_on_chart(self):
        html = _render(
            build_example_payload(),
            load_history=[
                {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-05', 'program_id': 'bruno-2026-q1', 'week_in_program': 4, 'idempotency_key': 'k1'},
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-04-01', 'program_id': 'bruno-2026-q2', 'week_in_program': 1, 'idempotency_key': 'k2'},
            ],
        )

        self.assertIn('workout-load-chart-version-line', html)
        self.assertIn('workout-load-chart-dot--version', html)
        self.assertIn('Novo programa a partir daqui: bruno-2026-q2', html)
        self.assertIn('semana 1', html)

    def test_history_tab_does_not_mark_change_when_program_id_is_the_same(self):
        html = _render(
            build_example_payload(),
            load_history=[
                {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-05', 'program_id': 'bruno-2026-q1', 'week_in_program': 1, 'idempotency_key': 'k1'},
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-12', 'program_id': 'bruno-2026-q1', 'week_in_program': 2, 'idempotency_key': 'k2'},
            ],
        )

        self.assertNotIn('workout-load-chart-version-line', html)
        self.assertNotIn('workout-load-chart-dot--version', html)


class WorkoutTopbarAndNavTests(TestCase):
    """Fundação visual pedida pelo Renan (topbar/semana/bottom nav), com o
    mesmo padrão do app do aluno de box — reimplementada do zero aqui
    (D.00/D.3: nunca importa templates/CSS do student_app)."""

    def test_greeting_includes_first_name(self):
        html = _render(build_example_payload(), student_name='Juliana Silva')

        # so o primeiro nome, mesmo corte de student_shell.student_greeting --
        # escopado a tag da saudacao, nao a pagina inteira: o cabecalho do
        # Perfil (workout-profile-header__name) mostra o NOME COMPLETO de
        # proposito (mesma estrutura do app do aluno, que tambem mostra nome
        # completo no Perfil), entao 'Silva' aparece em outro lugar da pagina.
        greeting_match = re.search(r'<strong class="workout-topbar-greeting">([^<]*)</strong>', html)
        self.assertIsNotNone(greeting_match)
        self.assertIn('Juliana', greeting_match.group(1))
        self.assertNotIn('Silva', greeting_match.group(1))

    def test_greeting_without_name_still_renders(self):
        html = _render(build_example_payload(), student_name='')

        self.assertIn('workout-topbar-greeting', html)

    def test_avatar_shows_first_letter_when_no_photo(self):
        html = _render(build_example_payload(), student_name='Juliana', student_photo_url=None)

        self.assertIn('>J<', html)
        self.assertNotIn('<img', html)

    def test_avatar_shows_photo_when_provided(self):
        html = _render(build_example_payload(), student_name='Juliana', student_photo_url='https://example.com/foto.jpg')

        self.assertIn('<img src="https://example.com/foto.jpg"', html)

    def test_bottom_nav_has_five_destinations_in_order(self):
        # Treino nao tem mais [data-workout-tab-target] fixo -- virou o
        # botao de ciclo (Treino/Cardio/Periodizacao, ver
        # data-workout-cycle-nav) pedido pelo Renan, ainda assim ocupa o
        # 3o slot visualmente entre Avaliacao e Cargas.
        html = _render(build_example_payload())

        nav_start = html.index('workout-mobile-nav')
        fixed_order = ['workout-panel-inicio', 'workout-panel-avaliacao']
        positions = [html.index(f'data-workout-tab-target="{target}"', nav_start) for target in fixed_order]
        cycle_nav_position = html.index('data-workout-cycle-nav', nav_start)
        trailing_order = ['workout-panel-cargas', 'workout-panel-perfil']
        positions += [html.index(f'data-workout-tab-target="{target}"', nav_start) for target in trailing_order]

        self.assertEqual(positions[:2], sorted(positions[:2]))
        self.assertTrue(positions[1] < cycle_nav_position < positions[2])
        self.assertEqual(positions[2:], sorted(positions[2:]))

    def test_inicio_panel_is_active_by_default(self):
        html = _render(build_example_payload())

        self.assertIn('id="workout-panel-inicio" class="is-tab-active"', html)

    def test_week_strip_shows_seven_days(self):
        html = _render(build_example_payload())

        for label in ('Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'):
            self.assertIn(f'>{label}<', html)

    def test_week_strip_marks_prescribed_day_not_rest(self):
        # build_example_payload tem um unico dia, day_id='seg' — vira
        # <button> clicavel (pula pra Treino); os outros 6 dias da semana
        # ficam <span class="... is-rest"> (Descanso, sem clique — nao ha
        # treino nenhum pra abrir). "hoje" varia por execucao do teste,
        # entao nao travamos qual dia especifico esta marcado is-today.
        html = _render(build_example_payload())

        self.assertIn('data-workout-jump-panel="workout-panel-treino"', html)
        self.assertIn('data-workout-jump-day="workout-tab-seg"', html)
        self.assertIn('is-rest" title="Descanso"', html)

    def test_week_strip_marks_complete_day_from_load_history(self):
        import datetime

        payload = build_example_payload()  # dia unico day_id='seg'
        # segunda-feira da semana CORRENTE (build_week_overview usa date.today()
        # internamente, entao a carga registrada precisa cair na mesma semana
        # de "hoje" pra aparecer, nao importa quando o teste rodar).
        today = datetime.date.today()
        monday = today - datetime.timedelta(days=today.weekday())
        html = _render(payload, load_history=[
            {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': monday.isoformat(), 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1'},
        ])

        self.assertIn('carga registrada', html)

    def test_program_summary_headline_and_body_render(self):
        html = _render(build_example_payload())

        self.assertIn('workout-summary-card', html)
        self.assertIn('Programa de exemplo', html)
        self.assertIn('Montado pra rodar', html)

    def test_week_strip_shows_flame_icon(self):
        html = _render(build_example_payload())

        self.assertIn('workout-week-strip__flame', html)

    def test_week_strip_shows_streak_label(self):
        # build_example_payload tem 1 dia prescrito ('seg') -- "0 de 1" ou
        # "1 de 1" dependendo se caiu carga essa semana no teste; so' checa
        # que o rotulo aparece, sem travar o numero exato.
        html = _render(build_example_payload())

        self.assertIn('dia com treino', html)

    def test_week_strip_no_streak_label_when_no_days_prescribed(self):
        payload = build_example_payload()
        payload['days'] = []

        html = _render(payload)

        self.assertNotIn('dia com treino', html)
        self.assertNotIn('dias com treino', html)


class CardioPeriodizacaoCycleNavTests(TestCase):
    """Botao de ciclo "Treino" do bottom nav (pedido do Renan): um SO' slot
    alterna Treino/Cardio/Periodizacao a cada toque, em vez de 3 botoes
    fixos. Cardio/Periodizacao saem da lista de alvos quando o payload nao
    tem esse dado (aditivo ao schema, ver schema.py)."""

    def test_cycle_targets_only_treino_without_cardio_or_periodization(self):
        html = _render(build_example_payload())

        match = re.search(r'data-cycle-targets="([^"]*)"', html)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), 'workout-panel-treino')

    def test_cycle_targets_include_cardio_when_present(self):
        payload = build_example_payload()
        payload['cardio'] = {'sessions': [{'title': 'LISS', 'badge': '', 'details': [], 'note': ''}]}

        html = _render(payload)

        match = re.search(r'data-cycle-targets="([^"]*)"', html)
        self.assertEqual(match.group(1), 'workout-panel-treino|workout-panel-cardio')

    def test_cycle_targets_include_both_when_present(self):
        payload = build_example_payload()
        payload['cardio'] = {'sessions': [{'title': 'LISS', 'badge': '', 'details': [], 'note': ''}]}
        payload['periodization'] = {
            'weeks_table': [{'week': 'S1', 'focus': 'x', 'reps': 'x', 'guidance': 'x'}],
            'volume_table': [], 'note': '', 'chart': [],
        }

        html = _render(payload)

        match = re.search(r'data-cycle-targets="([^"]*)"', html)
        self.assertEqual(match.group(1), 'workout-panel-treino|workout-panel-cardio|workout-panel-periodizacao')

    def test_cardio_panel_empty_without_cardio_data(self):
        html = _render(build_example_payload())

        self.assertNotIn('workout-cardio-card', html)

    def test_periodization_panel_empty_without_periodization_data(self):
        html = _render(build_example_payload())

        self.assertNotIn('workout-period-chart', html)
        self.assertNotIn('Semana a semana', html)


class CardioPeriodizacaoPanelContentTests(TestCase):
    def test_cardio_session_renders_title_badge_details_and_note(self):
        payload = build_example_payload()
        payload['cardio'] = {
            'sessions': [{
                'title': 'LISS leve',
                'badge': 'Quarta · pós-treino',
                'details': [{'label': 'Duração', 'value': '20 min contínuos'}],
                'note': 'Feito depois do treino de superior.',
            }],
        }

        html = _render(payload)

        self.assertIn('LISS leve', html)
        self.assertIn('Quarta · pós-treino', html)
        self.assertIn('Duração', html)
        self.assertIn('20 min contínuos', html)
        self.assertIn('Feito depois do treino de superior.', html)

    def test_periodization_renders_chart_weeks_table_and_volume_table(self):
        payload = build_example_payload()
        payload['periodization'] = {
            'weeks_table': [{'week': 'Semana 1', 'focus': 'Adaptação', 'reps': 'Teto', 'guidance': 'Carga base'}],
            'volume_table': [{'muscle_group': 'Quadríceps', 'sets_per_week': '~22', 'frequency': '2×/sem', 'where': 'Terça'}],
            'note': 'Respeite o deload.',
            'chart': [{'label': 'S1', 'focus': 'Adaptação', 'reps': 'Teto', 'color': '#FB7185', 'bg': '#FFF1F2', 'fg': '#BE123C', 'h': 65}],
        }

        html = _render(payload)

        self.assertIn('workout-period-chart', html)
        self.assertIn('background:#FB7185', html)
        self.assertIn('Semana 1', html)
        self.assertIn('Carga base', html)
        self.assertIn('Quadríceps', html)
        self.assertIn('Respeite o deload.', html)

    def test_periodization_without_chart_omits_chart_section(self):
        payload = build_example_payload()
        payload['periodization'] = {
            'weeks_table': [{'week': 'Semana 1', 'focus': 'x', 'reps': 'x', 'guidance': 'x'}],
            'volume_table': [], 'note': '', 'chart': [],
        }

        html = _render(payload)

        self.assertNotIn('workout-period-chart', html)
        self.assertIn('Semana a semana', html)


class WorkoutAssessmentPanelTests(TestCase):
    """Avaliacao nao usa contexto Django nenhum -- o painel e' montado
    inteiro por assessments.js (fetch client-side de avaliacoes.json),
    igual aos 10 templates legados. O template so precisa expor o
    container certo pro mountPanel() encontrar e os assets certos."""

    def test_panel_container_exists_and_starts_empty(self):
        html = _render(build_example_payload())

        self.assertIn('<section id="workout-panel-avaliacao"', html)

    def test_loads_assessments_script_and_stylesheet(self):
        html = _render(build_example_payload())

        self.assertIn('js/public_workouts/assessments.js', html)
        self.assertIn('css/public_workouts/assessments.css', html)


class WorkoutProfilePanelTests(TestCase):
    def test_payments_link_shown_when_portal_url_provided(self):
        html = _render(build_example_payload(), customer_portal_url='https://billing.stripe.com/session/abc')

        self.assertIn('href="https://billing.stripe.com/session/abc"', html)
        self.assertIn('Pagamentos', html)

    def test_payments_shows_unavailable_without_portal_url(self):
        html = _render(build_example_payload(), customer_portal_url=None)

        self.assertIn('indisponível', html)

    def test_theme_toggle_button_present(self):
        html = _render(build_example_payload())

        self.assertIn('data-ui="theme-toggle"', html)

    def test_profile_header_shows_full_name_and_email(self):
        html = _render(build_example_payload(), student_name='Juliana Silva', account_email='juliana@example.com')

        self.assertIn('<strong class="workout-profile-header__name">Juliana Silva</strong>', html)
        self.assertIn('juliana@example.com', html)

    def test_profile_header_omits_email_when_absent(self):
        html = _render(build_example_payload(), student_name='Juliana Silva', account_email=None)

        self.assertNotIn('workout-profile-header__email', html)

    def test_dados_pessoais_row_shows_email(self):
        html = _render(build_example_payload(), account_email='juliana@example.com')

        self.assertIn('Dados pessoais', html)
        self.assertIn('juliana@example.com', html)

    def test_signout_button_present_with_slug_scoped_url(self):
        html = _render(build_example_payload(), plan_slug='juliana')

        self.assertIn('Sair da conta', html)
        self.assertIn('data-signout-url="/renan/juliana/sair"', html)


class HumanizeMovementSlugFilterTests(TestCase):
    def test_replaces_hyphens_and_capitalizes(self):
        self.assertEqual(humanize_movement_slug('agachamento-livre'), 'Agachamento livre')

    def test_empty_string_stays_empty(self):
        self.assertEqual(humanize_movement_slug(''), '')

    def test_none_stays_empty(self):
        self.assertEqual(humanize_movement_slug(None), '')


class DictGetFilterTests(TestCase):
    def test_returns_value_for_existing_key(self):
        self.assertEqual(dict_get({'a': 1, 'b': 2}, 'b'), 2)

    def test_returns_none_for_missing_key(self):
        self.assertIsNone(dict_get({'a': 1}, 'z'))

    def test_returns_none_for_empty_dict(self):
        self.assertIsNone(dict_get({}, 'a'))

    def test_returns_none_for_none_dict(self):
        self.assertIsNone(dict_get(None, 'a'))


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

    def test_first_point_never_marks_program_change(self):
        # Nao ha "antes" pra contrastar no primeiro ponto da serie, mesmo
        # com program_id preenchido.
        entries = [
            {'weight_kg': 90.0, 'performed_on': '2026-01-05', 'program_id': 'bruno-2026-q1'},
            {'weight_kg': 100.0, 'performed_on': '2026-01-12', 'program_id': 'bruno-2026-q1'},
        ]

        result = load_chart_points(entries)

        self.assertFalse(result['points'][0]['is_program_change'])
        self.assertFalse(result['points'][1]['is_program_change'])

    def test_marks_program_change_when_program_id_differs_from_previous_point(self):
        entries = [
            {'weight_kg': 90.0, 'performed_on': '2026-01-05', 'program_id': 'bruno-2026-q1', 'week_in_program': 4},
            {'weight_kg': 100.0, 'performed_on': '2026-04-01', 'program_id': 'bruno-2026-q2', 'week_in_program': 1},
        ]

        result = load_chart_points(entries)

        self.assertFalse(result['points'][0]['is_program_change'])
        self.assertTrue(result['points'][1]['is_program_change'])
        self.assertEqual(result['points'][1]['program_id'], 'bruno-2026-q2')
        self.assertEqual(result['points'][1]['week_in_program'], 1)

    def test_empty_program_id_never_marks_change(self):
        # Carga sem programa associado (registrada fora de qualquer versao
        # publicada) nunca conta como "troca" — so ruido, nao sinal.
        entries = [
            {'weight_kg': 90.0, 'performed_on': '2026-01-05', 'program_id': 'bruno-2026-q1'},
            {'weight_kg': 95.0, 'performed_on': '2026-01-08', 'program_id': ''},
            {'weight_kg': 100.0, 'performed_on': '2026-01-12', 'program_id': ''},
        ]

        result = load_chart_points(entries)

        self.assertFalse(any(point['is_program_change'] for point in result['points']))

    def test_program_id_reappears_after_gap_still_compares_to_last_known(self):
        # Um ponto no meio sem program_id nao apaga o contexto: a troca
        # ainda e' detectada contra o ultimo program_id conhecido.
        entries = [
            {'weight_kg': 90.0, 'performed_on': '2026-01-05', 'program_id': 'bruno-2026-q1'},
            {'weight_kg': 95.0, 'performed_on': '2026-01-08', 'program_id': ''},
            {'weight_kg': 100.0, 'performed_on': '2026-04-01', 'program_id': 'bruno-2026-q2'},
        ]

        result = load_chart_points(entries)

        self.assertFalse(result['points'][0]['is_program_change'])
        self.assertFalse(result['points'][1]['is_program_change'])
        self.assertTrue(result['points'][2]['is_program_change'])

    def test_missing_program_id_key_defaults_to_empty_and_never_marks(self):
        # list_load_history sempre inclui program_id, mas o filtro nao deve
        # quebrar se um chamador futuro omitir a chave.
        entries = [
            {'weight_kg': 90.0, 'performed_on': '2026-01-05'},
            {'weight_kg': 100.0, 'performed_on': '2026-01-12'},
        ]

        result = load_chart_points(entries)

        self.assertFalse(result['points'][1]['is_program_change'])
        self.assertEqual(result['points'][0]['program_id'], '')

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


class GlossaryHighlightFilterTests(TestCase):
    def test_wraps_known_term_with_glossary_bubble(self):
        html = glossary_highlight('3x8-10 · RIR 2')

        self.assertIn('data-workout-glossary', html)
        self.assertIn('>RIR<', html)
        self.assertIn('Reps in Reserve', html)
        self.assertIn('3x8-10', html)

    def test_matches_are_case_insensitive_but_word_bounded(self):
        # 'top' precisa casar isolado (Top Set), mas NUNCA dentro de outra
        # palavra que so' contem as mesmas letras (ex.: 'topo').
        html = glossary_highlight('3x Top (6-8) no topo da tabela')

        self.assertEqual(html.count('data-workout-glossary'), 1)
        self.assertIn('topo da tabela', html)

    def test_text_without_jargon_is_unchanged_but_escaped(self):
        html = glossary_highlight('3x10-12')

        self.assertEqual(html, '3x10-12')

    def test_empty_text_returns_empty(self):
        self.assertEqual(glossary_highlight(''), '')

    def test_surrounding_text_is_html_escaped(self):
        html = glossary_highlight('<script>alert(1)</script> RIR 3')

        self.assertNotIn('<script>alert', html)
        self.assertIn('&lt;script&gt;', html)

    def test_multiple_known_terms_each_get_their_own_bubble(self):
        html = glossary_highlight('2x Prep -> 1x Feeder -> 3x Top (6-8)')

        self.assertEqual(html.count('data-workout-glossary'), 3)

    def test_ramp_appends_suggested_weight_to_matching_term_only(self):
        html = glossary_highlight('3x Top (6-8)', ramp=('top', [82.5]))

        self.assertIn('Peso sugerido', html)
        self.assertIn('82,5 kg', html)

    def test_ramp_never_touches_a_different_term(self):
        # ramp e' pro estagio 'feeder', mas o texto so' tem 'Top' -- nao
        # pode vazar peso nenhum pro termo errado.
        html = glossary_highlight('3x Top (6-8)', ramp=('feeder', [60.0]))

        self.assertNotIn('Peso sugerido', html)

    def test_ramp_with_multiple_weights_shows_full_progression(self):
        html = glossary_highlight('2x Prep', ramp=('prep', [40.0, 55.0]))

        self.assertIn('40,0 kg → 55,0 kg', html)

    def test_no_ramp_keeps_original_static_definition(self):
        html = glossary_highlight('3x Top (6-8)')

        self.assertNotIn('Peso sugerido', html)


class MovementCardGlossaryRenderTests(TestCase):
    def test_reps_spec_with_rir_renders_glossary_bubble(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['reps_spec'] = '3x8-10'
        payload['days'][0]['blocks'][0]['movements'][0]['rir_spec'] = 'RIR 2'

        html = _render(payload)

        self.assertIn('data-workout-glossary', html)
        self.assertIn('Reps in Reserve', html)

    def test_reps_spec_without_jargon_has_no_glossary_bubble(self):
        # 'data-workout-glossary' sozinho aparece SEMPRE na pagina, mesmo sem
        # nenhum termo casado — e' o nome do atributo dentro do <script>
        # inline (delegacao de clique). O que precisa estar ausente e' a
        # tag de verdade que glossary_highlight gera.
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['reps_spec'] = '3x8-10'
        payload['days'][0]['blocks'][0]['movements'][0]['rir_spec'] = ''

        html = _render(payload)

        self.assertNotIn('<span class="workout-glossary-term"', html)


class RepsPhasesFilterTests(TestCase):
    def test_single_phase_returns_empty_list(self):
        # reps_spec simples ("3x12", sem "→") nao vale a pena virar chip
        # grande -- o template mantem a linha unica de sempre.
        self.assertEqual(reps_phases('3x12'), [])

    def test_empty_reps_spec_returns_empty_list(self):
        self.assertEqual(reps_phases(''), [])
        self.assertEqual(reps_phases(None), [])

    def test_splits_multi_phase_reps_spec(self):
        phases = reps_phases('2-3× Prep → 1× Feeder → 3× Top (6-8)')

        self.assertEqual(len(phases), 3)
        self.assertEqual(phases[0]['phase'], 'prep')
        self.assertEqual(phases[1]['phase'], 'feeder')
        self.assertEqual(phases[2]['phase'], 'top')

    def test_amrap_detected_as_max_phase(self):
        phases = reps_phases('2× Prep → 1× AMRAP')

        self.assertEqual(phases[1]['phase'], 'max')

    def test_unrecognized_phase_falls_back_to_plain(self):
        phases = reps_phases('2× Algo → 1× Outro')

        self.assertEqual(phases[0]['phase'], 'plain')
        self.assertEqual(phases[1]['phase'], 'plain')

    def test_phase_text_is_glossary_highlighted(self):
        phases = reps_phases('2× Prep → 1× Feeder')

        self.assertIn('data-workout-glossary', phases[0]['text'])
        self.assertIn('data-workout-glossary', phases[1]['text'])

    def test_without_top_weight_no_ramp_appears_in_any_bubble(self):
        phases = reps_phases('2× Prep → 1× Feeder → 3× Top (6-8)')

        for phase in phases:
            self.assertNotIn('Peso sugerido', phase['text'])

    def test_with_top_weight_each_stage_gets_its_own_ramp(self):
        phases = reps_phases('2× Prep → 1× Feeder → 3× Top (6-8)', top_weight_kg=100.0)

        prep, feeder, top = phases
        self.assertIn('Peso sugerido', prep['text'])
        self.assertIn('Peso sugerido', feeder['text'])
        self.assertIn('Peso sugerido', top['text'])
        # Top e' sempre a propria referencia (100kg), sem ramp — so' 1 numero.
        self.assertIn('100,0 kg.', top['text'])

    def test_prep_ramp_is_lighter_than_feeder_ramp(self):
        phases = reps_phases('2× Prep → 1× Feeder → 3× Top (6-8)', top_weight_kg=100.0)

        prep_text, feeder_text = phases[0]['text'], phases[1]['text']
        # prep (40-55%) sempre mais leve que feeder (60-80%) pro mesmo Top.
        self.assertIn('40,0 kg', prep_text)
        self.assertIn('70,0 kg', feeder_text)

    def test_plain_phase_never_gets_a_ramp(self):
        phases = reps_phases('2× Algo → 1× Outro', top_weight_kg=100.0)

        for phase in phases:
            self.assertNotIn('Peso sugerido', phase['text'])

    def test_ramp_set_count_follows_the_segments_own_prefix(self):
        phases = reps_phases('2× Prep → 1× Feeder → 3× Top (6-8)', top_weight_kg=100.0)

        prep_text = phases[0]['text']
        # 2 sets de Prep -> ramp com 2 numeros distintos (piso e teto da faixa).
        self.assertIn('40,0 kg → 55,0 kg', prep_text)


class MovementCardPhaseChipRenderTests(TestCase):
    def test_multi_phase_reps_spec_renders_chip_row(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['reps_spec'] = '2× Prep → 3× Top (6-8)'
        payload['days'][0]['blocks'][0]['movements'][0]['rir_spec'] = 'RIR 1-2'

        html = _render(payload)

        self.assertIn('workout-phase-row', html)
        self.assertIn('workout-phase-chip--prep', html)
        self.assertIn('workout-phase-chip--top', html)
        self.assertIn('workout-phase-note', html)

    def test_single_phase_reps_spec_keeps_plain_line(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['reps_spec'] = '3x12'
        payload['days'][0]['blocks'][0]['movements'][0]['rir_spec'] = 'RIR 2'

        html = _render(payload)

        self.assertNotIn('workout-phase-row', html)
        self.assertIn('3x12', html)

    def test_ramp_appears_in_phase_chip_tooltips_once_a_top_weight_resolves(self):
        # pedido do Renan: "ao registrar a kilagem aparecer a kilagem
        # apropriada no balão" -- fim-a-fim, com 1RM real disponivel.
        payload = build_example_payload()
        movement = payload['days'][0]['blocks'][0]['movements'][0]
        movement['reps_spec'] = '2× Prep → 1× Feeder → 3× Top (6-8)'
        movement['rir_spec'] = 'RIR 1-2'
        one_rm = {movement['movement_slug']: {'value_kg': 100.0}}

        html = _render(payload, one_rep_max_by_movement=one_rm)

        self.assertIn('Peso sugerido', html)

    def test_no_ramp_in_tooltips_without_any_one_rep_max_data(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['reps_spec'] = '2× Prep → 1× Feeder → 3× Top (6-8)'
        payload['days'][0]['blocks'][0]['movements'][0]['rir_spec'] = 'RIR 1-2'

        html = _render(payload)

        self.assertNotIn('Peso sugerido', html)


class MovementDisplayNameAndVariationRenderTests(TestCase):
    """`movement.name` (portugues, escrito pelo treinador) e' aditivo —
    achado real: nomes estavam saindo em ingles (slug do MuscleWiki
    humanizado) porque o template nunca usava `name`, so' `movement_slug`."""

    def test_movement_with_name_shows_portuguese_text_not_slug(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['name'] = 'Agachamento com barra livre'
        # slug continua em ingles de proposito (vem do MuscleWiki) -- so' a
        # exibicao muda.
        payload['days'][0]['blocks'][0]['movements'][0]['movement_slug'] = 'barbell-squat'

        html = _render(payload)

        self.assertIn('Agachamento com barra livre', html)
        self.assertNotIn('>Barbell squat<', html)

    def test_movement_without_name_falls_back_to_humanized_slug(self):
        # Movimento publicado ANTES desta fatia, sem `name` no payload.
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['movement_slug'] = 'barbell-squat'
        payload['days'][0]['blocks'][0]['movements'][0].pop('name', None)

        html = _render(payload)

        self.assertIn('Barbell squat', html)

    def test_single_variation_renders_as_link(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['variations'] = [
            {'label': 'Supino com halteres', 'reference_url': 'https://musclewiki.com/exercise/dumbbell-bench-press'},
        ]

        html = _render(payload)

        self.assertIn('workout-movement-variation', html)
        self.assertIn('Variação:', html)
        self.assertIn('href="https://musclewiki.com/exercise/dumbbell-bench-press"', html)
        self.assertIn('Supino com halteres', html)

    def test_variation_is_hidden_by_default_behind_a_toggle(self):
        # Pedido do Renan: mesmo padrao de clique-expande do registro de
        # carga -- oculto por padrao, um toggle proprio revela.
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['variations'] = [
            {'label': 'Supino com halteres', 'reference_url': 'https://musclewiki.com/exercise/dumbbell-bench-press'},
        ]

        html = _render(payload)

        self.assertIn('data-workout-variation-toggle', html)
        self.assertIn('<span class="workout-movement-variation" data-workout-variation hidden>', html)

    def test_variation_toggle_available_regardless_of_is_tracked(self):
        # Igual ao registro de carga: a disponibilidade do toggle nao
        # depende de is_tracked.
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['is_tracked'] = False
        payload['days'][0]['blocks'][0]['movements'][0]['variations'] = [
            {'label': 'Supino com halteres', 'reference_url': 'https://musclewiki.com/exercise/dumbbell-bench-press'},
        ]

        html = _render(payload)

        self.assertIn('data-workout-variation-toggle', html)

    def test_multiple_variations_all_render(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['variations'] = [
            {'label': 'Hack squat', 'reference_url': 'https://musclewiki.com/exercise/machine-hack-squat'},
            {'label': 'Leg press 45°', 'reference_url': 'https://musclewiki.com/exercise/machine-leg-press'},
        ]

        html = _render(payload)

        self.assertIn('Hack squat', html)
        self.assertIn('Leg press 45°', html)

    def test_movement_without_variations_omits_variation_line(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0].pop('variations', None)

        html = _render(payload)

        self.assertNotIn('workout-movement-variation', html)


def _canonical_periodization(weeks):
    return {'weeks': weeks, 'volume_table': [], 'note': ''}


_SIX_CANONICAL_WEEKS = [
    {'week_number': 1, 'phase_type': 'adaptation'},
    {'week_number': 2, 'phase_type': 'volume'},
    {'week_number': 3, 'phase_type': 'strength_hypertrophy'},
    {'week_number': 4, 'phase_type': 'intensity'},
    {'week_number': 5, 'phase_type': 'peak'},
    {'week_number': 6, 'phase_type': 'deload'},
]


class PeriodizationChartPointsFilterTests(TestCase):
    def test_legacy_chart_passthrough_gets_week_number_none(self):
        chart = [{'label': 'S1', 'focus': 'x', 'reps': 'x', 'color': '#fff', 'bg': '#fff', 'fg': '#fff', 'h': 50}]

        points = periodization_chart_points({'chart': chart})

        self.assertEqual(points[0]['week_number'], None)
        self.assertEqual(points[0]['label'], 'S1')

    def test_canonical_weeks_take_priority_over_legacy_chart(self):
        periodization = {
            'weeks': _SIX_CANONICAL_WEEKS,
            'chart': [{'label': 'legado', 'focus': 'x', 'reps': 'x', 'color': '#fff', 'bg': '#fff', 'fg': '#fff', 'h': 1}],
        }

        points = periodization_chart_points(periodization)

        self.assertEqual(len(points), 6)
        self.assertEqual(points[0]['label'], 'S1')
        self.assertIsNotNone(points[0]['week_number'])

    def test_empty_periodization_returns_empty_list(self):
        self.assertEqual(periodization_chart_points({}), [])
        self.assertEqual(periodization_chart_points(None), [])


class CurrentPeriodWeekNumberFilterTests(TestCase):
    def test_delegates_to_periodization_module(self):
        payload = {
            'started_on': '2026-01-05',
            'periodization': _canonical_periodization(_SIX_CANONICAL_WEEKS),
        }

        # sem `today` explicito o filtro usa date.today() -- so' confirma
        # que nao quebra e devolve um inteiro dentro da faixa esperada.
        result = current_period_week_number(payload)

        self.assertTrue(result is None or 1 <= result <= 6)

    def test_none_without_periodization(self):
        self.assertIsNone(current_period_week_number({'started_on': '2026-01-05'}))


class PeriodizationPhaseBannerTagTests(TestCase):
    def test_invisible_without_canonical_weeks(self):
        payload = build_example_payload()

        banner = periodization_phase_banner(payload)

        self.assertFalse(banner['visible'])

    def test_visible_with_canonical_weeks_shows_phase_details(self):
        payload = build_example_payload()
        payload['periodization'] = _canonical_periodization(_SIX_CANONICAL_WEEKS)

        banner = periodization_phase_banner(payload)

        self.assertTrue(banner['visible'])
        self.assertIn(banner['phase_label'], [p.label for p in PHASE_PROFILES.values()])
        self.assertIsInstance(banner['total_weeks'], int)
        self.assertEqual(banner['total_weeks'], 6)


class MovementLoadDisplayTagTests(TestCase):
    def _movement(self, **overrides):
        movement = {
            'movement_slug': 'hack-squat',
            'reps_spec': '3× Top (6-8)',
            'rir_spec': 'RIR 1-2',
            'load_type': 'free',
            'load_value': None,
        }
        movement.update(overrides)
        return movement

    def test_fixed_kg_short_circuits_everything_else(self):
        movement = self._movement(load_type='fixed_kg', load_value=40)

        result = movement_load_display(movement, {}, None, {}, [])

        self.assertEqual(result, {'kind': 'fixed_kg', 'value_kg': 40, 'percentage': None, 'show_registration_hint': False})

    def test_percentage_of_rm_without_one_rep_max_shows_percentage_and_hint(self):
        movement = self._movement(load_type='percentage_of_rm', load_value=70.0)

        result = movement_load_display(movement, {}, None, {}, [])

        self.assertEqual(result['kind'], 'percentage')
        self.assertIsNone(result['value_kg'])
        self.assertEqual(result['percentage'], 70.0)
        self.assertTrue(result['show_registration_hint'])

    def test_percentage_of_rm_with_one_rep_max_computes_kg(self):
        movement = self._movement(load_type='percentage_of_rm', load_value=70.0)
        one_rm = {'hack-squat': {'value_kg': 100.0}}

        result = movement_load_display(movement, {}, None, one_rm, [])

        self.assertEqual(result['kind'], 'percentage')
        self.assertEqual(result['value_kg'], 70.0)
        self.assertFalse(result['show_registration_hint'])

    def test_canonical_phase_with_prior_log_uses_progressive_ratio(self):
        movement = self._movement()
        payload = {
            'program_id': 'juliana-2026-q1', 'started_on': '2026-01-05',
            'periodization': _canonical_periodization(_SIX_CANONICAL_WEEKS),
        }
        load_history = [{
            'movement_slug': 'hack-squat', 'weight_kg': 80.0,
            'performed_on': '2026-01-05', 'program_id': 'juliana-2026-q1',
        }]

        result = movement_load_display(movement, payload, PHASE_PROFILES['volume'], {}, load_history)

        self.assertEqual(result['kind'], 'phase_progressive')
        self.assertGreater(result['value_kg'], 80.0)
        self.assertFalse(result['show_registration_hint'])

    def test_canonical_phase_without_prior_log_falls_back_to_rir_estimate(self):
        movement = self._movement()  # reps_spec/rir_spec parseaveis
        payload = {
            'program_id': 'juliana-2026-q1', 'started_on': '2026-01-05',
            'periodization': _canonical_periodization(_SIX_CANONICAL_WEEKS),
        }
        one_rm = {'hack-squat': {'value_kg': 100.0}}

        result = movement_load_display(movement, payload, PHASE_PROFILES['adaptation'], one_rm, [])

        self.assertEqual(result['kind'], 'rir_estimate')
        self.assertIsNotNone(result['value_kg'])

    def test_no_phase_uses_rir_estimate_when_one_rep_max_available(self):
        movement = self._movement()
        one_rm = {'hack-squat': {'value_kg': 100.0}}

        result = movement_load_display(movement, {}, None, one_rm, [])

        self.assertEqual(result['kind'], 'rir_estimate')
        self.assertIsNotNone(result['value_kg'])
        self.assertFalse(result['show_registration_hint'])

    def test_nothing_resolves_without_one_rep_max_shows_free_and_hint(self):
        movement = self._movement()

        result = movement_load_display(movement, {}, None, {}, [])

        self.assertEqual(result['kind'], 'free')
        self.assertIsNone(result['value_kg'])
        self.assertTrue(result['show_registration_hint'])

    def test_ambiguous_reps_spec_with_one_rep_max_shows_free_without_hint(self):
        # 1RM ja existe (o aluno ja registrou carga) -- so' esse exercicio
        # em especifico tem texto ambiguo demais pra estimar. Nao mostra o
        # hint de registro (seria enganoso, ele ja registrou).
        movement = self._movement(reps_spec='Feeder → 3× Top (crescente) → 1× Max')
        one_rm = {'hack-squat': {'value_kg': 100.0}}

        result = movement_load_display(movement, {}, None, one_rm, [])

        self.assertEqual(result['kind'], 'free')
        self.assertFalse(result['show_registration_hint'])


class PeriodizationCanonicalTreinoRenderTests(TestCase):
    """Renderizacao ponta-a-ponta: gráfico com destaque de semana atual,
    banner de fase, e a cascata de carga integrada no template real."""

    def test_current_week_column_gets_highlight_class(self):
        payload = build_example_payload()
        payload['started_on'] = '2026-01-05'
        payload['periodization'] = _canonical_periodization(_SIX_CANONICAL_WEEKS)

        html = _render(payload)

        self.assertIn('workout-period-chart__col--current', html)

    def test_legacy_client_chart_never_gets_highlight_class(self):
        payload = build_example_payload()
        payload['periodization'] = {
            'weeks_table': [{'week': 'S1', 'focus': 'x', 'reps': 'x', 'guidance': 'x'}],
            'volume_table': [], 'note': '',
            'chart': [{'label': 'S1', 'focus': 'x', 'reps': 'x', 'color': '#fff', 'bg': '#fff', 'fg': '#fff', 'h': 50}],
        }

        html = _render(payload)

        self.assertNotIn('workout-period-chart__col--current', html)

    def test_phase_banner_appears_for_canonical_client(self):
        payload = build_example_payload()
        payload['started_on'] = '2026-01-05'
        payload['periodization'] = _canonical_periodization(_SIX_CANONICAL_WEEKS)

        html = _render(payload)

        self.assertIn('workout-phase-banner', html)

    def test_phase_banner_absent_for_legacy_client(self):
        html = _render(build_example_payload())

        self.assertNotIn('workout-phase-banner', html)

    def test_registration_hint_renders_in_treino_tab_without_one_rep_max(self):
        html = _render(build_example_payload())

        self.assertIn('Registre sua carga para controlar a kilagem.', html)

    def test_registration_hint_absent_once_one_rep_max_exists(self):
        payload = build_example_payload()
        movement = payload['days'][0]['blocks'][0]['movements'][0]
        one_rm = {movement['movement_slug']: {'value_kg': 100.0}}

        html = _render(payload, one_rep_max_by_movement=one_rm)

        self.assertNotIn('Registre sua carga para controlar a kilagem.', html)
