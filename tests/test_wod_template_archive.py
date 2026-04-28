"""
Testes de arquivamento reversível de templates de WOD.

Cobre o serviço workout_template_archive e as views HTTP de
archive, archive-all e restore.
"""

from datetime import timedelta

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
        t = _make_template('Para listar', created_by=self.coach)
        t.archived_at = timezone.now() - timedelta(days=5)
        t.archived_by = self.coach
        t.save(update_fields=['archived_at', 'archived_by'])

        result = build_archived_template_list(box_id=None)

        self.assertEqual(len(result), 1)
        item = result[0]
        self.assertEqual(item['id'], t.id)
        self.assertEqual(item['name'], 'Para listar')
        self.assertEqual(item['days_left'], 24)
        self.assertFalse(item['expires_soon'])

    def test_build_archived_template_list_marks_expiring_soon(self):
        t = _make_template('Expirando', created_by=self.coach)
        t.archived_at = timezone.now() - timedelta(days=25)
        t.archived_by = self.coach
        t.save(update_fields=['archived_at', 'archived_by'])

        result = build_archived_template_list(box_id=None)

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]['expires_soon'])


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
