"""
ARQUIVO: testes do comando `migrate_legacy_workouts` (Onda A2 do CORDA —
docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- e' o criterio de aceite real da migracao dos 10 programas de consultoria
  pra `PublicWorkoutProgram`: nao basta o parser rodar sem erro (isso ja e'
  coberto por `test_parser.py`, com fixtures sinteticas) -- precisa provar,
  contra os 10 HTMLs REAIS, que nenhum exercicio sumiu (fixture de
  contagem) e que o texto/link migrado rastreia ate a pagina original
  (subconjunto do golden de `scripts/public_workout_signature.py`).
- as contagens abaixo vieram de `migrate_legacy_workouts --dry-run`
  conferido visualmente contra cada um dos 10 HTMLs nesta sessao -- ver
  Onda A2 do plano. Se esse numero mudar sem uma edicao intencional de
  algum dos 10 templates, algo no parser regrediu.
"""

import json

from django.core.management import call_command
from django.test import TestCase

from public_workouts import schema, services
from public_workouts.management.commands.extract_movements_from_html import LEGACY_WORKOUT_SLUGS
from public_workouts.models import PublicWorkoutProgram

EXPECTED_COUNTS = {
    'bruno': {'days': 5, 'movements': 26, 'skipped': 0},
    # franciele: 29 (so' "Etapa 2 - Forca") + 20 (4 dias com "Etapa 1 -
    # Mobilidade/..." x 4 c-row + qua x4, sex x4 = 20 movimentos auxiliares
    # via _EmbeddedStageParser, ate entao ignorados por completo -- mudanca
    # intencional, nao regressao (ver parser.py::_EmbeddedStageParser).
    'franciele': {'days': 5, 'movements': 49, 'skipped': 0},
    'giovanna': {'days': 3, 'movements': 12, 'skipped': 0},
    'henrique': {'days': 5, 'movements': 26, 'skipped': 0},
    'john': {'days': 6, 'movements': 30, 'skipped': 0},
    'johnespanha': {'days': 5, 'movements': 30, 'skipped': 0},
    'juliana': {'days': 4, 'movements': 23, 'skipped': 0},
    'milene': {'days': 3, 'movements': 15, 'skipped': 1},
    'rafael': {'days': 4, 'movements': 15, 'skipped': 0},
    'thaislima': {'days': 3, 'movements': 14, 'skipped': 0},
}

EXPECTED_ACCENT_VARIANT = {
    'franciele': 'F',
    'rafael': 'M',
}


def _count_movements(payload: dict) -> int:
    return sum(len(block['movements']) for day in payload['days'] for block in day['blocks'])


class MigrateLegacyWorkoutsCommandTests(TestCase):
    def test_all_ten_slugs_have_an_expected_count_fixture(self):
        # Regressao contra "esqueceu de atualizar a fixture" tanto quanto
        # contra o parser em si -- os dois dicionarios acima tem que cobrir
        # exatamente os 10 slugs reais.
        self.assertEqual(set(EXPECTED_COUNTS), set(LEGACY_WORKOUT_SLUGS))

    def test_dry_run_persists_nothing(self):
        call_command('migrate_legacy_workouts', '--dry-run')

        self.assertEqual(PublicWorkoutProgram.objects.count(), 0)

    def test_real_run_publishes_all_ten_with_valid_schema(self):
        call_command('migrate_legacy_workouts')

        self.assertEqual(PublicWorkoutProgram.objects.filter(is_active=True).count(), 10)
        for slug in LEGACY_WORKOUT_SLUGS:
            with self.subTest(slug=slug):
                payload = services.get_active_program(slug=slug)
                self.assertIsNotNone(payload, f'{slug}: nao foi publicado')
                self.assertEqual(schema.validate_payload(payload), [])

    def test_movement_count_per_day_matches_manually_verified_fixture(self):
        # Pega desaparecimento silencioso de exercicio: se um `.ex` parar de
        # ser reconhecido (ex.: uma variacao de markup nova de algum
        # cliente), a contagem move e o teste acusa -- mesmo que o payload
        # continue "valido" pelo schema (schema nao sabe quantos exercicios
        # DEVERIAM existir).
        call_command('migrate_legacy_workouts')

        for slug, expected in EXPECTED_COUNTS.items():
            with self.subTest(slug=slug):
                payload = services.get_active_program(slug=slug)
                self.assertEqual(len(payload['days']), expected['days'], f'{slug}: numero de dias mudou')
                self.assertEqual(
                    _count_movements(payload), expected['movements'], f'{slug}: numero de movimentos mudou',
                )

    def test_accent_variant_is_derived_from_assessment_sex_not_hardcoded(self):
        call_command('migrate_legacy_workouts')

        for slug in LEGACY_WORKOUT_SLUGS:
            with self.subTest(slug=slug):
                payload = services.get_active_program(slug=slug)
                expected = EXPECTED_ACCENT_VARIANT.get(slug)
                self.assertEqual(payload['accent_variant'], expected)

    def test_migrated_payload_content_is_a_subset_of_the_legacy_golden(self):
        # "Subconjunto", nao igualdade: o golden (pagina renderizada) tem
        # nav/variacoes/widgets narrativos que o payload nao modela de
        # proposito (so' a prescricao: reps/RIR/link) -- ver docstring de
        # scripts/public_workout_signature.py.
        from scripts.public_workout_signature import golden_path, payload_fidelity_report

        call_command('migrate_legacy_workouts')

        for slug in LEGACY_WORKOUT_SLUGS:
            with self.subTest(slug=slug):
                path = golden_path(slug)
                self.assertTrue(path.exists(), f'golden ausente pra {slug}: {path}')
                golden = json.loads(path.read_text(encoding='utf-8'))

                payload = services.get_active_program(slug=slug)
                problems = payload_fidelity_report(payload, golden)

                self.assertEqual(problems, [], f'{slug}: {problems}')

    def test_running_twice_publishes_a_new_active_version_not_a_duplicate_slug(self):
        # publish_program (Onda A1) ja garante isso -- este teste e' so' a
        # ponta do management command, nao uma reimplementacao da regra.
        call_command('migrate_legacy_workouts', '--slug=bruno')
        call_command('migrate_legacy_workouts', '--slug=bruno')

        active = PublicWorkoutProgram.objects.filter(slug='bruno', is_active=True)
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.first().version, 2)


class MigratedProgramAcceptanceTests(TestCase):
    """Traduz os requisitos de negocio explicitos dos 3 clientes de
    Categoria 3 (student_app/tests.py) para o PAYLOAD migrado.

    Deliberadamente NAO substitui os testes de student_app/tests.py que
    leem a pagina ao vivo (`/renan/<slug>`): aquela rota ainda serve o HTML
    estatico ate a Onda B3 fazer o corte de producao pro payload, entao
    aqueles testes continuam sendo a protecao real do que o aluno ve HOJE.
    Estes aqui sao o criterio de aceite da MIGRACAO em si -- e cobrem menos
    superficie de proposito: o payload (schema.py, Onda S0) nao carrega
    nome de exercicio nem copy narrativa de widget (ex.: "4 sessoes · 100
    min"), so' movement_slug/reps_spec/rir_spec/reference_url.
    """

    def test_juliana_payload_preserves_day_order_and_quad_frequency_exercises(self):
        call_command('migrate_legacy_workouts', '--slug=juliana')
        payload = services.get_active_program(slug='juliana')

        self.assertEqual([day['day_id'] for day in payload['days']], ['ter', 'qua', 'qui', 'sab'])

        slugs = {m['movement_slug'] for day in payload['days'] for block in day['blocks'] for m in block['movements']}
        specs = [
            m['reps_spec']
            for day in payload['days'] for block in day['blocks'] for m in block['movements']
        ]

        # Quadriceps em alta frequencia (2x/semana): mesmo movement_slug
        # (cadeira extensora) aparece nos dois dias, com prescricoes
        # DIFERENTES -- se um dia sumir, uma das duas specs some tambem.
        self.assertIn('machine-leg-extension', slugs)
        self.assertIn('5× Top (12-15) · pausa 1s no topo', specs)
        self.assertIn('2× 8 pesado → 2× 20 leve', specs)
        self.assertIn('dumbbell-sumo-squat', slugs)
        self.assertIn('smith-machine-calf-raise', slugs)

    def test_henrique_payload_preserves_day_order_and_required_back_exercises(self):
        call_command('migrate_legacy_workouts', '--slug=henrique')
        payload = services.get_active_program(slug='henrique')

        self.assertEqual([day['day_id'] for day in payload['days']], ['seg', 'ter', 'qua', 'qui', 'sex'])

        slugs = {m['movement_slug'] for day in payload['days'] for block in day['blocks'] for m in block['movements']}

        # Exigidos explicitamente no escopo do treino: trapezio medio /
        # deltoide posterior no dia de costas.
        self.assertIn('dumbbell-rear-delt-fly', slugs)  # Crucifixo invertido
        self.assertIn('cable-bar-face-pull', slugs)  # Face pull no cabo

    def test_johnespanha_payload_preserves_day_order_and_glute_priority(self):
        call_command('migrate_legacy_workouts', '--slug=johnespanha')
        payload = services.get_active_program(slug='johnespanha')

        self.assertEqual([day['day_id'] for day in payload['days']], ['seg', 'ter', 'qua', 'qui', 'sex'])

        slugs = [m['movement_slug'] for day in payload['days'] for block in day['blocks'] for m in block['movements']]
        specs = [m['rir_spec'] for day in payload['days'] for block in day['blocks'] for m in block['movements']]

        # Gluteo e' a unica prioridade de crescimento (hip thrust como
        # exercicio-ancora, presente em 2 dias diferentes da semana).
        self.assertEqual(slugs.count('barbell-hip-thrust'), 2)
        # Costas/peito em volume minimo de manutencao de proposito (RIR
        # alto = longe da falha).
        self.assertIn('RIR 3 · ADM parcial no alongamento', specs)
