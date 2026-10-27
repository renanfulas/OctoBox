"""
Testes de arquivamento reversível de templates de WOD.

Cobre o serviço workout_template_archive e as views HTTP de
archive, archive-all e restore.
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from operations.models import WorkoutTemplate
from operations.services.workout_template_archive import (
    archive_all_templates,
    archive_template,
    build_archived_template_list,
    delete_expired_archives,
    restore_template,
)
from tests.workout_test_support import WorkoutFlowBaseTestCase


def _make_template(name, *, created_by, archived_at=None, archived_by=None):
    return WorkoutTemplate.objects.create(
        name=name,
        created_by=created_by,
        archived_at=archived_at,
        archived_by=archived_by,
    )


class ArchiveTemplateServiceTests(WorkoutFlowBaseTestCase):
    def test_archive_sets_archived_at_and_archived_by(self):
        template = _make_template('Base força', created_by=self.coach)
        archive_template(template=template, actor=self.coach)

        template.refresh_from_db()
        self.assertIsNotNone(template.archived_at)
        self.assertEqual(template.archived_by, self.coach)
        self.assertFalse(template.is_active)

    def test_restore_clears_archive_fields_and_reactivates(self):
        template = _make_template(
            'Metcon longo',
            created_by=self.coach,
            archived_at=timezone.now(),
            archived_by=self.coach,
        )
        template.is_active = False
        template.save(update_fields=['is_active'])

        restore_template(template=template)

        template.refresh_from_db()
        self.assertIsNone(template.archived_at)
        self.assertIsNone(template.archived_by)
        self.assertTrue(template.is_active)

    def test_archive_all_templates_archives_active_ones(self):
        _make_template('T1', created_by=self.coach)
        _make_template('T2', created_by=self.coach)
        already_archived = _make_template(
            'T3',
            created_by=self.coach,
            archived_at=timezone.now(),
            archived_by=self.coach,
        )

        count = archive_all_templates(box_id=None, actor=self.owner)

        self.assertEqual(count, 2)
        already_archived.refresh_from_db()
        self.assertIsNotNone(already_archived.archived_at)

    def test_delete_expired_archives_removes_old_templates(self):
        old_archived = _make_template('Velho', created_by=self.coach)
        old_archived.archived_at = timezone.now() - timedelta(days=31)
        old_archived.save(update_fields=['archived_at'])

        recent_archived = _make_template('Recente', created_by=self.coach)
        recent_archived.archived_at = timezone.now() - timedelta(days=10)
        recent_archived.save(update_fields=['archived_at'])

        deleted = delete_expired_archives()

        self.assertEqual(deleted, 1)
        self.assertFalse(WorkoutTemplate.objects.filter(pk=old_archived.pk).exists())
        self.assertTrue(WorkoutTemplate.objects.filter(pk=recent_archived.pk).exists())

    def test_build_archived_template_list_returns_correct_shape(self):
        # Arquivado há 5 dias -> retenção de 30 dias -> ~25 dias restantes.
        # Usamos tolerância de 1 dia porque o serviço chama timezone.now()
        # depois do setup; truncamento de .days pode oscilar entre 24 e 25.
        t = _make_template('Para listar', created_by=self.coach)
        t.archived_at = timezone.now() - timedelta(days=5)
        t.archived_by = self.coach
        t.save(update_fields=['archived_at', 'archived_by'])

        result = build_archived_template_list(box_id=None)

        # Filtra apenas o template criado por este teste para não depender
        # de outros templates arquivados que outros testes possam ter
        # deixado no banco (AP8: independência de ordem).
        my_items = [item for item in result if item['id'] == t.id]
        self.assertEqual(len(my_items), 1)
        item = my_items[0]
        self.assertEqual(item['name'], 'Para listar')
        self.assertIn(item['days_left'], (24, 25))
        self.assertFalse(item['expires_soon'])
        self.assertIn('archived_at_label', item)
        self.assertIn('archived_by_label', item)

    def test_build_archived_template_list_marks_expiring_soon(self):
        t = _make_template('Expirando', created_by=self.coach)
        t.archived_at = timezone.now() - timedelta(days=25)
        t.archived_by = self.coach
        t.save(update_fields=['archived_at', 'archived_by'])

        result = build_archived_template_list(box_id=None)

        # Filtra apenas o template criado por este teste para não depender
        # do estado global do banco entre execuções (AP8).
        my_items = [item for item in result if item['id'] == t.id]
        self.assertEqual(len(my_items), 1)
        self.assertTrue(my_items[0]['expires_soon'])


class ArchiveTemplateViewTests(WorkoutFlowBaseTestCase):
    def test_coach_can_archive_individual_template(self):
        template = _make_template('Teste arquivar', created_by=self.coach)
        self.login_as_coach()

        response = self.client.post(
            reverse('workout-template-archive', kwargs={'template_id': template.id}),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        template.refresh_from_db()
        self.assertIsNotNone(template.archived_at)

    def test_coach_cannot_archive_another_authors_template(self):
        template = _make_template('Template de outro autor', created_by=self.owner)
        self.login_as_coach()

        response = self.client.post(
            reverse('workout-template-archive', kwargs={'template_id': template.id}),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        template.refresh_from_db()
        self.assertIsNone(template.archived_at)
        self.assertTrue(template.is_active)
        self.assertContains(response, 'Coach so pode gerenciar templates criados por ele.')

    def test_cannot_archive_already_archived_template(self):
        template = _make_template('Já arquivado', created_by=self.coach)
        template.archived_at = timezone.now()
        template.save(update_fields=['archived_at'])
        self.login_as_coach()

        response = self.client.post(
            reverse('workout-template-archive', kwargs={'template_id': template.id}),
        )

        self.assertEqual(response.status_code, 404)

    def test_coach_can_restore_archived_template(self):
        template = _make_template('Para restaurar', created_by=self.coach)
        template.archived_at = timezone.now()
        template.archived_by = self.coach
        template.is_active = False
        template.save(update_fields=['archived_at', 'archived_by', 'is_active'])
        self.login_as_coach()

        response = self.client.post(
            reverse('workout-template-restore', kwargs={'template_id': template.id}),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        template.refresh_from_db()
        self.assertIsNone(template.archived_at)
        self.assertTrue(template.is_active)

    def test_coach_cannot_restore_another_authors_template(self):
        template = _make_template(
            'Template arquivado de outro autor',
            created_by=self.owner,
            archived_at=timezone.now(),
            archived_by=self.owner,
        )
        template.is_active = False
        template.save(update_fields=['is_active'])
        archived_at = template.archived_at
        self.login_as_coach()

        response = self.client.post(
            reverse('workout-template-restore', kwargs={'template_id': template.id}),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        template.refresh_from_db()
        self.assertEqual(template.archived_at, archived_at)
        self.assertFalse(template.is_active)
        self.assertContains(response, 'Coach so pode gerenciar templates criados por ele.')

    def test_owner_can_archive_all_with_correct_confirmation(self):
        _make_template('Bulk1', created_by=self.coach)
        _make_template('Bulk2', created_by=self.coach)
        self.login_as_owner()

        response = self.client.post(
            reverse('workout-template-archive-all'),
            data={'confirmation': 'ARQUIVAR'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(WorkoutTemplate.objects.filter(archived_at__isnull=True).count(), 0)

    def test_archive_all_rejects_wrong_confirmation(self):
        _make_template('NaoArquivar', created_by=self.coach)
        self.login_as_owner()

        response = self.client.post(
            reverse('workout-template-archive-all'),
            data={'confirmation': 'deletar'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(WorkoutTemplate.objects.filter(archived_at__isnull=True).exists())

    def test_archive_all_forbidden_for_coach(self):
        self.login_as_coach()

        response = self.client.post(
            reverse('workout-template-archive-all'),
            data={'confirmation': 'ARQUIVAR'},
        )

        self.assertIn(response.status_code, [302, 403])
        self.assertFalse(
            WorkoutTemplate.objects.filter(archived_at__isnull=False).exists()
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.requires_postgres
def test_template_routes_cannot_resolve_rows_from_another_tenant_schema(test_tenant):
    """Template, block and movement PKs present only in B stay invisible to requests in A."""
    from uuid import uuid4

    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group
    from django.core.management import call_command
    from django.db import connection
    from django.test import Client
    from django_tenants.utils import schema_context

    from access.roles import ROLE_OWNER
    from operations.models import WorkoutTemplateBlock, WorkoutTemplateMovement

    call_command('bootstrap_roles')
    actor = get_user_model().objects.create_user(
        username=f'template-schema-owner-{uuid4().hex}',
        password='test-password',
    )
    actor.groups.add(Group.objects.get(name=ROLE_OWNER))
    template_id = 2_000_000_000
    archived_template_id = template_id + 1
    block_id = template_id + 2
    movement_id = template_id + 3
    other_schema = f'box_tpl_{uuid4().hex[:12]}'
    with connection.cursor() as cursor:
        cursor.execute(f'CREATE SCHEMA "{other_schema}"')

    try:
        call_command('migrate_schemas', schema=other_schema, verbosity=0, interactive=False)
        with schema_context(other_schema):
            foreign_template = WorkoutTemplate.objects.create(
                id=template_id,
                name='Template privado do box B',
                created_by=actor,
            )
            foreign_archived_template = WorkoutTemplate.objects.create(
                id=archived_template_id,
                name='Template arquivado do box B',
                created_by=actor,
                archived_at=timezone.now(),
                archived_by=actor,
                is_active=False,
            )
            foreign_block = WorkoutTemplateBlock.objects.create(
                id=block_id,
                template=foreign_template,
                title='Bloco privado do box B',
                kind='strength',
                sort_order=1,
            )
            foreign_movement = WorkoutTemplateMovement.objects.create(
                id=movement_id,
                block=foreign_block,
                movement_slug='deadlift',
                movement_label='Deadlift privado do box B',
                sets=3,
                reps=5,
                sort_order=1,
            )

        with schema_context(test_tenant.schema_name):
            assert not WorkoutTemplate.objects.filter(pk=template_id).exists()

        client = Client()
        client.force_login(actor)
        cases = [
            ('workout-template-duplicate', {'template_id': template_id}, {'name': 'Cópia indevida'}),
            ('workout-template-delete', {'template_id': template_id}, {}),
            ('workout-template-toggle-active', {'template_id': template_id}, {}),
            ('workout-template-toggle-featured', {'template_id': template_id}, {}),
            ('workout-template-update-metadata', {'template_id': template_id}, {
                'name': 'Alterado', 'description': 'Alterada', 'is_featured': '1', 'is_trusted': '1',
            }),
            ('workout-template-archive', {'template_id': template_id}, {}),
            ('workout-template-restore', {'template_id': archived_template_id}, {}),
            ('workout-template-create-block', {'template_id': template_id}, {
                'title': 'Novo bloco', 'kind': 'strength', 'notes': '', 'sort_order': 2,
            }),
            ('workout-template-update-block', {'block_id': block_id}, {
                'title': 'Alterado', 'kind': 'metcon', 'notes': '', 'sort_order': 2,
            }),
            ('workout-template-delete-block', {'block_id': block_id}, {}),
            ('workout-template-move-block', {'block_id': block_id, 'direction': 'down'}, {}),
            ('workout-template-create-movement', {'block_id': block_id}, {
                'movement_slug': 'row', 'movement_label': 'Row', 'sets': 1, 'reps': 10,
                'load_type': 'free', 'sort_order': 2,
            }),
            ('workout-template-update-movement', {'movement_id': movement_id}, {
                'movement_slug': 'power-clean', 'movement_label': 'Power Clean',
                'sets': 4, 'reps': 2, 'load_type': 'fixed_kg', 'load_value': '60',
                'notes': '', 'sort_order': 2,
            }),
            ('workout-template-delete-movement', {'movement_id': movement_id}, {}),
            ('workout-template-move-movement', {'movement_id': movement_id, 'direction': 'down'}, {}),
        ]
        for route_name, route_kwargs, data in cases:
            response = client.post(reverse(route_name, kwargs=route_kwargs), data=data)
            assert response.status_code == 404, route_name

        response = client.post(
            reverse('workout-template-archive-all'),
            data={'confirmation': 'ARQUIVAR'},
        )
        assert response.status_code == 302

        with schema_context(other_schema):
            foreign_template.refresh_from_db()
            foreign_archived_template.refresh_from_db()
            foreign_block.refresh_from_db()
            foreign_movement.refresh_from_db()
            assert foreign_template.archived_at is None
            assert foreign_template.is_active is True
            assert foreign_template.name == 'Template privado do box B'
            assert foreign_archived_template.archived_at is not None
            assert foreign_archived_template.is_active is False
            assert foreign_block.title == 'Bloco privado do box B'
            assert foreign_block.sort_order == 1
            assert foreign_movement.movement_label == 'Deadlift privado do box B'
            assert foreign_movement.sort_order == 1
    finally:
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{other_schema}" CASCADE')
