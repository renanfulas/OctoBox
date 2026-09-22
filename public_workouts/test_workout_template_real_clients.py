"""
ARQUIVO: renderiza o payload REAL dos 10 clientes (parseado do HTML legado
de verdade, nunca fixture sintetica) atraves do template inteiro
(templates/public_workouts/workout.html).

POR QUE ELE EXISTE — achado da auditoria de QA pedida pelo Renan ("faça um
teste de QA pra ver bugs"):
- `test_workout_template.py` prova que o template renderiza qualquer
  payload valido pelo CONTRATO de schema.py, mas so' usa
  `build_example_payload()`/fixtures curadas — nunca o texto livre de
  verdade que um treinador escreveu.
- `test_migrate_legacy_workouts.py` prova que o parser produz um payload
  SCHEMA-VALIDO pros 10 clientes reais, mas nunca renderiza esse payload
  atraves do template — schema.py nao sabe (nem deveria) se um
  `reps_spec`/`rir_spec` de verdade quebra um filtro/tag (`reps_phases`,
  `movement_load_display`, `glossary_highlight`) que so' foi exercitado
  contra texto sintetico ate agora.
- Sem este arquivo, um filtro que so' quebra contra um formato de texto
  real e especifico (ex.: um `reps_spec` de um cliente futuro parecido com
  o dialeto do john.html) passaria batido nos dois arquivos acima e so'
  apareceria em producao.

PONTOS CRITICOS:
- `current_period_phase` (workout.html) usa `date.today()` sem override
  pra teste (decisao correta pra producao) -- por isso os testes aqui
  NUNCA afirmam qual fase canonica esta ativa (isso muda com o calendario
  real), so' que o render NAO EXPLODE mesmo com 1RM/historico de carga
  simulados alimentando o caminho de fase progressiva + ramp.
"""

from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.test import TestCase

from public_workouts.management.commands.extract_movements_from_html import LEGACY_WORKOUT_SLUGS
from public_workouts.management.commands.migrate_legacy_workouts import LEGACY_PROGRAM_METADATA
from public_workouts.parser import build_program_payload_from_html
from public_workouts.schema import validate_payload

_CANONICAL_PERIODIZATION_SLUGS = ('henrique', 'john', 'juliana', 'milene', 'bruno')


def _real_payload(slug: str) -> dict:
    from student_app.views.public_workout_views import PUBLIC_WORKOUT_LIBRARY

    path = Path(settings.BASE_DIR) / 'templates' / 'public_workouts' / f'{slug}.html'
    html = path.read_text(encoding='utf-8')
    metadata = LEGACY_PROGRAM_METADATA[slug]
    plan = PUBLIC_WORKOUT_LIBRARY.get(slug)
    payload, _skipped = build_program_payload_from_html(
        html=html,
        program_id=f'{slug}-legado-v1',
        program_label=metadata['program_label'],
        started_on=metadata.get('started_on') or '2026-01-01',
        weeks=metadata['weeks'],
        accent_variant=plan.assessment_sex if plan else None,
    )
    return payload


def _render(payload: dict, *, plan_slug: str, load_history=None, one_rep_max_by_movement=None) -> str:
    from public_workouts.services import build_movement_label_lookup

    return render_to_string('public_workouts/workout.html', {
        'program': payload,
        'accent_variant': payload.get('accent_variant'),
        'program_versions': [],
        'load_history': load_history or [],
        'one_rep_max_by_movement': one_rep_max_by_movement or {},
        'trends_by_movement': {},
        'plan_slug': plan_slug,
        'movement_labels': build_movement_label_lookup(payload),
        'student_name': '',
        'student_photo_url': None,
        'customer_portal_url': None,
        'account_email': None,
    })


def _first_movement_slug(payload: dict) -> str:
    return payload['days'][0]['blocks'][0]['movements'][0]['movement_slug']


class AllRealClientsRenderWithoutErrorTests(TestCase):
    def test_all_ten_real_clients_render_without_exception(self):
        for slug in LEGACY_WORKOUT_SLUGS:
            with self.subTest(slug=slug):
                payload = _real_payload(slug)
                self.assertEqual(validate_payload(payload), [], f'{slug}: payload invalido')

                html = _render(payload, plan_slug=slug)

                self.assertIn(payload['program_label'], html)
                self.assertNotIn('TemplateSyntaxError', html)

    def test_all_ten_real_clients_render_with_load_history_and_one_rep_max(self):
        # Mesmo payload de cima, mas alimentando 1RM + historico de carga
        # pro PRIMEIRO movimento de cada cliente -- exercita o caminho de
        # `movement_load_display` que calcula kg (percentage_of_rm+1RM,
        # fase progressiva, estimativa por texto) em vez de so' cair no
        # fallback "Livre". Nenhum dos 10 tinha isso coberto contra texto
        # REAL antes desta fatia.
        for slug in LEGACY_WORKOUT_SLUGS:
            with self.subTest(slug=slug):
                payload = _real_payload(slug)
                movement_slug = _first_movement_slug(payload)

                html = _render(
                    payload,
                    plan_slug=slug,
                    one_rep_max_by_movement={movement_slug: {'value_kg': 100.0}},
                    load_history=[{
                        'movement_slug': movement_slug,
                        'weight_kg': 80.0,
                        'performed_on': payload['started_on'],
                        'program_id': payload['program_id'],
                    }],
                )

                self.assertIn(payload['program_label'], html)


class CanonicalPeriodizationRealClientsRenderTests(TestCase):
    """Os 5 clientes com `periodization.weeks` curado (henrique/john/
    juliana/milene/bruno, `CURATED_WEEKS_MAPPING` em
    upgrade_periodization_model.py) exercitam caminho extra: banner de
    fase + grafico com semana atual destacada + ramp de Prep/Feeder nos
    chips. `bruno` especificamente exercita o caminho `hold_load` (fases
    `maintenance`/`test`, bloco de corte) através do template inteiro,
    não só da função pura (ver `HoldLoadPhaseTests` em
    test_periodization.py). O parser NUNCA produz `weeks` sozinho (so'
    existe depois da curadoria manual em cima do payload JA publicado —
    ver docstring de upgrade_periodization_model.py) — por isso injetamos
    o MESMO mapeamento curado aqui antes de renderizar, replicando o
    payload real publicado sem precisar de banco.

    `current_period_phase` (workout.html) usa `date.today()` sem override
    pra teste (decisao correta pra producao) -- por isso os testes aqui
    NUNCA afirmam qual fase canonica esta ativa (isso muda com o
    calendario real), so' que o render NAO EXPLODE mesmo com 1RM/
    historico de carga simulados alimentando o caminho de fase
    progressiva + ramp, em QUALQUER semana do ciclo."""

    def _payload_with_curated_weeks(self, slug: str) -> dict:
        from public_workouts.management.commands.upgrade_periodization_model import CURATED_WEEKS_MAPPING

        payload = _real_payload(slug)
        periodization = dict(payload.get('periodization') or {})
        periodization['weeks'] = CURATED_WEEKS_MAPPING[slug]
        payload['periodization'] = periodization
        return payload

    def test_curated_mapping_covers_exactly_these_five_slugs(self):
        from public_workouts.management.commands.upgrade_periodization_model import CURATED_WEEKS_MAPPING

        self.assertEqual(set(CURATED_WEEKS_MAPPING), set(_CANONICAL_PERIODIZATION_SLUGS))

    def test_canonical_clients_render_with_simulated_progressive_load_data(self):
        for slug in _CANONICAL_PERIODIZATION_SLUGS:
            with self.subTest(slug=slug):
                payload = self._payload_with_curated_weeks(slug)
                self.assertEqual(validate_payload(payload), [], f'{slug}: payload invalido')
                movement_slug = _first_movement_slug(payload)

                html = _render(
                    payload,
                    plan_slug=slug,
                    one_rep_max_by_movement={movement_slug: {'value_kg': 100.0}},
                    load_history=[{
                        'movement_slug': movement_slug,
                        'weight_kg': 80.0,
                        'performed_on': payload['started_on'],
                        'program_id': payload['program_id'],
                    }],
                )

                self.assertIn(payload['program_label'], html)
                self.assertIn('workout-period-chart', html)
