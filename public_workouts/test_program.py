"""
ARQUIVO: testes de S1 (leitura) e publish_program (escrita) do corredor
(Onda A1 do CORDA — docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- os 4 "Pronto quando" da Onda A1 sao garantias de integridade de dado real
  (nunca duas versoes ativas, publicar/reverter e so um UPDATE, movimento
  desconhecido nao trava a publicacao) — cada um tem que ter o teste que
  prova que a garantia segura, nao so "roda sem erro".
"""

import copy

from django.db import IntegrityError, transaction
from django.test import TestCase

from public_workouts.models import PublicWorkoutMovement, PublicWorkoutProgram
from public_workouts.schema import PayloadValidationError, build_example_payload
from public_workouts.services import (
    activate_program_version,
    get_active_program,
    list_program_versions,
    publish_program,
)


def _payload(**overrides) -> dict:
    payload = copy.deepcopy(build_example_payload())
    payload.update(overrides)
    return payload


class GetActiveProgramTests(TestCase):
    def test_returns_none_when_no_program_exists(self):
        self.assertIsNone(get_active_program(slug='bruno'))

    def test_returns_payload_of_active_program(self):
        payload = _payload(program_id='bruno-2026-q1')
        publish_program(slug='bruno', payload=payload)

        result = get_active_program(slug='bruno')

        self.assertEqual(result, payload)

    def test_ignores_inactive_versions(self):
        publish_program(slug='bruno', payload=_payload(program_id='bruno-2026-q1', weeks=4))
        publish_program(slug='bruno', payload=_payload(program_id='bruno-2026-q1', weeks=6))

        result = get_active_program(slug='bruno')

        self.assertEqual(result['weeks'], 6)

    def test_does_not_leak_between_slugs(self):
        publish_program(slug='bruno', payload=_payload(program_id='bruno-2026-q1'))

        self.assertIsNone(get_active_program(slug='juliana'))


class PublishProgramTests(TestCase):
    def test_first_publish_creates_version_1_active(self):
        program = publish_program(slug='bruno', payload=_payload(program_id='bruno-2026-q1'))

        self.assertEqual(program.version, 1)
        self.assertTrue(program.is_active)
        self.assertEqual(PublicWorkoutProgram.objects.count(), 1)

    def test_republish_creates_version_2_and_deactivates_version_1(self):
        v1 = publish_program(slug='bruno', payload=_payload(program_id='bruno-2026-q1'))
        v2 = publish_program(slug='bruno', payload=_payload(program_id='bruno-2026-q1', weeks=6))

        v1.refresh_from_db()
        self.assertEqual(v2.version, 2)
        self.assertTrue(v2.is_active)
        self.assertFalse(v1.is_active)
        self.assertEqual(PublicWorkoutProgram.objects.filter(program_id='bruno-2026-q1').count(), 2)

    def test_database_rejects_two_active_rows_for_same_slug(self):
        # Pronto quando #2 da Onda A1: o banco, nao so o codigo, recusa.
        publish_program(slug='bruno', payload=_payload(program_id='bruno-2026-q1'))

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PublicWorkoutProgram.objects.create(
                    slug='bruno',
                    program_id='bruno-outro-programa',
                    program_label='Outro programa ativo pro mesmo slug',
                    started_on='2026-02-01',
                    weeks=4,
                    version=1,
                    is_active=True,
                    payload=_payload(program_id='bruno-outro-programa'),
                )

    def test_database_rejects_duplicate_program_id_version(self):
        with transaction.atomic():
            PublicWorkoutProgram.objects.create(
                slug='bruno', program_id='bruno-2026-q1', program_label='v1',
                started_on='2026-01-05', weeks=4, version=1, is_active=True,
                payload=_payload(program_id='bruno-2026-q1'),
            )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PublicWorkoutProgram.objects.create(
                    slug='bruno', program_id='bruno-2026-q1', program_label='v1 de novo',
                    started_on='2026-01-05', weeks=4, version=1, is_active=False,
                    payload=_payload(program_id='bruno-2026-q1'),
                )

    def test_invalid_payload_raises_and_creates_nothing(self):
        invalid = _payload(program_id='bruno-2026-q1')
        del invalid['weeks']

        with self.assertRaises(PayloadValidationError):
            publish_program(slug='bruno', payload=invalid)

        self.assertEqual(PublicWorkoutProgram.objects.count(), 0)

    def test_unknown_movement_is_created_as_pending_and_does_not_block_publish(self):
        payload = _payload(program_id='bruno-2026-q1')
        payload['days'][0]['blocks'][0]['movements'][0]['movement_slug'] = 'movimento-nunca-visto'
        payload['days'][0]['blocks'][0]['movements'][0]['reference_url'] = 'https://musclewiki.com/exercise/x'

        program = publish_program(slug='bruno', payload=payload)

        self.assertTrue(program.is_active)
        movement = PublicWorkoutMovement.objects.get(slug='movimento-nunca-visto')
        self.assertEqual(movement.status, 'pending')
        self.assertEqual(movement.modality, 'strength')
        self.assertEqual(movement.reference_url, 'https://musclewiki.com/exercise/x')

    def test_known_movement_is_not_touched(self):
        PublicWorkoutMovement.objects.create(
            slug='agachamento-livre', label_pt='Agachamento livre (revisado)',
            modality='crossfit', status='active', movement_pattern='squat',
        )

        publish_program(slug='bruno', payload=_payload(program_id='bruno-2026-q1'))

        movement = PublicWorkoutMovement.objects.get(slug='agachamento-livre')
        self.assertEqual(movement.label_pt, 'Agachamento livre (revisado)')
        self.assertEqual(movement.movement_pattern, 'squat')
        self.assertEqual(PublicWorkoutMovement.objects.filter(slug='agachamento-livre').count(), 1)

    def test_repeated_movement_slug_across_blocks_creates_only_one_catalog_row(self):
        payload = _payload(program_id='bruno-2026-q1')
        second_day = copy.deepcopy(payload['days'][0])
        second_day['day_id'] = 'qua'
        payload['days'].append(second_day)  # mesmo movement_slug nos dois dias

        publish_program(slug='bruno', payload=payload)

        self.assertEqual(PublicWorkoutMovement.objects.filter(slug='agachamento-livre').count(), 1)


class ServicesTenantBoundaryTests(TestCase):
    def test_services_module_never_imports_tenant_orm_models(self):
        # S1 (get_active_program) e publish_program rodam no schema public,
        # sem tenant nenhum — um import do ORM de TENANT_APPS aqui passaria
        # no teste (o conftest forca schema_context) e so quebraria em
        # producao (R2 do CORDA). Quem monta payload a partir de dado de
        # tenant resolve isso ANTES de chamar publish_program.
        #
        # Nao bloqueia `student_app.views.public_workout_views` — modulo de
        # view que roda no schema public de proposito (mesma exigencia:
        # "NENHUMA view aqui pode tocar modelo de TENANT_APPS", ver seu
        # docstring), so `PUBLIC_WORKOUT_LIBRARY` (dict Python, sem ORM).
        import ast
        import pathlib

        tenant_orm_modules = ('student_app.models', 'operations.model_definitions', 'operations.models')

        source = pathlib.Path('public_workouts/services.py').read_text(encoding='utf-8')
        tree = ast.parse(source, filename='public_workouts/services.py')
        offenders = []
        for node in ast.walk(tree):
            module = None
            if isinstance(node, ast.ImportFrom) and node.module:
                module = node.module
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(tenant_orm_modules):
                        offenders.append(alias.name)
            if module and module.startswith(tenant_orm_modules):
                offenders.append(module)

        self.assertEqual(offenders, [], f'public_workouts/services.py importando ORM de TENANT_APPS: {offenders}')


class ActivateProgramVersionTests(TestCase):
    def test_reverting_to_v1_does_not_create_a_new_row(self):
        publish_program(slug='bruno', payload=_payload(program_id='bruno-2026-q1'))
        publish_program(slug='bruno', payload=_payload(program_id='bruno-2026-q1', weeks=6))
        count_before = PublicWorkoutProgram.objects.count()

        activate_program_version(slug='bruno', program_id='bruno-2026-q1', version=1)

        self.assertEqual(PublicWorkoutProgram.objects.count(), count_before)
        self.assertEqual(get_active_program(slug='bruno')['weeks'], 4)

    def test_activating_v1_deactivates_v2(self):
        publish_program(slug='bruno', payload=_payload(program_id='bruno-2026-q1'))
        v2 = publish_program(slug='bruno', payload=_payload(program_id='bruno-2026-q1', weeks=6))

        activate_program_version(slug='bruno', program_id='bruno-2026-q1', version=1)

        v2.refresh_from_db()
        self.assertFalse(v2.is_active)


class ListProgramVersionsTests(TestCase):
    def test_returns_empty_list_when_never_published(self):
        self.assertEqual(list_program_versions(slug='bruno'), [])

    def test_returns_all_versions_most_recent_first(self):
        publish_program(slug='bruno', payload=_payload(program_id='bruno-2026-q1', weeks=4))
        publish_program(slug='bruno', payload=_payload(program_id='bruno-2026-q1', weeks=6))

        versions = list_program_versions(slug='bruno')

        self.assertEqual([v['version'] for v in versions], [2, 1])
        self.assertEqual(versions[0]['weeks'], 6)
        self.assertEqual(versions[1]['weeks'], 4)

    def test_reflects_which_version_is_active_after_reverting(self):
        publish_program(slug='bruno', payload=_payload(program_id='bruno-2026-q1'))
        publish_program(slug='bruno', payload=_payload(program_id='bruno-2026-q1', weeks=6))
        activate_program_version(slug='bruno', program_id='bruno-2026-q1', version=1)

        versions = list_program_versions(slug='bruno')

        by_version = {v['version']: v for v in versions}
        self.assertTrue(by_version[1]['is_active'])
        self.assertFalse(by_version[2]['is_active'])

    def test_does_not_leak_between_slugs(self):
        publish_program(slug='bruno', payload=_payload(program_id='bruno-2026-q1'))

        self.assertEqual(list_program_versions(slug='juliana'), [])

    def test_never_includes_the_raw_payload(self):
        publish_program(slug='bruno', payload=_payload(program_id='bruno-2026-q1'))

        versions = list_program_versions(slug='bruno')

        self.assertNotIn('payload', versions[0])
