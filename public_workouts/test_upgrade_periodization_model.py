"""
ARQUIVO: testes do comando upgrade_periodization_model (Onda B3+ do CORDA
— "Periodização canônica").
"""

from django.core.management import CommandError, call_command
from django.test import TestCase

from public_workouts import services
from public_workouts.management.commands.upgrade_periodization_model import CURATED_WEEKS_MAPPING
from public_workouts.schema import build_example_payload


class UpgradePeriodizationModelCommandTests(TestCase):
    def test_unknown_slug_raises_command_error(self):
        services.publish_program(slug='bruno', payload=build_example_payload())

        with self.assertRaises(CommandError):
            call_command('upgrade_periodization_model', slug='bruno')  # bruno nao esta em CURATED_WEEKS_MAPPING

    def test_slug_without_published_program_raises_command_error(self):
        # 'juliana' esta em CURATED_WEEKS_MAPPING mas ninguem publicou nada
        # nesta base de teste ainda.
        with self.assertRaises(CommandError):
            call_command('upgrade_periodization_model', slug='juliana')

    def test_dry_run_does_not_persist_anything(self):
        services.publish_program(slug='juliana', payload=build_example_payload())

        call_command('upgrade_periodization_model', slug='juliana', dry_run=True)

        program = services.get_active_program(slug='juliana')
        self.assertNotIn('weeks', (program.get('periodization') or {}))

    def test_publishes_a_new_version_with_canonical_weeks(self):
        services.publish_program(slug='juliana', payload=build_example_payload())

        call_command('upgrade_periodization_model', slug='juliana')

        program = services.get_active_program(slug='juliana')
        weeks = program['periodization']['weeks']
        self.assertEqual(weeks, CURATED_WEEKS_MAPPING['juliana'])

    def test_publishing_creates_a_new_version_not_an_in_place_edit(self):
        services.publish_program(slug='juliana', payload=build_example_payload())

        call_command('upgrade_periodization_model', slug='juliana')

        versions = services.list_program_versions(slug='juliana')
        self.assertEqual(len(versions), 2)
        self.assertTrue(versions[0]['is_active'])

    def test_preserves_existing_payload_fields(self):
        payload = build_example_payload()
        services.publish_program(slug='juliana', payload=payload)

        call_command('upgrade_periodization_model', slug='juliana')

        program = services.get_active_program(slug='juliana')
        self.assertEqual(program['program_label'], payload['program_label'])
        self.assertEqual(len(program['days']), len(payload['days']))

    def test_preserves_existing_periodization_fields_alongside_weeks(self):
        payload = build_example_payload()
        payload['periodization'] = {
            'weeks_table': [{'week': 'S1', 'focus': 'x', 'reps': 'x', 'guidance': 'x'}],
            'volume_table': [], 'note': 'nota existente', 'chart': [],
        }
        services.publish_program(slug='juliana', payload=payload)

        call_command('upgrade_periodization_model', slug='juliana')

        program = services.get_active_program(slug='juliana')
        self.assertEqual(program['periodization']['note'], 'nota existente')
        self.assertIn('weeks', program['periodization'])
