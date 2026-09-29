from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from operations import workout_templates


class PersistedWorkoutTemplateCopyTests(SimpleTestCase):
    def test_duplicate_preserves_block_and_movement_prescription_metadata(self):
        actor = object()
        movement = SimpleNamespace(
            movement_slug='push_press',
            movement_label='Push press',
            sets=5,
            reps=3,
            reps_spec='21/15/9',
            load_type='percentage_of_rm',
            load_value='70.00',
            load_spec='70% RM',
            is_scaled_alternative=True,
            notes='Carga por categoria.',
            sort_order=2,
        )
        block = SimpleNamespace(
            kind='metcon',
            title='WOD',
            notes='Manter consistencia.',
            timecap_min=12,
            rounds=3,
            interval_seconds=60,
            score_type='for_time',
            format_spec='21/15/9',
            sort_order=1,
            movements=SimpleNamespace(all=lambda: [movement]),
        )
        source = SimpleNamespace(
            name='Semana base',
            description='Template original.',
            created_by=actor,
            source_workout=None,
            is_active=True,
            is_trusted=False,
            blocks=SimpleNamespace(all=lambda: [block]),
        )
        copied_template = object()
        copied_block = object()

        with (
            patch.object(workout_templates.WorkoutTemplate.objects, 'create', return_value=copied_template) as create_template,
            patch.object(workout_templates.WorkoutTemplateBlock.objects, 'create', return_value=copied_block) as create_block,
            patch.object(workout_templates.WorkoutTemplateMovement.objects, 'create') as create_movement,
        ):
            result = workout_templates.duplicate_persisted_template(actor=actor, template=source)

        self.assertIs(result, copied_template)
        create_template.assert_called_once_with(
            name='Semana base copia',
            description='Template original.',
            created_by=actor,
            source_workout=None,
            is_active=True,
            is_featured=False,
            is_trusted=False,
        )
        self.assertEqual(
            create_block.call_args.kwargs,
            {
                'template': copied_template,
                'kind': 'metcon',
                'title': 'WOD',
                'notes': 'Manter consistencia.',
                'timecap_min': 12,
                'rounds': 3,
                'interval_seconds': 60,
                'score_type': 'for_time',
                'format_spec': '21/15/9',
                'sort_order': 1,
            },
        )
        self.assertEqual(
            create_movement.call_args.kwargs,
            {
                'block': copied_block,
                'movement_slug': 'push_press',
                'movement_label': 'Push press',
                'sets': 5,
                'reps': 3,
                'reps_spec': '21/15/9',
                'load_type': 'percentage_of_rm',
                'load_value': '70.00',
                'load_spec': '70% RM',
                'is_scaled_alternative': True,
                'notes': 'Carga por categoria.',
                'sort_order': 2,
            },
        )
