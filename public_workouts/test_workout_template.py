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
from datetime import date, datetime, timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import TestCase
from django.utils import timezone

from public_workouts.models import (
    PublicWorkoutMovement,
    PublicWorkoutMovementEquipment,
    PublicWorkoutMovementStatus,
)
from public_workouts.periodization import PHASE_PROFILES
from public_workouts.schema import build_example_payload
from public_workouts.templatetags.public_workouts_extras import (
    current_period_week_number,
    cycle_summary_rows,
    dict_get,
    glossary_highlight,
    humanize_movement_slug,
    load_chart_points,
    movement_load_display,
    periodization_chart_points,
    periodization_phase_banner,
    personal_record,
    reps_phases,
    movement_shows_plate_calculator,
    resolve_movement_display_name,
    share_content_for_chart,
    sibling_variations,
    todays_logged_idempotency_key,
    todays_logged_reps,
    todays_logged_rir,
    todays_logged_weight,
    todays_top_set_weight,
)


def _render(
    payload: dict,
    accent_variant=None,
    program_versions=None,
    load_history=None,
    one_rep_max_by_movement=None,
    trends_by_movement=None,
    progress_snapshots=None,
    plan_slug='bruno',
    movement_labels=None,
    student_name='',
    student_photo_url=None,
    customer_portal_url=None,
    account_email=None,
) -> str:
    if progress_snapshots is None:
        # Template fixtures now follow the production contract: the graph
        # reads a prepared snapshot, while load_history remains the complete
        # visible log. Build the smallest deterministic snapshot from these
        # dict fixtures so legacy render assertions keep testing the real
        # presentation path without querying the database.
        grouped = {}
        for index, entry in enumerate(load_history or []):
            grouped.setdefault(entry.get('movement_slug'), []).append((index, entry))
        progress_snapshots = {}
        for movement_slug, indexed_entries in grouped.items():
            top_by_day = {}
            legacy_points = []
            for index, entry in indexed_entries:
                role = entry.get('set_role')
                performed_on = entry.get('performed_on')
                day = performed_on if isinstance(performed_on, date) else date.fromisoformat(str(performed_on))
                point = SimpleNamespace(
                    performed_on=day,
                    weight_kg=Decimal(str(entry['weight_kg'])) if entry.get('weight_kg') is not None else None,
                    reps=entry.get('reps'), rir=entry.get('rir'),
                    created_at=datetime.combine(day, datetime.min.time()) + timedelta(microseconds=index),
                    program_id=entry.get('program_id') or '',
                    week_in_program=entry.get('week_in_program'),
                )
                if role == 'top_set':
                    if day not in top_by_day or point.created_at > top_by_day[day].created_at:
                        top_by_day[day] = point
                elif role == 'legacy_unknown':
                    legacy_points.append(point)
            curve_points = sorted(top_by_day.values(), key=lambda point: point.performed_on)
            legacy_points.sort(key=lambda point: (point.performed_on, point.created_at))
            all_weights = [point.weight_kg for point in [*curve_points, *legacy_points] if point.weight_kg is not None]
            y_scale = None
            if all_weights:
                low, high = min(all_weights), max(all_weights)
                if low == high:
                    low, high = max(Decimal('0'), low - Decimal('2.5')), high + Decimal('2.5')
                increment = Decimal('2.5')
                y_scale = {
                    'min_kg': (low / increment).to_integral_value(rounding=ROUND_FLOOR) * increment,
                    'max_kg': (high / increment).to_integral_value(rounding=ROUND_CEILING) * increment,
                }
            trend = (trends_by_movement or {}).get(movement_slug, {})
            progress_snapshots[movement_slug] = SimpleNamespace(
                latest_top_set=curve_points[-1] if curve_points else None,
                curve_points=curve_points,
                legacy_points=legacy_points,
                has_legacy_history=any(entry.get('set_role') == 'legacy_unknown' for _, entry in indexed_entries),
                y_scale=y_scale,
                trend_signal=trend.get('label', 'insufficient_data'),
                one_rep_max=(one_rep_max_by_movement or {}).get(movement_slug),
            )
    return render_to_string('public_workouts/workout.html', {
        'program': payload,
        'accent_variant': accent_variant,
        'program_versions': program_versions or [],
        'load_history': load_history or [],
        'one_rep_max_by_movement': one_rep_max_by_movement or {},
        'trends_by_movement': trends_by_movement or {},
        'progress_snapshots': progress_snapshots,
        'plan_slug': plan_slug,
        'movement_labels': movement_labels or {},
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

    def test_free_load_explains_that_no_weight_is_prescribed(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['load_type'] = 'free'
        payload['days'][0]['blocks'][0]['movements'][0]['load_value'] = None

        html = _render(payload)

        self.assertIn('Sem carga prescrita', html)

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

    def test_load_input_widget_starts_hidden_and_has_explicit_register_button(self):
        html = _render(build_example_payload())  # is_tracked=True no exemplo

        self.assertIn('<div id="workout-load-input-seg-1-1" class="workout-load-input" data-workout-load-input', html)
        self.assertIn('data-workout-load-input data-movement-slug="agachamento-livre" data-program-id="exemplo-2026-q1" hidden', html)
        self.assertIn('class="workout-movement-register" data-workout-load-toggle aria-controls="workout-load-input-seg-1-1"', html)

    def test_register_button_controls_its_widget_without_nested_controls(self):
        html = _render(build_example_payload())

        card = re.search(r'<article class="[^"]*workout-movement-card[^"]*">(.*?)</article>', html, re.S)
        widget_id = re.search(r'data-workout-load-toggle aria-controls="([^"]+)"', card.group(1))
        widget = re.search(r'<div id="([^"]+)" class="workout-load-input"', html)

        self.assertIsNotNone(widget_id)
        self.assertEqual(widget_id.group(1), widget.group(1))
        opening_tag = card.group(0).split('>', 1)[0]
        self.assertNotIn('role="button"', opening_tag)
        self.assertNotIn('tabindex="0"', opening_tag)

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

        self.assertIn('class="workout-load-input" data-workout-load-input', html)
        self.assertIn('class="workout-movement-register" data-workout-load-toggle aria-controls=', html)
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

    def test_movement_label_lookup_shows_pt_br_name_instead_of_slug_guess(self):
        payload = build_example_payload()
        slug = payload['days'][0]['blocks'][0]['movements'][0]['movement_slug']

        html = _render(payload, movement_labels={slug: 'Nome revisado pelo treinador'})

        self.assertIn('Nome revisado pelo treinador', html)

    def test_movement_label_lookup_missing_falls_back_to_humanized_slug(self):
        html = _render(build_example_payload(), movement_labels={})

        self.assertIn('Agachamento livre', html)  # mesmo palpite de sempre

    def test_load_input_widget_has_stepper_and_hint(self):
        html = _render(build_example_payload())  # is_tracked=True no exemplo

        self.assertIn('data-workout-load-step="-2.5"', html)
        self.assertIn('data-workout-load-step="2.5"', html)
        self.assertIn('data-workout-load-hint', html)

    def test_load_input_widget_has_warmup_toggle_unchecked_by_default(self):
        # Plano curva-grafico-hierarquia-e-set-role.md, §2.3.6/§7.10.
        html = _render(build_example_payload())

        self.assertIn('data-workout-load-warmup-toggle', html)
        self.assertNotIn('data-workout-load-warmup-toggle checked', html)

    def test_load_input_widget_has_reps_and_effort_controls(self):
        # Plano curva-carga-completa-reps-rir-recorde, Fase 1 (§1.3/§1.4).
        html = _render(build_example_payload())

        self.assertIn('data-workout-reps-field', html)
        self.assertIn('data-workout-reps-step="-1"', html)
        self.assertIn('data-workout-reps-step="1"', html)
        self.assertIn('data-workout-rir-picker', html)
        self.assertIn('data-rir-value="0"', html)
        self.assertIn('data-rir-value="4"', html)
        self.assertIn('data-workout-rir-other-toggle', html)
        self.assertIn('data-workout-rir-other-field', html)
        self.assertIn('data-workout-rir-clear', html)
        self.assertIn('Esforço · opcional', html)

    def test_load_input_widget_prefills_todays_reps(self):
        today = timezone.localdate().isoformat()
        html = _render(
            build_example_payload(),
            load_history=[
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': None, 'performed_on': today, 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1', 'set_role': 'top_set'},
            ],
        )

        self.assertIn('data-workout-reps-field', html)
        self.assertIn('value="8"', html)

    def test_load_input_widget_hides_plate_calculator_by_default(self):
        # Sem nenhum PublicWorkoutMovement curado no catalogo (fixture
        # limpa), a calculadora nunca aparece -- nunca inferida.
        html = _render(build_example_payload())

        self.assertNotIn('data-workout-plate-calculator', html)

    def test_load_input_widget_shows_plate_calculator_when_curated(self):
        PublicWorkoutMovement.objects.create(
            slug='agachamento-livre', label_pt='Agachamento livre',
            equipment_type=PublicWorkoutMovementEquipment.BARBELL, logged_weight_includes_bar=True,
        )
        html = _render(build_example_payload())

        self.assertIn('data-workout-plate-calculator', html)
        self.assertIn('data-plate-inventory', html)
        self.assertIn('Montar anilhas', html)

    def test_load_input_widget_exposes_todays_idempotency_key_for_correction(self):
        today = timezone.localdate().isoformat()
        html = _render(
            build_example_payload(),
            load_history=[
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': None, 'performed_on': today, 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k-hoje', 'set_role': 'top_set'},
            ],
        )

        self.assertIn('data-today-idempotency-key="k-hoje"', html)

    def test_load_input_widget_omits_idempotency_key_without_todays_entry(self):
        html = _render(build_example_payload(), load_history=[])

        self.assertNotIn('data-today-idempotency-key', html)

    def test_load_input_widget_prefills_todays_rir_as_data_attribute(self):
        # RIR nunca vira um `value=""` de input comum (a selecao mora no
        # picker) -- o servidor so expoe o dado via data-today-rir, e o
        # JS decide se cai num atalho exato ou em "outro valor".
        today = timezone.localdate().isoformat()
        html = _render(
            build_example_payload(),
            load_history=[
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': 2.0, 'performed_on': today, 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1', 'set_role': 'top_set'},
            ],
        )

        self.assertIn('data-today-rir="2.0"', html)

    def test_load_input_targets_the_top_set_when_a_warmup_was_logged_after_it(self):
        today = timezone.localdate().isoformat()
        html = _render(build_example_payload(), load_history=[
            {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': 2.0,
             'performed_on': today, 'program_id': '', 'week_in_program': None,
             'idempotency_key': 'top-set-today', 'set_role': 'top_set'},
            {'movement_slug': 'agachamento-livre', 'weight_kg': 60.0, 'reps': 10, 'rir': None,
             'performed_on': today, 'program_id': '', 'week_in_program': None,
             'idempotency_key': 'warmup-later', 'set_role': 'warmup'},
        ])

        widget_start = html.index('data-workout-load-input')
        widget = html[widget_start:html.index('data-workout-load-status', widget_start)]
        self.assertIn('data-today-idempotency-key="top-set-today"', widget)
        self.assertIn('data-today-top-set-idempotency-key="top-set-today"', widget)
        self.assertIn('data-today-warmup-idempotency-key="warmup-later"', widget)
        self.assertIn('value="100.0"', widget)
        self.assertNotIn('data-workout-load-warmup-toggle checked', widget)

    def test_load_input_selects_existing_warmup_when_no_top_set_exists(self):
        today = timezone.localdate().isoformat()
        html = _render(build_example_payload(), load_history=[
            {'movement_slug': 'agachamento-livre', 'weight_kg': 60.0, 'reps': 10, 'rir': None,
             'performed_on': today, 'program_id': '', 'week_in_program': None,
             'idempotency_key': 'warmup-only', 'set_role': 'warmup'},
        ])

        widget_start = html.index('data-workout-load-input')
        widget = html[widget_start:html.index('data-workout-load-status', widget_start)]
        self.assertIn('data-today-idempotency-key="warmup-only"', widget)
        self.assertIn('data-today-warmup-idempotency-key="warmup-only"', widget)
        self.assertIn('data-workout-load-warmup-toggle checked', widget)
        self.assertIn('value="60.0"', widget)

    def test_records_section_exists_inside_cargas_panel(self):
        # "Suas Cargas" (recorde por movimento) mora dentro do painel de
        # nivel superior "Cargas" (bottom nav) desde a reestruturacao de
        # 5 telas — nao e mais uma aba propria dentro do dia.
        html = _render(build_example_payload())

        self.assertIn('id="workout-panel-cargas"', html)
        self.assertIn('Seus recordes', html)

    def test_records_tab_shows_empty_state_without_load_history(self):
        html = _render(build_example_payload(), load_history=[])

        self.assertIn('Nenhuma carga registrada ainda.', html)

    def test_records_tab_shows_personal_record_card(self):
        html = _render(
            build_example_payload(),
            load_history=[
                {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-05', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1', 'set_role': 'top_set'},
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 6, 'rir': 2.0, 'performed_on': '2026-02-01', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k2', 'set_role': 'top_set'},
            ],
        )

        self.assertIn('workout-record-card', html)
        # o maior peso ja registrado (100.0), nao o mais recente (90.0 foi
        # registrado antes, 100.0 depois — personal_record ignora ordem
        # cronologica e pega so o maior valor).
        self.assertIn('<strong class="workout-record-card__value">100,0', html)
        # personal_record ja devolve `reps` do mesmo log de maior peso
        # (6, nao 8 -- o log de 100kg, nao o de 90kg) — achado real: o
        # template ignorava esse valor mesmo com o dado pronto no dict.
        self.assertIn('workout-record-card__reps">6 reps', html)
        self.assertIn('Maior carga em 01/02/2026', html)

    def test_records_tab_omits_reps_when_none(self):
        # Registro anterior a esta fase (ou movimento sem reps
        # quantificavel) tem reps=None -- o card nao pode renderizar
        # "None reps", so omitir o span inteiro.
        html = _render(
            build_example_payload(),
            load_history=[
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': None, 'rir': None, 'performed_on': '2026-01-05', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1', 'set_role': 'top_set'},
            ],
        )

        self.assertIn('workout-record-card', html)
        self.assertNotIn('None reps', html)
        self.assertNotIn('workout-record-card__reps', html)

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

        self.assertEqual(html.count('class="workout-movement-register" data-workout-load-toggle'), 2)
        self.assertEqual(html.count('class="workout-load-input" data-workout-load-input'), 2)
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
        second_day = timezone.localdate() - timedelta(days=10)
        first_day = second_day - timedelta(days=20)
        html = _render(build_example_payload(), load_history=[
            {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': first_day.isoformat(), 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1', 'set_role': 'top_set'},
            {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': 2.0, 'performed_on': second_day.isoformat(), 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k2', 'set_role': 'top_set'},
        ])

        self.assertIn('Agachamento livre', html)
        self.assertIn('workout-load-chart-line', html)
        self.assertIn('workout-load-chart-trend--up', html)
        self.assertIn('Ver registros recentes', html)
        self.assertIn('RIR 2', html)
        self.assertIn('8 reps', html)
        # Texto visivel usa separador decimal pt-BR (USE_L10N, mesma
        # convencao de "75,0% RM" ja testada acima); coordenadas do SVG
        # abaixo tem que ficar de FORA disso (SVG so aceita ponto).
        self.assertIn('100,0 kg', html)
        expected_first_x = round(46 + (600 - 10 - 46) * 60 / 90, 2)
        expected_last_x = round(46 + (600 - 10 - 46) * 80 / 90, 2)
        self.assertIn(f'cx="{expected_first_x}" cy="90.0"', html)
        self.assertIn(f'cx="{expected_last_x}" cy="10.0"', html)
        self.assertIn('text-anchor="middle"', html)
        self.assertNotIn('Ainda não há carga suficiente', html)

    def test_history_tab_shows_fallback_with_fewer_than_two_points(self):
        recent_day = timezone.localdate().isoformat()
        html = _render(build_example_payload(), load_history=[
            {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': recent_day, 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1', 'set_role': 'top_set'},
        ])

        self.assertIn('Você já tem uma série principal recente.', html)
        self.assertIn('Ver registros recentes', html)
        self.assertNotIn('workout-load-chart-line', html)

    def test_legacy_only_history_shows_last_value_without_an_empty_chart(self):
        from public_workouts.progress_snapshot import ProgressPoint

        legacy_day = timezone.localdate() - timedelta(days=25)
        legacy = ProgressPoint(
            performed_on=legacy_day, weight_kg=Decimal('72.5'), reps=None, rir=None,
            created_at=datetime.combine(legacy_day, datetime.min.time()), program_id='',
        )
        html = _render(
            build_example_payload(),
            load_history=[{
                'movement_slug': 'agachamento-livre', 'weight_kg': 72.5, 'reps': None, 'rir': None,
                'performed_on': legacy_day.isoformat(), 'program_id': '', 'week_in_program': None,
                'idempotency_key': 'legacy-only', 'set_role': 'legacy_unknown',
            }],
            progress_snapshots={
                'agachamento-livre': SimpleNamespace(
                    latest_top_set=None, curve_points=[], legacy_points=[legacy], has_legacy_history=True,
                    y_scale=None, trend_signal='insufficient_data', one_rep_max=None,
                ),
            },
        )

        self.assertIn('Último registro anterior', html)
        self.assertIn('72,5 <span>kg</span>', html)
        self.assertIn(legacy_day.strftime('%d/%m/%Y'), html)
        self.assertIn('não entra na curva comparável', html)
        self.assertNotIn('workout-load-chart-svg', html)

    def test_history_tab_keeps_latest_load_visible_when_outside_chart_window(self):
        from public_workouts.progress_snapshot import ProgressPoint

        latest_day = timezone.localdate() - timedelta(days=120)
        latest = ProgressPoint(
            performed_on=latest_day, weight_kg=Decimal('82.5'), reps=6, rir=Decimal('2'),
            created_at=datetime.combine(latest_day, datetime.min.time()), program_id='bruno-2026-q1',
        )
        html = _render(
            build_example_payload(),
            load_history=[{
                'movement_slug': 'agachamento-livre', 'weight_kg': 82.5, 'reps': 6, 'rir': 2.0,
                'performed_on': latest_day.isoformat(), 'program_id': 'bruno-2026-q1',
                'week_in_program': None, 'idempotency_key': 'stale-top-set', 'set_role': 'top_set',
            }],
            progress_snapshots={
                'agachamento-livre': SimpleNamespace(
                    latest_top_set=latest, curve_points=[], legacy_points=[], has_legacy_history=False,
                    y_scale=None, trend_signal='insufficient_data', one_rep_max=None,
                ),
            },
        )

        self.assertIn('82,5 kg', html)
        self.assertIn('há mais de 90 dias', html)
        self.assertIn(latest_day.strftime('%d/%m/%Y'), html)
        self.assertNotIn('workout-load-chart-line', html)

    def test_warmup_only_history_explains_why_it_does_not_start_the_curve(self):
        html = _render(build_example_payload(), load_history=[
            {'movement_slug': 'agachamento-livre', 'weight_kg': 60.0, 'reps': 8, 'rir': None,
             'performed_on': timezone.localdate().isoformat(), 'program_id': '', 'week_in_program': None,
             'idempotency_key': 'warmup-only', 'set_role': 'warmup'},
        ])

        self.assertIn('Séries de aquecimento não entram na evolução.', html)
        self.assertIn('Seu histórico está salvo. Séries de aquecimento e registros anteriores não contam como recorde.', html)
        self.assertIn('Registre uma série principal atual para começar seu resumo do ciclo.', html)
        self.assertNotIn('data-workout-record-card', html)
        self.assertNotIn('workout-load-chart-line', html)

    def test_history_tab_shows_sibling_variation_as_labeled_reference(self):
        # "Variação irmã" (Pronto quando #3, secao A3/B4 do CORDA): outro
        # movimento ATIVO do MESMO movement_pattern aparece como referencia
        # rotulada ao lado do grafico -- nunca precisa de carga propria
        # registrada, e' so' informativo (suggest_substitutes ja garante
        # que nunca entra no calculo de 1RM/tendencia deste movimento).
        PublicWorkoutMovement.objects.create(
            slug='agachamento-livre', label_pt='Agachamento livre', movement_pattern='squat',
            status=PublicWorkoutMovementStatus.ACTIVE, reference_url='https://musclewiki.com/exercise/barbell-squat',
        )
        PublicWorkoutMovement.objects.create(
            slug='machine-hack-squat', label_pt='Hack squat na máquina', movement_pattern='squat',
            status=PublicWorkoutMovementStatus.ACTIVE, reference_url='https://musclewiki.com/exercise/machine-hack-squat',
        )

        html = _render(build_example_payload(), load_history=[
            {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-05', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1', 'set_role': 'top_set'},
        ])

        self.assertIn('workout-load-chart-siblings', html)
        self.assertIn('Variação:', html)
        self.assertIn('Hack squat na máquina', html)
        self.assertIn('href="https://musclewiki.com/exercise/machine-hack-squat"', html)

    def test_history_tab_hides_sibling_note_when_movement_unclassified(self):
        # Sem PublicWorkoutMovement classificado (catalogo nao tem o slug,
        # ou nao tem movement_pattern) -- nao aparece nada, nunca quebra.
        html = _render(build_example_payload(), load_history=[
            {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-05', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1', 'set_role': 'top_set'},
        ])

        self.assertNotIn('workout-load-chart-siblings', html)

    def test_history_tab_shows_one_rep_max_estimate_when_provided(self):
        html = _render(
            build_example_payload(),
            load_history=[
                {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-05', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1', 'set_role': 'top_set'},
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-12', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k2', 'set_role': 'top_set'},
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
                {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-05', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1', 'set_role': 'top_set'},
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-12', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k2', 'set_role': 'top_set'},
            ],
            one_rep_max_by_movement={'outro-movimento': {'value_kg': 50.0, 'formula': 'epley', 'confidence': 'low', 'effective_reps': 14}},
        )

        self.assertNotIn('workout-load-chart-1rm', html)

    def test_history_tab_shows_declining_signal_badge(self):
        html = _render(
            build_example_payload(),
            load_history=[
                {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-05', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1', 'set_role': 'top_set'},
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-12', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k2', 'set_role': 'top_set'},
            ],
            trends_by_movement={'agachamento-livre': {'label': 'declining', 'weekly_estimates_kg': [130.0, 125.0, 118.0]}},
        )

        self.assertIn('workout-load-chart-signal--declining', html)
        self.assertIn('Em queda', html)

    def test_history_tab_shows_plateau_signal_badge(self):
        html = _render(
            build_example_payload(),
            load_history=[
                {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-05', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1', 'set_role': 'top_set'},
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-12', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k2', 'set_role': 'top_set'},
            ],
            trends_by_movement={'agachamento-livre': {'label': 'plateau', 'weekly_estimates_kg': [128.0, 129.0, 127.5]}},
        )

        self.assertIn('workout-load-chart-signal--plateau', html)
        self.assertIn('Platô', html)

    def test_history_tab_shows_improving_signal_badge(self):
        html = _render(
            build_example_payload(),
            load_history=[
                {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-05', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1', 'set_role': 'top_set'},
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-12', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k2', 'set_role': 'top_set'},
            ],
            trends_by_movement={'agachamento-livre': {'label': 'improving', 'weekly_estimates_kg': [118.0, 124.0, 130.0]}},
        )

        self.assertIn('workout-load-chart-signal--improving', html)
        self.assertIn('Em evolução', html)

    def test_history_tab_marks_program_version_change_on_chart(self):
        html = _render(
            build_example_payload(),
            load_history=[
                {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-05', 'program_id': 'bruno-2026-q1', 'week_in_program': 4, 'idempotency_key': 'k1', 'set_role': 'top_set'},
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-04-01', 'program_id': 'bruno-2026-q2', 'week_in_program': 1, 'idempotency_key': 'k2', 'set_role': 'top_set'},
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
                {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-05', 'program_id': 'bruno-2026-q1', 'week_in_program': 1, 'idempotency_key': 'k1', 'set_role': 'top_set'},
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-12', 'program_id': 'bruno-2026-q1', 'week_in_program': 2, 'idempotency_key': 'k2', 'set_role': 'top_set'},
            ],
        )

        self.assertNotIn('workout-load-chart-version-line', html)
        self.assertNotIn('workout-load-chart-dot--version', html)

    def test_cycle_summary_renders_a_row_per_movement_with_data(self):
        html = _render(
            build_example_payload(),
            load_history=[
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-12', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1', 'set_role': 'top_set'},
            ],
            trends_by_movement={'agachamento-livre': {'label': 'improving', 'weekly_estimates_kg': [90.0, 95.0, 100.0]}},
        )

        self.assertIn('Resumo do ciclo', html)
        self.assertIn('Agachamento livre', html)
        self.assertIn('Em evolução', html)
        self.assertNotIn('Registre suas cargas pra ver o resumo deste ciclo.', html)

    def test_cycle_summary_shows_empty_state_without_any_active_top_set(self):
        html = _render(build_example_payload(), load_history=[])

        self.assertIn('Registre suas cargas pra ver o resumo deste ciclo.', html)

    def test_share_button_renders_with_server_computed_content(self):
        html = _render(build_example_payload(), load_history=[
            {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-12', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1', 'set_role': 'top_set'},
        ])

        self.assertIn('data-workout-share', html)
        self.assertIn('data-share-title="Minha evolução em Agachamento livre"', html)
        self.assertIn('data-share-text="💪 Agachamento livre: 100 kg"', html)

    def test_share_button_is_absent_without_any_weight_to_share(self):
        html = _render(build_example_payload(), load_history=[
            {'movement_slug': 'prancha', 'weight_kg': None, 'reps': 40, 'performed_on': '2026-01-12', 'idempotency_key': 'k1', 'set_role': 'top_set'},
        ])

        self.assertNotIn('data-workout-share', html)

    def test_share_button_survives_a_movement_with_a_one_rep_max_estimate(self):
        # Regressao real pega nesta rodada: one_rep_max_by_movement chega
        # como DICT puro no fixture de teste do template (nunca
        # OneRepMaxEstimate) -- sem o isinstance() guard em
        # share_content_for_chart, isto levantava AttributeError e
        # quebrava a renderizacao inteira da pagina pra qualquer aluno
        # com 1RM estimado.
        html = _render(
            build_example_payload(),
            load_history=[
                {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-05', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1', 'set_role': 'top_set'},
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100.0, 'reps': 8, 'rir': 2.0, 'performed_on': '2026-01-12', 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k2', 'set_role': 'top_set'},
            ],
            one_rep_max_by_movement={
                'agachamento-livre': {'value_kg': 128.6, 'formula': 'brzycki', 'confidence': 'high', 'effective_reps': 10},
            },
        )

        self.assertIn('1RM estimado 128,6 kg', html)


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
        # segunda-feira da semana local corrente (mesma data local do seletor
        # de treino, inclusive perto da virada do dia no servidor).
        today = timezone.localdate()
        monday = today - datetime.timedelta(days=today.weekday())
        html = _render(payload, load_history=[
            {'movement_slug': 'agachamento-livre', 'weight_kg': 90.0, 'reps': 8, 'rir': 2.0, 'performed_on': monday.isoformat(), 'program_id': '', 'week_in_program': None, 'idempotency_key': 'k1', 'set_role': 'top_set'},
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
        self.assertIn('css/public_workouts/workout-assessment.css', html)
        self.assertIn('class="workout-assessment-panel"', html)


class WorkoutModuleAssetTests(TestCase):
    def test_training_progress_and_shell_assets_are_separate(self):
        html = _render(build_example_payload())

        self.assertIn('css/public_workouts/workout-training.css', html)
        self.assertIn('css/public_workouts/workout-progress.css', html)
        self.assertIn('js/public_workouts/workout-shell.js', html)
        self.assertNotIn('data-workout-load-toggle tabindex="0" role="button"', html)


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


class SiblingVariationsFilterTests(TestCase):
    """"Variação irmã" (Onda A3/B4, item 3 do "Pronto quando" do CORDA) --
    reusa suggest_substitutes tal e qual, só prova a fiação do filtro."""

    def test_movement_with_active_sibling_returns_it(self):
        PublicWorkoutMovement.objects.create(
            slug='barbell-squat', label_pt='Agachamento livre com barra', movement_pattern='squat',
            status=PublicWorkoutMovementStatus.ACTIVE, reference_url='https://musclewiki.com/exercise/barbell-squat',
        )
        PublicWorkoutMovement.objects.create(
            slug='machine-hack-squat', label_pt='Hack squat na máquina', movement_pattern='squat',
            status=PublicWorkoutMovementStatus.ACTIVE, reference_url='https://musclewiki.com/exercise/machine-hack-squat',
        )

        result = sibling_variations('barbell-squat')

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['label_pt'], 'Hack squat na máquina')

    def test_unclassified_movement_returns_empty(self):
        self.assertEqual(sibling_variations('nao-existe-no-catalogo'), [])


class MovementShowsPlateCalculatorFilterTests(TestCase):
    # Plano curva-carga-completa-reps-rir-recorde, Fase 3 (§5.1) -- os
    # DOIS metadados curados precisam bater; nenhum sozinho basta.

    def test_barbell_with_convention_confirmed_shows_calculator(self):
        PublicWorkoutMovement.objects.create(
            slug='agachamento-livre', label_pt='Agachamento livre',
            equipment_type=PublicWorkoutMovementEquipment.BARBELL, logged_weight_includes_bar=True,
        )

        self.assertTrue(movement_shows_plate_calculator('agachamento-livre'))

    def test_barbell_without_convention_confirmed_hides_calculator(self):
        # equipment_type=barbell sozinho nao basta -- o treinador pode
        # registrar so' o peso das anilhas, sem a barra.
        PublicWorkoutMovement.objects.create(
            slug='agachamento-livre', label_pt='Agachamento livre',
            equipment_type=PublicWorkoutMovementEquipment.BARBELL, logged_weight_includes_bar=False,
        )

        self.assertFalse(movement_shows_plate_calculator('agachamento-livre'))

    def test_non_barbell_hides_calculator_even_with_convention_flag(self):
        PublicWorkoutMovement.objects.create(
            slug='desenvolvimento-halteres', label_pt='Desenvolvimento com halteres',
            equipment_type=PublicWorkoutMovementEquipment.DUMBBELL, logged_weight_includes_bar=True,
        )

        self.assertFalse(movement_shows_plate_calculator('desenvolvimento-halteres'))

    def test_unclassified_movement_returns_false(self):
        self.assertFalse(movement_shows_plate_calculator('nao-existe-no-catalogo'))


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
    # set_role='top_set' em toda entry de proposito (plano
    # curva-grafico-hierarquia-e-set-role.md, §2.1/§2.2): load_chart_points
    # so' conecta series ELEGIVEIS na curva agora -- uma entry sem
    # set_role (ou com warmup/legacy_unknown) e' filtrada fora antes de
    # chegar no `len(weighted) < 2`, entao os testes deste arquivo (que
    # nao sao sobre elegibilidade, e sim sobre geometria/trend/label)
    # precisam do papel elegivel pra nao virar has_data=False por engano.

    def test_no_entries_has_no_data(self):
        result = load_chart_points([])

        self.assertFalse(result['has_data'])
        self.assertEqual(result['points'], [])
        self.assertEqual(result['points_attr'], '')

    def test_single_point_has_no_data(self):
        # Mesma supressao de assessments.js::buildWeightChart — 1 ponto so
        # nao mostra tendencia nenhuma.
        entries = [{'weight_kg': 100.0, 'performed_on': '2026-01-05', 'set_role': 'top_set'}]

        result = load_chart_points(entries)

        self.assertFalse(result['has_data'])

    def test_entries_with_weight_kg_none_are_ignored(self):
        # Movimento so de peso corporal (weight_kg=None) nunca deveria
        # contar como ponto de grafico de carga.
        entries = [
            {'weight_kg': None, 'performed_on': '2026-01-01', 'set_role': 'top_set'},
            {'weight_kg': None, 'performed_on': '2026-01-02', 'set_role': 'top_set'},
        ]

        result = load_chart_points(entries)

        self.assertFalse(result['has_data'])

    def test_non_eligible_role_is_ignored_even_with_weight(self):
        # Achado real do plano: sem este filtro, aquecimento contaminava a
        # mesma linha da serie principal.
        entries = [
            {'weight_kg': 90.0, 'performed_on': '2026-01-05', 'set_role': 'top_set'},
            {'weight_kg': 100.0, 'performed_on': '2026-01-12', 'set_role': 'warmup'},
        ]

        result = load_chart_points(entries)

        self.assertFalse(result['has_data'])  # so' 1 top_set -> abaixo do minimo de 2

    def test_two_points_normalizes_between_pad_and_width_minus_pad(self):
        entries = [
            {'weight_kg': 90.0, 'performed_on': '2026-01-05', 'set_role': 'top_set'},
            {'weight_kg': 100.0, 'performed_on': '2026-01-12', 'set_role': 'top_set'},
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
            {'weight_kg': 100.0, 'performed_on': '2026-01-05', 'set_role': 'top_set'},
            {'weight_kg': 100.0, 'performed_on': '2026-01-12', 'set_role': 'top_set'},
        ]

        result = load_chart_points(entries)

        self.assertTrue(result['has_data'])
        self.assertEqual(result['points'][0]['y'], result['points'][1]['y'])

    def test_labels_are_short_dates(self):
        entries = [
            {'weight_kg': 90.0, 'performed_on': '2026-01-05', 'set_role': 'top_set'},
            {'weight_kg': 100.0, 'performed_on': '2026-01-12', 'set_role': 'top_set'},
        ]

        result = load_chart_points(entries)

        self.assertEqual(result['points'][0]['label'], '05/01')
        self.assertEqual(result['points'][1]['label'], '12/01')

    def test_first_point_never_marks_program_change(self):
        # Nao ha "antes" pra contrastar no primeiro ponto da serie, mesmo
        # com program_id preenchido.
        entries = [
            {'weight_kg': 90.0, 'performed_on': '2026-01-05', 'program_id': 'bruno-2026-q1', 'set_role': 'top_set'},
            {'weight_kg': 100.0, 'performed_on': '2026-01-12', 'program_id': 'bruno-2026-q1', 'set_role': 'top_set'},
        ]

        result = load_chart_points(entries)

        self.assertFalse(result['points'][0]['is_program_change'])
        self.assertFalse(result['points'][1]['is_program_change'])

    def test_marks_program_change_when_program_id_differs_from_previous_point(self):
        entries = [
            {'weight_kg': 90.0, 'performed_on': '2026-01-05', 'program_id': 'bruno-2026-q1', 'week_in_program': 4, 'set_role': 'top_set'},
            {'weight_kg': 100.0, 'performed_on': '2026-04-01', 'program_id': 'bruno-2026-q2', 'week_in_program': 1, 'set_role': 'top_set'},
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
            {'weight_kg': 90.0, 'performed_on': '2026-01-05', 'program_id': 'bruno-2026-q1', 'set_role': 'top_set'},
            {'weight_kg': 95.0, 'performed_on': '2026-01-08', 'program_id': '', 'set_role': 'top_set'},
            {'weight_kg': 100.0, 'performed_on': '2026-01-12', 'program_id': '', 'set_role': 'top_set'},
        ]

        result = load_chart_points(entries)

        self.assertFalse(any(point['is_program_change'] for point in result['points']))

    def test_program_id_reappears_after_gap_still_compares_to_last_known(self):
        # Um ponto no meio sem program_id nao apaga o contexto: a troca
        # ainda e' detectada contra o ultimo program_id conhecido.
        entries = [
            {'weight_kg': 90.0, 'performed_on': '2026-01-05', 'program_id': 'bruno-2026-q1', 'set_role': 'top_set'},
            {'weight_kg': 95.0, 'performed_on': '2026-01-08', 'program_id': '', 'set_role': 'top_set'},
            {'weight_kg': 100.0, 'performed_on': '2026-04-01', 'program_id': 'bruno-2026-q2', 'set_role': 'top_set'},
        ]

        result = load_chart_points(entries)

        self.assertFalse(result['points'][0]['is_program_change'])
        self.assertFalse(result['points'][1]['is_program_change'])
        self.assertTrue(result['points'][2]['is_program_change'])

    def test_missing_program_id_key_defaults_to_empty_and_never_marks(self):
        # list_load_history sempre inclui program_id, mas o filtro nao deve
        # quebrar se um chamador futuro omitir a chave.
        entries = [
            {'weight_kg': 90.0, 'performed_on': '2026-01-05', 'set_role': 'top_set'},
            {'weight_kg': 100.0, 'performed_on': '2026-01-12', 'set_role': 'top_set'},
        ]

        result = load_chart_points(entries)

        self.assertFalse(result['points'][1]['is_program_change'])
        self.assertEqual(result['points'][0]['program_id'], '')

    def test_upward_trend_reports_positive_delta(self):
        entries = [
            {'weight_kg': 90.0, 'performed_on': '2026-01-05', 'set_role': 'top_set'},
            {'weight_kg': 100.0, 'performed_on': '2026-01-12', 'set_role': 'top_set'},
        ]

        result = load_chart_points(entries)

        self.assertEqual(result['trend'], 'up')
        self.assertEqual(result['delta_weight_kg'], 10.0)
        self.assertEqual(result['latest_weight_kg'], 100.0)

    def test_downward_trend_reports_negative_delta(self):
        entries = [
            {'weight_kg': 100.0, 'performed_on': '2026-01-05', 'set_role': 'top_set'},
            {'weight_kg': 90.0, 'performed_on': '2026-01-12', 'set_role': 'top_set'},
        ]

        result = load_chart_points(entries)

        self.assertEqual(result['trend'], 'down')
        self.assertEqual(result['delta_weight_kg'], -10.0)

    def test_flat_trend_reports_zero_delta(self):
        entries = [
            {'weight_kg': 100.0, 'performed_on': '2026-01-05', 'set_role': 'top_set'},
            {'weight_kg': 100.0, 'performed_on': '2026-01-12', 'set_role': 'top_set'},
        ]

        result = load_chart_points(entries)

        self.assertEqual(result['trend'], 'flat')
        self.assertEqual(result['delta_weight_kg'], 0.0)

    def test_area_points_closes_polygon_at_baseline(self):
        entries = [
            {'weight_kg': 90.0, 'performed_on': '2026-01-05', 'set_role': 'top_set'},
            {'weight_kg': 100.0, 'performed_on': '2026-01-12', 'set_role': 'top_set'},
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


class PersonalRecordFilterTests(TestCase):
    def test_empty_list_has_no_data(self):
        result = personal_record([])

        self.assertFalse(result['has_data'])
        self.assertIsNone(result['weight_kg'])

    def test_entries_with_weight_kg_none_are_ignored(self):
        result = personal_record([{'weight_kg': None, 'performed_on': '2026-01-01', 'reps': None, 'set_role': 'top_set'}])

        self.assertFalse(result['has_data'])

    def test_picks_highest_weight_regardless_of_date_order(self):
        result = personal_record([
            {'weight_kg': 90.0, 'performed_on': '2026-02-01', 'reps': 8, 'set_role': 'top_set'},  # mais recente, mas nao o maior
            {'weight_kg': 100.0, 'performed_on': '2026-01-05', 'reps': 6, 'set_role': 'top_set'},
        ])

        self.assertTrue(result['has_data'])
        self.assertEqual(result['weight_kg'], 100.0)
        self.assertEqual(result['performed_on'], '2026-01-05')
        self.assertEqual(result['reps'], 6)


    def test_warmup_and_legacy_never_become_personal_records(self):
        result = personal_record([
            {'weight_kg': 150.0, 'performed_on': '2026-01-01', 'set_role': 'warmup'},
            {'weight_kg': 130.0, 'performed_on': '2026-01-02', 'set_role': 'legacy_unknown'},
            {'weight_kg': 120.0, 'performed_on': '2026-01-03', 'set_role': 'top_set'},
            {'weight_kg': 125.0, 'performed_on': '2026-01-04', 'set_role': 'max_set'},
        ])
        self.assertTrue(result['has_data'])
        self.assertEqual(result['weight_kg'], 125.0)
        self.assertEqual(result['performed_on'], '2026-01-04')

    def test_single_entry_already_has_data(self):
        # Diferente de load_chart_points (que exige 2+ pontos pra mostrar
        # tendencia), um recorde so precisa de 1 registro.
        result = personal_record([{'weight_kg': 60.0, 'performed_on': '2026-01-01', 'reps': 10, 'set_role': 'top_set'}])

        self.assertTrue(result['has_data'])
        self.assertEqual(result['weight_kg'], 60.0)

    def test_warmup_never_becomes_the_record(self):
        # Achado real do plano curva-grafico-hierarquia-e-set-role.md
        # (§7.5/§8.1 item 4): max(weighted, key=peso) sem filtro deixava
        # uma serie de aquecimento pesada virar "recorde" por engano.
        result = personal_record([
            {'weight_kg': 150.0, 'performed_on': '2026-01-01', 'reps': 5, 'set_role': 'warmup'},
            {'weight_kg': 100.0, 'performed_on': '2026-01-01', 'reps': 5, 'set_role': 'top_set'},
        ])

        self.assertTrue(result['has_data'])
        self.assertEqual(result['weight_kg'], 100.0)

    def test_legacy_unknown_never_becomes_the_record(self):
        result = personal_record([{'weight_kg': 200.0, 'performed_on': '2026-01-01', 'reps': 5, 'set_role': 'legacy_unknown'}])

        self.assertFalse(result['has_data'])

    def test_max_set_is_eligible_for_the_record(self):
        result = personal_record([{'weight_kg': 100.0, 'performed_on': '2026-01-01', 'reps': 1, 'set_role': 'max_set'}])

        self.assertTrue(result['has_data'])


class CycleSummaryRowsTagTests(TestCase):
    # "Visão consolidada do ciclo" -- 1ª das 3 frentes seguintes citadas em
    # curva-grafico-hierarquia-e-set-role.md §0 (junto de celebração de PR,
    # já entregue, e card compartilhável, abaixo).

    def test_no_snapshots_returns_empty_list(self):
        self.assertEqual(cycle_summary_rows({}, {}), [])

    def test_movement_without_a_latest_top_set_is_skipped(self):
        # Sem nenhum top_set ativo (nunca registrado, ou so' aquecimento/
        # legado) -- uma linha vazia no resumo nao ajuda ninguem.
        snapshots = {
            'prancha': SimpleNamespace(latest_top_set=None, trend_signal='insufficient_data', one_rep_max=None),
        }

        self.assertEqual(cycle_summary_rows(snapshots, {}), [])

    def test_builds_one_row_per_movement_sorted_by_label(self):
        point_squat = SimpleNamespace(weight_kg=Decimal('100'), reps=8, performed_on=date(2026, 1, 12))
        point_bench = SimpleNamespace(weight_kg=Decimal('60'), reps=10, performed_on=date(2026, 1, 12))
        snapshots = {
            'supino-reto': SimpleNamespace(latest_top_set=point_bench, trend_signal='plateau', one_rep_max=None),
            'agachamento-livre': SimpleNamespace(latest_top_set=point_squat, trend_signal='improving', one_rep_max=None),
        }

        rows = cycle_summary_rows(snapshots, {})

        self.assertEqual([row['movement_slug'] for row in rows], ['agachamento-livre', 'supino-reto'])
        self.assertEqual(rows[0]['weight_kg'], Decimal('100'))
        self.assertEqual(rows[0]['reps'], 8)
        self.assertEqual(rows[0]['trend_signal'], 'improving')

    def test_uses_movement_labels_when_available(self):
        point = SimpleNamespace(weight_kg=Decimal('100'), reps=8, performed_on=date(2026, 1, 12))
        snapshots = {'agachamento-livre': SimpleNamespace(latest_top_set=point, trend_signal='improving', one_rep_max=None)}

        rows = cycle_summary_rows(snapshots, {'agachamento-livre': 'Back Squat'})

        self.assertEqual(rows[0]['label'], 'Back Squat')

    def test_never_recomputes_never_queries_the_database(self):
        # NUNCA reconsulta o banco -- cada linha vem so' do snapshot ja
        # calculado em lote (build_progress_snapshots), nunca de uma
        # query nova por movimento.
        point = SimpleNamespace(weight_kg=Decimal('100'), reps=8, performed_on=date(2026, 1, 12))
        snapshots = {'agachamento-livre': SimpleNamespace(latest_top_set=point, trend_signal='declining', one_rep_max=None)}

        with self.assertNumQueries(0):
            cycle_summary_rows(snapshots, {})


class ShareContentForChartTagTests(TestCase):
    # Card compartilhável -- fundação decidida com o Renan em 24/09/2026:
    # so' texto pro Web Share API por agora (ver docstring da tag).

    def test_without_weight_returns_empty_content(self):
        result = share_content_for_chart({'latest_weight_kg': None}, 'Agachamento livre')

        self.assertEqual(result, {'title': '', 'text': ''})

    def test_weight_only(self):
        result = share_content_for_chart(
            {
                'latest_weight_kg': Decimal('100.00'), 'trend_signal': 'insufficient_data',
                'delta_weight_kg': None, 'one_rep_max': None,
            },
            'Agachamento livre',
        )

        self.assertEqual(result['title'], 'Minha evolução em Agachamento livre')
        self.assertEqual(result['text'], '💪 Agachamento livre: 100 kg')

    def test_improving_trend_and_positive_delta_are_both_mentioned(self):
        result = share_content_for_chart(
            {
                'latest_weight_kg': Decimal('102.5'), 'trend_signal': 'improving',
                'delta_weight_kg': 2.5, 'one_rep_max': None,
            },
            'Agachamento livre',
        )

        self.assertEqual(result['text'], '💪 Agachamento livre: 102,5 kg · em evolução · +2,5 kg no período')

    def test_negative_delta_is_never_mentioned(self):
        # Card compartilhavel e' superficie de celebracao (mesmo espirito
        # da Fase 4) -- uma queda no periodo nunca aparece como numero
        # negativo, so' o trend_signal (de forma neutra) se houver.
        result = share_content_for_chart(
            {
                'latest_weight_kg': Decimal('90'), 'trend_signal': 'declining',
                'delta_weight_kg': -10.0, 'one_rep_max': None,
            },
            'Agachamento livre',
        )

        self.assertNotIn('-10', result['text'])
        self.assertNotIn('kg no período', result['text'])
        self.assertIn('recuperando de um platô', result['text'])

    def test_includes_one_rep_max_when_present_as_a_dataclass(self):
        # Formato de PRODUCAO: OneRepMaxEstimate (progress_snapshot.py),
        # acessado por ATRIBUTO.
        estimate = SimpleNamespace(value_kg=128.6, formula='brzycki', confidence='high', effective_reps=5)
        result = share_content_for_chart(
            {
                'latest_weight_kg': Decimal('100'), 'trend_signal': 'insufficient_data',
                'delta_weight_kg': None, 'one_rep_max': estimate,
            },
            'Agachamento livre',
        )

        self.assertIn('1RM estimado 128,6 kg', result['text'])

    def test_includes_one_rep_max_when_present_as_a_plain_dict(self):
        # Formato de FIXTURE DE TESTE DE TEMPLATE (test_workout_template.py
        # ::_render, one_rep_max_by_movement) -- acessado por CHAVE, nunca
        # por atributo. Sem o isinstance() guard em share_content_for_chart,
        # isto levantava AttributeError (bug real pego nesta mesma rodada:
        # test_history_tab_shows_one_rep_max_estimate_when_provided combina
        # load_history+one_rep_max_by_movement e quebraria a suite inteira).
        estimate = {'value_kg': 128.6, 'formula': 'brzycki', 'confidence': 'high', 'effective_reps': 5}
        result = share_content_for_chart(
            {
                'latest_weight_kg': Decimal('100'), 'trend_signal': 'insufficient_data',
                'delta_weight_kg': None, 'one_rep_max': estimate,
            },
            'Agachamento livre',
        )

        self.assertIn('1RM estimado 128,6 kg', result['text'])


class ResolveMovementDisplayNameFilterTests(TestCase):
    def test_uses_label_when_present_in_lookup(self):
        result = resolve_movement_display_name('barbell-bench-press', {'barbell-bench-press': 'Supino reto com barra'})

        self.assertEqual(result, 'Supino reto com barra')

    def test_falls_back_to_humanized_slug_when_missing(self):
        result = resolve_movement_display_name('barbell-bench-press', {})

        self.assertEqual(result, 'Barbell bench press')

    def test_falls_back_when_lookup_is_none(self):
        result = resolve_movement_display_name('agachamento-livre', None)

        self.assertEqual(result, 'Agachamento livre')

    def test_does_not_mangle_label_with_internal_capitals(self):
        # Regressao: encadear |default:slug|humanize_movement_slug no
        # template faria .capitalize() derrubar maiusculas internas tipo
        # "Wall Ball" -> "Wall ball". O filtro proprio nunca faz isso.
        result = resolve_movement_display_name('wall-ball', {'wall-ball': 'Wall Ball'})

        self.assertEqual(result, 'Wall Ball')


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

    def test_max_set_gets_its_own_glossary_bubble(self):
        # Achado real do Renan clicando no chip "1x Max": faltava 'max' em
        # _GLOSSARY_TERMS -- Prep/Feeder/Top tinham balao, Max nao.
        html = glossary_highlight('1x Max')

        self.assertIn('data-workout-glossary', html)
        self.assertIn('>Max<', html)
        self.assertIn('Max Set', html)

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
        self.assertIn('aria-controls="workout-variation-seg-1-1"', html)
        self.assertIn('id="workout-variation-seg-1-1"', html)
        self.assertIn('class="workout-movement-variation" data-workout-variation hidden>', html)

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
        # Plano curva-grafico-hierarquia-e-set-role.md (§7.5/§8.1 item 5):
        # o "ultimo log" agora vem de progress_snapshots[slug].latest_top_set
        # (ja' elegivel -- nunca mais escaneia load_history bruto).
        from datetime import date, datetime
        from decimal import Decimal

        from public_workouts.progress_snapshot import ProgressPoint, ProgressSnapshot

        movement = self._movement()
        payload = {
            'program_id': 'juliana-2026-q1', 'started_on': '2026-01-05',
            'periodization': _canonical_periodization(_SIX_CANONICAL_WEEKS),
        }
        latest_top_set = ProgressPoint(
            performed_on=date(2026, 1, 5), weight_kg=Decimal('80.0'), reps=None, rir=None,
            created_at=datetime(2026, 1, 5, 12, 0), program_id='juliana-2026-q1',
        )
        progress_snapshots = {
            'hack-squat': ProgressSnapshot(
                latest_top_set=latest_top_set, curve_points=[], legacy_points=[],
                has_legacy_history=False, y_scale=None, trend_signal='insufficient_data', one_rep_max=None,
            ),
        }

        result = movement_load_display(movement, payload, PHASE_PROFILES['volume'], {}, progress_snapshots)

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


class TodaysLoggedWeightTagTests(TestCase):
    # Achado real (usuario/Juliana): o campo de carga sempre renderizava
    # vazio, mesmo apos salvar com sucesso -- sem confirmacao visivel ao
    # recarregar, ela achava que nao tinha salvo e registrava de novo
    # (13 registros no mesmo dia, varios duplicados a poucos segundos de
    # distancia). O aviso mostra o último registro de hoje; o campo usa
    # somente a última série principal para não sugerir um aquecimento.

    def _today_iso(self) -> str:
        return timezone.localdate().isoformat()

    def test_returns_todays_weight_for_the_movement(self):
        load_history = [{'movement_slug': 'hack-squat', 'weight_kg': 42.5, 'performed_on': self._today_iso(), 'set_role': 'top_set'}]

        self.assertEqual(todays_logged_weight(load_history, 'hack-squat'), 42.5)
        self.assertEqual(todays_top_set_weight(load_history, 'hack-squat'), 42.5)

    def test_today_status_keeps_warmup_but_input_uses_last_top_set(self):
        today = self._today_iso()
        history = [
            {'movement_slug': 'hack-squat', 'weight_kg': 80.0, 'performed_on': today, 'set_role': 'top_set'},
            {'movement_slug': 'hack-squat', 'weight_kg': 30.0, 'performed_on': today, 'set_role': 'warmup'},
        ]

        self.assertEqual(todays_logged_weight(history, 'hack-squat'), 30.0)
        self.assertEqual(todays_top_set_weight(history, 'hack-squat'), 80.0)
        self.assertIsNone(todays_top_set_weight(history[1:], 'hack-squat'))

    def test_ignores_entries_from_other_movements(self):
        load_history = [{'movement_slug': 'leg-press', 'weight_kg': 100.0, 'performed_on': self._today_iso(), 'set_role': 'top_set'}]

        self.assertIsNone(todays_logged_weight(load_history, 'hack-squat'))

    def test_ignores_entries_from_previous_days(self):
        load_history = [{'movement_slug': 'hack-squat', 'weight_kg': 40.0, 'performed_on': '2020-01-01', 'set_role': 'top_set'}]

        self.assertIsNone(todays_logged_weight(load_history, 'hack-squat'))

    def test_returns_the_most_recent_entry_when_saved_more_than_once_today(self):
        # Cenario exato do achado real: clique repetido no mesmo dia grava
        # varias linhas (idempotency_key diferente a cada clique, de
        # proposito -- ver load_tracker.js) -- o campo deve refletir a
        # ULTIMA, nunca a primeira.
        today = self._today_iso()
        load_history = [
            {'movement_slug': 'hack-squat', 'weight_kg': 40.0, 'performed_on': today, 'set_role': 'top_set'},
            {'movement_slug': 'hack-squat', 'weight_kg': 42.5, 'performed_on': today, 'set_role': 'top_set'},
        ]

        self.assertEqual(todays_logged_weight(load_history, 'hack-squat'), 42.5)

    def test_empty_history_returns_none(self):
        self.assertIsNone(todays_logged_weight([], 'hack-squat'))


class TodaysLoggedRepsAndRirTagTests(TestCase):
    # Mesma busca de TodaysLoggedWeightTagTests, so que pros dois campos
    # novos (plano curva-carga-completa-reps-rir-recorde, Fase 1).

    def _today_iso(self) -> str:
        return timezone.localdate().isoformat()

    def test_todays_logged_reps_returns_reps_for_the_movement(self):
        load_history = [{'movement_slug': 'hack-squat', 'reps': 8, 'performed_on': self._today_iso()}]

        self.assertEqual(todays_logged_reps(load_history, 'hack-squat'), 8)

    def test_todays_logged_reps_ignores_other_movements(self):
        load_history = [{'movement_slug': 'leg-press', 'reps': 10, 'performed_on': self._today_iso()}]

        self.assertIsNone(todays_logged_reps(load_history, 'hack-squat'))

    def test_todays_logged_reps_ignores_previous_days(self):
        load_history = [{'movement_slug': 'hack-squat', 'reps': 8, 'performed_on': '2020-01-01'}]

        self.assertIsNone(todays_logged_reps(load_history, 'hack-squat'))

    def test_todays_logged_rir_returns_rir_for_the_movement(self):
        load_history = [{'movement_slug': 'hack-squat', 'rir': 1.5, 'performed_on': self._today_iso()}]

        self.assertEqual(todays_logged_rir(load_history, 'hack-squat'), 1.5)

    def test_todays_logged_rir_empty_history_returns_none(self):
        self.assertIsNone(todays_logged_rir([], 'hack-squat'))

    def test_todays_logged_idempotency_key_returns_key_for_the_movement(self):
        # Fase 3 do plano curva-carga-completa-reps-rir-recorde (§4.2) --
        # esta chave e' o que o cliente manda como supersedes_idempotency_key
        # quando o aluno edita e salva de novo no mesmo dia.
        load_history = [{'movement_slug': 'hack-squat', 'idempotency_key': 'k1', 'performed_on': self._today_iso()}]

        self.assertEqual(todays_logged_idempotency_key(load_history, 'hack-squat'), 'k1')

    def test_todays_logged_idempotency_key_empty_history_returns_none(self):
        self.assertIsNone(todays_logged_idempotency_key([], 'hack-squat'))


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

        self.assertIn('Toque em registrar para acompanhar a evolução.', html)

    def test_registration_hint_absent_once_one_rep_max_exists(self):
        payload = build_example_payload()
        movement = payload['days'][0]['blocks'][0]['movements'][0]
        one_rm = {movement['movement_slug']: {'value_kg': 100.0}}

        html = _render(payload, one_rep_max_by_movement=one_rm)

        self.assertNotIn('Toque em registrar para acompanhar a evolução.', html)
