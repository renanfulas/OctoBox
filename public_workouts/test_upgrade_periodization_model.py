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
        services.publish_program(slug='giovanna', payload=build_example_payload())

        with self.assertRaises(CommandError):
            call_command('upgrade_periodization_model', slug='giovanna')  # giovanna nao esta em CURATED_WEEKS_MAPPING

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

    def test_newly_curated_slugs_publish_a_schema_valid_canonical_mapping(self):
        # Auditoria "pegue todos os treinos e corrija a periodizacao"
        # (pedido do Renan): henrique/john/milene/bruno entraram no
        # mapeamento curado -- confere que os 4 publicam sem erro de
        # schema e batem com o mapeamento declarado (nao promove alguem
        # que ainda nao deveria estar aqui, ex. giovanna, que fica de fora
        # de proposito).
        for slug in ('henrique', 'john', 'milene', 'bruno'):
            services.publish_program(slug=slug, payload=build_example_payload())

            call_command('upgrade_periodization_model', slug=slug)

            program = services.get_active_program(slug=slug)
            self.assertEqual(program['periodization']['weeks'], CURATED_WEEKS_MAPPING[slug])

        self.assertNotIn('giovanna', CURATED_WEEKS_MAPPING)

    def test_bruno_maintenance_and_test_weeks_use_hold_load_phase_types(self):
        # Bloco de corte (Renan aprovou propor phase_type novo: "vamos
        # tomar essa frente") -- confere que o mapeamento publicado usa
        # de verdade os phase_type com hold_load=True, nao aproximacoes
        # pras 6 fases antigas.
        services.publish_program(slug='bruno', payload=build_example_payload())

        call_command('upgrade_periodization_model', slug='bruno')

        weeks = services.get_active_program(slug='bruno')['periodization']['weeks']
        phase_types_by_week = {row['week_number']: row['phase_type'] for row in weeks}
        self.assertEqual(phase_types_by_week[2], 'maintenance')
        self.assertEqual(phase_types_by_week[3], 'maintenance')
        self.assertEqual(phase_types_by_week[4], 'maintenance')
        self.assertEqual(phase_types_by_week[5], 'test')

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
