"""
ARQUIVO: testes do extrator de movimentos dos 10 programas legados
(Onda A0 do CORDA — docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- o parser HTML e a parte mais fragil deste comando: um regex "nome mais
  proximo, link mais proximo" cruza a fronteira de um bloco `.ex` sem
  wiki-btn (ex.: os inserts de corrida/cardio) e associa o nome errado ao
  link do exercicio SEGUINTE. Achado ao prototipar, antes de qualquer
  commit — o teste de fronteira de bloco existe para nunca deixar essa
  classe de bug voltar.
- idempotencia e "nunca sobrescreve status/movement_pattern revisados"
  sao a garantia de que rodar o comando de novo (ex.: apos editar um dos
  10 HTMLs) nao apaga trabalho de revisao humana ja feito.
"""

from django.core.management import call_command
from django.test import TestCase

from public_workouts.management.commands.extract_movements_from_html import (
    CROSSFIT_ESSENTIALS,
    LEGACY_WORKOUT_SLUGS,
    _extract_pairs_from_html,
)
from public_workouts.models import PublicWorkoutMovement, PublicWorkoutMovementModality, PublicWorkoutMovementStatus


_BLOCK_WITH_CARDIO_INSERT_THEN_EXERCISE = """
<div class="ex">
  <div class="ex-top">
    <div class="ex-left">
      <div class="ex-code">Cardio · Esteira</div>
      <div class="ex-name">Corrida — 10 min</div>
    </div>
  </div>
  <div class="ex-note">Sem link — insert de cardio, nao tem wiki-btn.</div>
</div>
<div class="ex">
  <div class="ex-top">
    <div class="ex-left">
      <div class="ex-code">A1 · Peito — Compound</div>
      <div class="ex-name">Supino reto com barra</div>
      <div class="ex-var"><span class="var-lbl">Variação:</span><a class="var-link" href="https://musclewiki.com/exercise/dumbbell-bench-press">Supino com halteres</a></div>
    </div>
    <a class="wiki-btn" href="https://musclewiki.com/exercise/barbell-bench-press" target="_blank" rel="noopener">Ver no MuscleWiki ↗</a>
  </div>
  <div class="gym-card">
    <div class="gym-summary"><strong>Supino reto c/ barra</strong></div>
    <a class="gym-wiki" href="https://musclewiki.com/exercise/barbell-bench-press">Ver ↗</a>
  </div>
</div>
"""


class ExerciseBlockParserTests(TestCase):
    def test_cardio_insert_without_wiki_btn_does_not_leak_into_next_block(self):
        # O bug que motivou o parser escopado por bloco: uma extracao ingenua
        # ("nome mais proximo do wiki-btn mais proximo") associaria "Corrida
        # — 10 min" ao href de barbell-bench-press (o wiki-btn seguinte).
        pairs = _extract_pairs_from_html(_BLOCK_WITH_CARDIO_INSERT_THEN_EXERCISE)

        self.assertEqual(pairs, [('Supino reto com barra', 'https://musclewiki.com/exercise/barbell-bench-press')])

    def test_var_link_is_not_mistaken_for_wiki_btn(self):
        # var-link (a variacao) tem seu proprio href — nao pode vencer o
        # wiki-btn do movimento principal.
        pairs = _extract_pairs_from_html(_BLOCK_WITH_CARDIO_INSERT_THEN_EXERCISE)

        self.assertEqual(len(pairs), 1)
        self.assertNotIn('dumbbell-bench-press', pairs[0][1])

    def test_block_without_ex_name_is_skipped_without_crashing(self):
        html = """
        <div class="ex">
          <div class="ex-top">
            <a class="wiki-btn" href="https://musclewiki.com/exercise/orphan">Ver ↗</a>
          </div>
        </div>
        """
        pairs = _extract_pairs_from_html(html)

        self.assertEqual(pairs, [])


class ExtractMovementsFromHtmlCommandTests(TestCase):
    def test_running_against_real_templates_creates_expected_counts(self):
        call_command('extract_movements_from_html')

        strength_count = PublicWorkoutMovement.objects.filter(modality=PublicWorkoutMovementModality.STRENGTH).count()
        crossfit_count = PublicWorkoutMovement.objects.filter(modality=PublicWorkoutMovementModality.CROSSFIT).count()

        # 82 movimentos unicos extraidos dos 10 HTMLs reais, menos 1 (toes-to-bar,
        # que tambem esta nos essenciais de CrossFit e vira modality=crossfit).
        self.assertEqual(strength_count, 81)
        self.assertEqual(crossfit_count, len(CROSSFIT_ESSENTIALS))
        self.assertEqual(PublicWorkoutMovement.objects.count(), 81 + len(CROSSFIT_ESSENTIALS))

    def test_html_derived_movements_default_to_pending_and_no_pattern(self):
        call_command('extract_movements_from_html')

        movement = PublicWorkoutMovement.objects.get(slug='barbell-bench-press')

        self.assertEqual(movement.status, PublicWorkoutMovementStatus.PENDING)
        self.assertEqual(movement.movement_pattern, '')
        self.assertEqual(movement.label_pt, 'Supino reto com barra')
        self.assertEqual(movement.reference_url, 'https://musclewiki.com/exercise/barbell-bench-press')

    def test_crossfit_essentials_are_seeded_as_active(self):
        call_command('extract_movements_from_html')

        movement = PublicWorkoutMovement.objects.get(slug='back-squat')

        self.assertEqual(movement.modality, PublicWorkoutMovementModality.CROSSFIT)
        self.assertEqual(movement.status, PublicWorkoutMovementStatus.ACTIVE)

    def test_running_twice_is_idempotent(self):
        call_command('extract_movements_from_html')
        first_count = PublicWorkoutMovement.objects.count()

        call_command('extract_movements_from_html')

        self.assertEqual(PublicWorkoutMovement.objects.count(), first_count)

    def test_second_run_does_not_overwrite_manually_set_movement_pattern(self):
        call_command('extract_movements_from_html')
        movement = PublicWorkoutMovement.objects.get(slug='barbell-squat')
        movement.movement_pattern = 'squat'
        movement.status = PublicWorkoutMovementStatus.ACTIVE
        movement.save(update_fields=['movement_pattern', 'status'])

        call_command('extract_movements_from_html')

        movement.refresh_from_db()
        self.assertEqual(movement.movement_pattern, 'squat')
        self.assertEqual(movement.status, PublicWorkoutMovementStatus.ACTIVE)

    def test_dry_run_persists_nothing(self):
        call_command('extract_movements_from_html', '--dry-run')

        self.assertEqual(PublicWorkoutMovement.objects.count(), 0)

    def test_extraction_never_touches_student_app_movement_library(self):
        # V1 do CORDA (secao D.00): PublicWorkoutMovement pode ser semeado a
        # partir de MovementLibrary (copia read-only da lista), mas o
        # comando nunca pode ESCREVER nela — senao um movimento de
        # musculacao apareceria no picker de WOD do coach de um box.
        from student_app.models import MovementLibrary

        before = MovementLibrary.objects.count()

        call_command('extract_movements_from_html')

        self.assertEqual(MovementLibrary.objects.count(), before)

    def test_all_ten_legacy_templates_are_covered(self):
        # Regressao contra remocao acidental de um slug da lista — os 10
        # templates precisam existir de verdade (R.T do CORDA: sao os
        # mesmos 10 que a Onda A2 migra).
        import pathlib

        for slug in LEGACY_WORKOUT_SLUGS:
            path = pathlib.Path('templates') / 'public_workouts' / f'{slug}.html'
            self.assertTrue(path.exists(), f'template ausente: {path}')

        self.assertEqual(len(LEGACY_WORKOUT_SLUGS), 10)
