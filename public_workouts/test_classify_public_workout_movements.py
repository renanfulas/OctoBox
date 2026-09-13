"""
ARQUIVO: testes de classify_public_workout_movements (Onda A0).

POR QUE ELE EXISTE:
- a regra central deste comando e NUNCA sobrescrever uma edicao humana:
  se `movement_pattern` ja tem qualquer valor (inclusive um diferente da
  sugestao), o comando tem que preservar — e status nunca e tocado, so
  quem confirma a classificacao (voce) promove pending -> active.
"""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from .models import PublicWorkoutMovement, PublicWorkoutMovementModality, PublicWorkoutMovementStatus


class ClassifyPublicWorkoutMovementsTests(TestCase):
    def _make_movement(self, slug, movement_pattern='', status=PublicWorkoutMovementStatus.PENDING):
        return PublicWorkoutMovement.objects.create(
            slug=slug,
            label_pt=slug,
            modality=PublicWorkoutMovementModality.STRENGTH,
            movement_pattern=movement_pattern,
            status=status,
        )

    def test_fills_blank_pattern_for_known_slug(self):
        self._make_movement('barbell-hip-thrust')
        call_command('classify_public_workout_movements', stdout=StringIO())

        movement = PublicWorkoutMovement.objects.get(slug='barbell-hip-thrust')
        self.assertEqual(movement.movement_pattern, 'hip-hinge')

    def test_never_overwrites_an_existing_value_even_if_different(self):
        self._make_movement('barbell-hip-thrust', movement_pattern='algo-que-o-renan-escolheu')
        call_command('classify_public_workout_movements', stdout=StringIO())

        movement = PublicWorkoutMovement.objects.get(slug='barbell-hip-thrust')
        self.assertEqual(movement.movement_pattern, 'algo-que-o-renan-escolheu')

    def test_does_not_touch_status(self):
        self._make_movement('barbell-hip-thrust', status=PublicWorkoutMovementStatus.PENDING)
        call_command('classify_public_workout_movements', stdout=StringIO())

        movement = PublicWorkoutMovement.objects.get(slug='barbell-hip-thrust')
        self.assertEqual(movement.status, PublicWorkoutMovementStatus.PENDING)

    def test_running_twice_is_idempotent(self):
        self._make_movement('barbell-hip-thrust')
        call_command('classify_public_workout_movements', stdout=StringIO())

        stdout = StringIO()
        call_command('classify_public_workout_movements', stdout=stdout)
        self.assertIn('0 movimento(s)', stdout.getvalue())
        self.assertIn('1 ja tinham valor', stdout.getvalue())

    def test_dry_run_does_not_write_to_database(self):
        self._make_movement('barbell-hip-thrust')
        call_command('classify_public_workout_movements', dry_run=True, stdout=StringIO())

        movement = PublicWorkoutMovement.objects.get(slug='barbell-hip-thrust')
        self.assertEqual(movement.movement_pattern, '')

    def test_slug_not_yet_in_database_is_reported_not_crashed(self):
        stdout = StringIO()
        call_command('classify_public_workout_movements', stdout=stdout)
        self.assertIn('nao existem em PublicWorkoutMovement', stdout.getvalue())

    def test_unrecognized_slug_in_database_is_left_untouched(self):
        self._make_movement('exercicio-fora-da-tabela-de-classificacao')
        call_command('classify_public_workout_movements', stdout=StringIO())

        movement = PublicWorkoutMovement.objects.get(slug='exercicio-fora-da-tabela-de-classificacao')
        self.assertEqual(movement.movement_pattern, '')
