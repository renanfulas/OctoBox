"""
ARQUIVO: testes de sugestao de substituicao de exercicio (Onda A3 do CORDA).

POR QUE ELE EXISTE:
- a regra que mais importa nao e' "acha um do mesmo padrao" (trivial) —
  e' NUNCA sugerir um `pending`/sem padrao como se fosse uma recomendacao
  revisada. Cada teste aqui protege uma dessas fronteiras.
"""

from django.test import TestCase

from public_workouts.models import PublicWorkoutMovement, PublicWorkoutMovementModality, PublicWorkoutMovementStatus
from public_workouts.substitutions import suggest_substitutes


def _make(slug, label_pt, *, pattern='', status=PublicWorkoutMovementStatus.ACTIVE,
          modality=PublicWorkoutMovementModality.STRENGTH, reference_url=''):
    return PublicWorkoutMovement.objects.create(
        slug=slug, label_pt=label_pt, movement_pattern=pattern, status=status,
        modality=modality, reference_url=reference_url,
    )


class SuggestSubstitutesTests(TestCase):
    def test_unknown_slug_returns_empty(self):
        self.assertEqual(suggest_substitutes(movement_slug='nao-existe'), [])

    def test_movement_without_pattern_returns_empty(self):
        _make('acessorio-livre', 'Acessório livre', pattern='')

        self.assertEqual(suggest_substitutes(movement_slug='acessorio-livre'), [])

    def test_crossfit_essential_without_pattern_returns_empty(self):
        _make('back-squat', 'Agachamento Costas', pattern='', modality=PublicWorkoutMovementModality.CROSSFIT)

        self.assertEqual(suggest_substitutes(movement_slug='back-squat'), [])

    def test_no_other_active_movement_in_same_pattern_returns_empty(self):
        _make('barbell-squat', 'Agachamento livre com barra', pattern='squat')

        self.assertEqual(suggest_substitutes(movement_slug='barbell-squat'), [])

    def test_returns_other_active_movements_in_same_pattern(self):
        _make('barbell-squat', 'Agachamento livre com barra', pattern='squat',
              reference_url='https://musclewiki.com/exercise/barbell-squat')
        _make('machine-leg-press', 'Leg press', pattern='squat',
              reference_url='https://musclewiki.com/exercise/machine-leg-press')
        _make('dumbbell-goblet-squat', 'Agachamento goblet com halter', pattern='squat')

        result = suggest_substitutes(movement_slug='barbell-squat')

        self.assertEqual([r['slug'] for r in result], ['dumbbell-goblet-squat', 'machine-leg-press'])
        self.assertNotIn('barbell-squat', [r['slug'] for r in result])
        self.assertEqual(result[1]['reference_url'], 'https://musclewiki.com/exercise/machine-leg-press')

    def test_pending_movements_in_same_pattern_are_never_suggested(self):
        # A regra que mais importa: pending nao e' recomendacao revisada.
        _make('barbell-squat', 'Agachamento livre com barra', pattern='squat')
        _make('some-new-squat-variant', 'Variação nova (não revisada)', pattern='squat',
              status=PublicWorkoutMovementStatus.PENDING)

        self.assertEqual(suggest_substitutes(movement_slug='barbell-squat'), [])

    def test_movements_in_a_different_pattern_are_never_suggested(self):
        _make('barbell-squat', 'Agachamento livre com barra', pattern='squat')
        _make('barbell-bench-press', 'Supino reto com barra', pattern='horizontal-push')

        self.assertEqual(suggest_substitutes(movement_slug='barbell-squat'), [])

    def test_limit_caps_the_result_list(self):
        _make('barbell-squat', 'Agachamento livre com barra', pattern='squat')
        _make('machine-leg-press', 'Leg press', pattern='squat')
        _make('dumbbell-goblet-squat', 'Agachamento goblet com halter', pattern='squat')
        _make('machine-hack-squat', 'Hack squat', pattern='squat')

        result = suggest_substitutes(movement_slug='barbell-squat', limit=2)

        self.assertEqual(len(result), 2)

    def test_reference_url_is_none_not_empty_string_when_missing(self):
        _make('barbell-squat', 'Agachamento livre com barra', pattern='squat')
        _make('dumbbell-goblet-squat', 'Agachamento goblet com halter', pattern='squat', reference_url='')

        result = suggest_substitutes(movement_slug='barbell-squat')

        self.assertIsNone(result[0]['reference_url'])
