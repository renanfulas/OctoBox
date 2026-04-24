from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse

from auditing.models import AuditEvent
from operations.models import Attendance, AttendanceStatus, ClassSession, WorkoutTemplate, WorkoutTemplateBlock, WorkoutTemplateMovement
from student_app.models import (
    SessionWorkout,
    SessionWorkoutBlock,
    SessionWorkoutMovement,
    SessionWorkoutRevision,
    SessionWorkoutRevisionEvent,
    SessionWorkoutStatus,
    StudentExerciseMax,
    WorkoutLoadType,
)
from tests.workout_test_support import WorkoutFlowBaseTestCase
from operations.models import WorkoutApprovalPolicySetting
from operations.workout_approval_policy import resolve_workout_approval_policy, update_workout_approval_policy_setting
from operations.workout_support import should_require_workout_approval


class CoachWorkoutEditorFlowTests(WorkoutFlowBaseTestCase):
    def _editor_url(self, session=None):
        target_session = session or self.session
        return reverse('coach-session-workout-editor', args=[target_session.id])

    def _create_workout(self, **overrides):
        payload = {
            'session': self.session,
            'title': 'WOD base',
            'coach_notes': 'Base',
            'status': SessionWorkoutStatus.DRAFT,
            'created_by': self.coach,
        }
        payload.update(overrides)
        return SessionWorkout.objects.create(**payload)

    def _create_block(self, workout, **overrides):
        payload = {
            'workout': workout,
            'title': 'Forca inicial',
            'kind': 'strength',
            'notes': 'Notas antigas',
            'sort_order': 1,
        }
        payload.update(overrides)
        return SessionWorkoutBlock.objects.create(**payload)

    def _create_movement(self, block, **overrides):
        payload = {
            'block': block,
            'movement_slug': 'deadlift',
            'movement_label': 'Deadlift',
            'sets': 5,
            'reps': 5,
            'load_type': WorkoutLoadType.FREE,
            'sort_order': 1,
        }
        payload.update(overrides)
        return SessionWorkoutMovement.objects.create(**payload)

    def test_coach_workspace_shows_wod_action_for_session(self):
        response = self.client.get(reverse('coach-workspace'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Criar WOD')
        self.assertContains(response, self._editor_url())

    def test_workout_editor_home_lists_session_cards(self):
        response = self.client.get(reverse('workout-editor-home'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('workout-planner'))

    def test_owner_can_access_editor_home_and_session_editor(self):
        self.login_as_owner()

        home_response = self.client.get(reverse('workout-editor-home'))
        editor_response = self.client.get(self._editor_url())

        self.assertEqual(home_response.status_code, 302)
        self.assertEqual(editor_response.status_code, 200)
        self.assertContains(editor_response, 'Aprovacoes')

    def test_coach_can_create_submit_block_and_movement(self):
        editor_url = self._editor_url()

        response = self.client.post(
            editor_url,
            data={
                'intent': 'save_workout',
                'title': 'Forca + Metcon',
                'coach_notes': 'Hoje o foco e ritmo constante.',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        workout = SessionWorkout.objects.get(session=self.session)
        self.assertEqual(workout.title, 'Forca + Metcon')
        self.assertEqual(workout.status, SessionWorkoutStatus.DRAFT)

        response = self.client.post(
            editor_url,
            data={
                'intent': 'add_block',
                'title': 'Forca principal',
                'kind': 'strength',
                'notes': 'Suba carga com tecnica.',
                'sort_order': 1,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        block = SessionWorkoutBlock.objects.get(workout=workout)
        self.assertEqual(block.title, 'Forca principal')

        response = self.client.post(
            editor_url,
            data={
                'intent': 'add_movement',
                'block_id': block.id,
                'movement_slug': 'deadlift',
                'movement_label': 'Deadlift',
                'sets': 5,
                'reps': 10,
                'load_type': WorkoutLoadType.PERCENTAGE_OF_RM,
                'load_value': Decimal('70.00'),
                'notes': 'Controle a lombar.',
                'sort_order': 1,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        movement = SessionWorkoutMovement.objects.get(block=block)
        self.assertEqual(movement.movement_label, 'Deadlift')
        self.assertEqual(movement.load_type, WorkoutLoadType.PERCENTAGE_OF_RM)
        self.assertEqual(movement.load_value, Decimal('70.00'))

        response = self.client.post(
            editor_url,
            data={'intent': 'submit_for_approval'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        workout.refresh_from_db()
        self.assertEqual(workout.status, SessionWorkoutStatus.PENDING_APPROVAL)
        self.assertEqual(workout.submitted_by, self.coach)
        self.assertTrue(
            SessionWorkoutRevision.objects.filter(
                workout=workout,
                event=SessionWorkoutRevisionEvent.SUBMITTED,
                version=workout.version,
            ).exists()
        )
        self.assertTrue(AuditEvent.objects.filter(action='session_workout_submitted_for_approval', target_id=str(workout.id)).exists())
        submitted_revision = SessionWorkoutRevision.objects.get(
            workout=workout,
            event=SessionWorkoutRevisionEvent.SUBMITTED,
            version=workout.version,
        )
        self.assertEqual(submitted_revision.snapshot['approval_policy'], 'strict')
        self.assertFalse(submitted_revision.snapshot['bypass_approval'])
        self.assertEqual(submitted_revision.snapshot['policy_decision_label'], 'Enviado para aprovacao')

    def test_coach_can_update_block_and_movement_inline(self):
        workout = self._create_workout()
        block = self._create_block(workout)
        movement = self._create_movement(block)
        editor_url = self._editor_url()

        response = self.client.post(
            editor_url,
            data={
                'intent': 'update_block',
                'block_id': block.id,
                'title': 'Forca revisada',
                'kind': 'skill',
                'notes': 'Notas novas',
                'sort_order': 2,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        block.refresh_from_db()
        self.assertEqual(block.title, 'Forca revisada')
        self.assertEqual(block.kind, 'skill')
        self.assertEqual(block.sort_order, 2)

        response = self.client.post(
            editor_url,
            data={
                'intent': 'update_movement',
                'movement_id': movement.id,
                'block_id': block.id,
                'movement_slug': 'power-clean',
                'movement_label': 'Power Clean',
                'sets': 6,
                'reps': 3,
                'load_type': WorkoutLoadType.FIXED_KG,
                'load_value': Decimal('52.50'),
                'notes': 'Explodir no quadril.',
                'sort_order': 2,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        movement.refresh_from_db()
        self.assertEqual(movement.movement_slug, 'power-clean')
        self.assertEqual(movement.movement_label, 'Power Clean')
        self.assertEqual(movement.load_type, WorkoutLoadType.FIXED_KG)
        self.assertEqual(movement.load_value, Decimal('52.50'))
        self.assertEqual(movement.sort_order, 2)

    def test_coach_can_duplicate_workout_to_another_session_as_draft(self):
        target_session = ClassSession.objects.create(
            title='Cross 18h',
            coach=self.coach,
            scheduled_at=self.session.scheduled_at + timedelta(days=1),
            duration_minutes=60,
            capacity=16,
        )
        workout = self._create_workout(
            title='WOD origem',
            coach_notes='Base de duplicacao.',
            status=SessionWorkoutStatus.PUBLISHED,
            version=4,
        )
        block = self._create_block(
            workout,
            title='Metcon final',
            kind='metcon',
            notes='Manter ritmo.',
        )
        self._create_movement(
            block,
            movement_slug='row',
            movement_label='Row',
            sets=4,
            reps=500,
            load_type=WorkoutLoadType.FREE,
        )
        editor_url = self._editor_url()

        response = self.client.post(
            editor_url,
            data={
                'intent': 'duplicate_workout',
                'target_session_id': target_session.id,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        duplicated_workout = SessionWorkout.objects.get(session=target_session)
        self.assertEqual(duplicated_workout.title, 'WOD origem')
        self.assertEqual(duplicated_workout.status, SessionWorkoutStatus.DRAFT)
        self.assertEqual(duplicated_workout.version, 1)
        self.assertEqual(duplicated_workout.blocks.count(), 1)
        duplicated_block = duplicated_workout.blocks.first()
        self.assertEqual(duplicated_block.movements.count(), 1)
        duplicated_movement = duplicated_block.movements.first()
        self.assertEqual(duplicated_movement.movement_label, 'Row')
        self.assertTrue(
            SessionWorkoutRevision.objects.filter(
                workout=duplicated_workout,
                event=SessionWorkoutRevisionEvent.DUPLICATED,
                version=1,
            ).exists()
        )
        self.assertTrue(AuditEvent.objects.filter(action='session_workout_duplicated', target_id=str(duplicated_workout.id)).exists())

    def test_coach_can_apply_quick_template_to_current_session_when_empty(self):
        source_session = ClassSession.objects.create(
            title='Cross template',
            coach=self.coach,
            scheduled_at=self.session.scheduled_at - timedelta(days=1),
            duration_minutes=60,
            capacity=16,
        )
        source_workout = SessionWorkout.objects.create(
            session=source_session,
            title='Template rapido base',
            coach_notes='Base reaproveitavel.',
            status=SessionWorkoutStatus.PUBLISHED,
            created_by=self.coach,
            approved_by=self.owner,
            version=2,
        )
        source_block = SessionWorkoutBlock.objects.create(
            workout=source_workout,
            title='Forca template',
            kind='strength',
            sort_order=1,
        )
        SessionWorkoutMovement.objects.create(
            block=source_block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sets=5,
            reps=3,
            load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            load_value=Decimal('70.00'),
            sort_order=1,
        )

        response = self.client.post(
            self._editor_url(),
            data={
                'intent': 'apply_quick_template',
                'source_workout_id': source_workout.id,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        target_workout = SessionWorkout.objects.get(session=self.session)
        self.assertEqual(target_workout.title, 'Template rapido base')
        self.assertEqual(target_workout.status, SessionWorkoutStatus.DRAFT)
        self.assertEqual(target_workout.blocks.count(), 1)
        self.assertEqual(target_workout.blocks.first().movements.count(), 1)
        self.assertContains(response, 'Template rapido aplicado como base do WOD desta aula.')

    def test_coach_editor_renders_quick_template_preview_panel(self):
        source_session = ClassSession.objects.create(
            title='Cross template',
            coach=self.coach,
            scheduled_at=self.session.scheduled_at - timedelta(days=1),
            duration_minutes=60,
            capacity=16,
        )
        source_workout = SessionWorkout.objects.create(
            session=source_session,
            title='Template rapido base',
            coach_notes='Base reaproveitavel.',
            status=SessionWorkoutStatus.PUBLISHED,
            created_by=self.coach,
            approved_by=self.owner,
            version=2,
        )
        source_block = SessionWorkoutBlock.objects.create(
            workout=source_workout,
            title='Forca template',
            kind='strength',
            sort_order=1,
        )
        SessionWorkoutMovement.objects.create(
            block=source_block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sets=5,
            reps=3,
            load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            load_value=Decimal('70.00'),
            sort_order=1,
        )

        response = self.client.get(self._editor_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Resumo do template')
        self.assertContains(response, 'wod-quick-template-options')
        self.assertContains(response, 'wod_quick_template_preview.js')
        self.assertContains(response, '1 bloco(s)')
        self.assertContains(response, '1 movimento(s)')
        self.assertContains(response, 'Use o resumo para confirmar a base antes de aplicar o template rapido na aula.')

    def test_quick_template_is_blocked_with_richer_message_when_session_already_has_blocks(self):
        existing_workout = self._create_workout(title='WOD existente')
        existing_block = self._create_block(existing_workout, title='Bloco atual')
        self._create_movement(existing_block, movement_slug='row', movement_label='Row')

        source_session = ClassSession.objects.create(
            title='Cross template',
            coach=self.coach,
            scheduled_at=self.session.scheduled_at - timedelta(days=1),
            duration_minutes=60,
            capacity=16,
        )
        source_workout = SessionWorkout.objects.create(
            session=source_session,
            title='Template rapido base',
            coach_notes='Base reaproveitavel.',
            status=SessionWorkoutStatus.PUBLISHED,
            created_by=self.coach,
            approved_by=self.owner,
            version=2,
        )
        source_block = SessionWorkoutBlock.objects.create(
            workout=source_workout,
            title='Forca template',
            kind='strength',
            sort_order=1,
        )
        SessionWorkoutMovement.objects.create(
            block=source_block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sets=5,
            reps=3,
            load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            load_value=Decimal('70.00'),
            sort_order=1,
        )

        response = self.client.post(
            self._editor_url(),
            data={
                'intent': 'apply_quick_template',
                'source_workout_id': source_workout.id,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A aula ja tem montagem parcial')
        self.assertContains(response, '1 bloco(s), 1 movimento(s)')
        self.assertContains(response, 'Nao aplicamos template por cima')

    def test_coach_can_apply_stored_template_to_current_session_when_empty(self):
        template = WorkoutTemplate.objects.create(
            name='Template persistente base',
            created_by=self.coach,
            is_active=True,
        )
        template_block = WorkoutTemplateBlock.objects.create(
            template=template,
            title='Forca template',
            kind='strength',
            sort_order=1,
        )
        WorkoutTemplateMovement.objects.create(
            block=template_block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sets=5,
            reps=3,
            load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            load_value=Decimal('70.00'),
            sort_order=1,
        )

        response = self.client.post(
            self._editor_url(),
            data={
                'intent': 'apply_stored_template',
                'template_id': template.id,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        target_workout = SessionWorkout.objects.get(session=self.session)
        self.assertEqual(target_workout.title, 'Template persistente base')
        self.assertEqual(target_workout.status, SessionWorkoutStatus.DRAFT)
        self.assertEqual(target_workout.blocks.count(), 1)
        self.assertEqual(target_workout.blocks.first().movements.count(), 1)
        self.assertContains(response, 'Template salvo aplicado como base do WOD desta aula.')

    def test_coach_can_save_current_wod_as_stored_template(self):
        workout = self._create_workout(title='WOD para virar template')
        block = self._create_block(workout, title='Forca base')
        self._create_movement(
            block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sets=5,
            reps=3,
            load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            load_value=Decimal('70.00'),
        )

        response = self.client.post(
            self._editor_url(),
            data={
                'intent': 'create_stored_template',
                'template_name': 'Template criado do editor',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        template = WorkoutTemplate.objects.get(name='Template criado do editor')
        self.assertEqual(template.source_workout, workout)
        self.assertEqual(template.blocks.count(), 1)
        self.assertEqual(template.blocks.first().movements.count(), 1)
        self.assertContains(response, 'Template salvo')
        self.assertContains(response, 'Template criado do editor')
        self.assertContains(response, 'criado a partir deste WOD')

    @override_settings(WOD_APPROVAL_POLICY='trusted_template')
    @patch('operations.workout_support.emit_wod_policy_decision')
    def test_trusted_stored_template_can_publish_directly_by_policy(self, emit_policy_decision):
        template = WorkoutTemplate.objects.create(
            name='Template confiavel base',
            created_by=self.coach,
            is_active=True,
            is_trusted=True,
        )
        template_block = WorkoutTemplateBlock.objects.create(
            template=template,
            title='Forca template',
            kind='strength',
            sort_order=1,
        )
        WorkoutTemplateMovement.objects.create(
            block=template_block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sets=5,
            reps=3,
            load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            load_value=Decimal('70.00'),
            sort_order=1,
        )

        response = self.client.post(
            self._editor_url(),
            data={
                'intent': 'apply_stored_template',
                'template_id': template.id,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        target_workout = SessionWorkout.objects.get(session=self.session)
        self.assertEqual(target_workout.status, SessionWorkoutStatus.PUBLISHED)
        self.assertEqual(target_workout.approved_by, self.coach)
        published_revision = SessionWorkoutRevision.objects.get(
            workout=target_workout,
            event=SessionWorkoutRevisionEvent.PUBLISHED,
            version=target_workout.version,
        )
        self.assertEqual(published_revision.snapshot['approval_policy'], 'trusted_template')
        self.assertTrue(published_revision.snapshot['bypass_approval'])
        self.assertEqual(published_revision.snapshot['policy_decision_label'], 'Publicado direto pela politica')
        self.assertTrue(
            AuditEvent.objects.filter(
                action='session_workout_published_directly',
                target_id=str(target_workout.id),
                metadata__approval_policy='trusted_template',
                metadata__bypass_approval=True,
            ).exists()
        )
        emit_policy_decision.assert_called_once()
        self.assertContains(response, 'Template salvo confiavel aplicado e publicado direto pela politica ativa.')

    @override_settings(WOD_APPROVAL_POLICY='trusted_template')
    def test_untrusted_stored_template_stays_as_draft_after_apply(self):
        template = WorkoutTemplate.objects.create(
            name='Template em revisao',
            created_by=self.coach,
            is_active=True,
            is_trusted=False,
        )
        template_block = WorkoutTemplateBlock.objects.create(
            template=template,
            title='Forca template',
            kind='strength',
            sort_order=1,
        )
        WorkoutTemplateMovement.objects.create(
            block=template_block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sets=5,
            reps=3,
            load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            load_value=Decimal('70.00'),
            sort_order=1,
        )

        response = self.client.post(
            self._editor_url(),
            data={
                'intent': 'apply_stored_template',
                'template_id': template.id,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        target_workout = SessionWorkout.objects.get(session=self.session)
        self.assertEqual(target_workout.status, SessionWorkoutStatus.DRAFT)
        self.assertContains(response, 'Template salvo aplicado como base do WOD desta aula.')

    def test_coach_editor_renders_stored_template_preview_panel(self):
        template = WorkoutTemplate.objects.create(
            name='Template persistente base',
            created_by=self.coach,
            is_active=True,
        )
        template_block = WorkoutTemplateBlock.objects.create(
            template=template,
            title='Forca template',
            kind='strength',
            sort_order=1,
        )
        WorkoutTemplateMovement.objects.create(
            block=template_block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sets=5,
            reps=3,
            load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            load_value=Decimal('70.00'),
            sort_order=1,
        )

        response = self.client.get(self._editor_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Resumo do template salvo')
        self.assertContains(response, 'wod-stored-template-options')
        self.assertContains(response, 'wod_stored_template_preview.js')
        self.assertContains(response, '1 bloco(s)')
        self.assertContains(response, '1 movimento(s)')

    def test_stored_template_is_blocked_with_richer_message_when_session_already_has_blocks(self):
        existing_workout = self._create_workout(title='WOD existente')
        existing_block = self._create_block(existing_workout, title='Bloco atual')
        self._create_movement(existing_block, movement_slug='row', movement_label='Row')

        template = WorkoutTemplate.objects.create(
            name='Template persistente base',
            created_by=self.coach,
            is_active=True,
        )
        template_block = WorkoutTemplateBlock.objects.create(
            template=template,
            title='Forca template',
            kind='strength',
            sort_order=1,
        )
        WorkoutTemplateMovement.objects.create(
            block=template_block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sets=5,
            reps=3,
            load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            load_value=Decimal('70.00'),
            sort_order=1,
        )

        response = self.client.post(
            self._editor_url(),
            data={
                'intent': 'apply_stored_template',
                'template_id': template.id,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A aula ja tem montagem parcial')
        self.assertContains(response, '1 bloco(s), 1 movimento(s)')
        self.assertContains(response, 'Nao aplicamos template salvo por cima')

    def test_template_management_lists_and_toggles_persisted_templates(self):
        template = WorkoutTemplate.objects.create(
            name='Template persistente base',
            created_by=self.coach,
            is_active=True,
            usage_count=3,
        )
        WorkoutTemplateBlock.objects.create(
            template=template,
            title='Forca template',
            kind='strength',
            sort_order=1,
        )

        response = self.client.get(reverse('workout-template-management'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Templates persistentes de WOD.')
        self.assertContains(response, 'Template persistente base')
        self.assertContains(response, '3 uso(s)')
        self.assertContains(response, 'Ativo')

        response = self.client.post(
            reverse('workout-template-toggle-active', args=[template.id]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        template.refresh_from_db()
        self.assertFalse(template.is_active)
        self.assertContains(response, 'inativado')

    def test_template_management_updates_metadata_and_featured_state(self):
        template = WorkoutTemplate.objects.create(
            name='Template persistente base',
            description='Descricao antiga',
            created_by=self.coach,
            is_active=True,
            is_featured=False,
        )

        response = self.client.post(
            reverse('workout-template-update-metadata', args=[template.id]),
            data={
                'name': 'Template refinado',
                'description': 'Descricao nova',
                'is_featured': '1',
                'is_trusted': '1',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        template.refresh_from_db()
        self.assertEqual(template.name, 'Template refinado')
        self.assertEqual(template.description, 'Descricao nova')
        self.assertTrue(template.is_featured)
        self.assertTrue(template.is_trusted)
        self.assertContains(response, 'Metadados do template')
        self.assertContains(response, 'Template refinado')
        self.assertContains(response, 'atualizados')

    def test_template_management_updates_block_and_movement(self):
        template = WorkoutTemplate.objects.create(
            name='Template persistente base',
            created_by=self.coach,
            is_active=True,
        )
        block = WorkoutTemplateBlock.objects.create(
            template=template,
            title='Forca template',
            kind='strength',
            sort_order=1,
        )
        movement = WorkoutTemplateMovement.objects.create(
            block=block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sets=5,
            reps=3,
            load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            load_value=Decimal('70.00'),
            sort_order=1,
        )

        response = self.client.post(
            reverse('workout-template-update-block', args=[block.id]),
            data={
                'block_id': block.id,
                'title': 'Forca refinada',
                'kind': 'skill',
                'notes': 'Notas novas',
                'sort_order': 2,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        block.refresh_from_db()
        self.assertEqual(block.title, 'Forca refinada')
        self.assertEqual(block.kind, 'skill')
        self.assertEqual(block.sort_order, 2)

        response = self.client.post(
            reverse('workout-template-update-movement', args=[movement.id]),
            data={
                'movement_id': movement.id,
                'movement_slug': 'power-clean',
                'movement_label': 'Power Clean',
                'sets': 6,
                'reps': 2,
                'load_type': WorkoutLoadType.FIXED_KG,
                'load_value': '52.50',
                'notes': 'Explodir no quadril.',
                'sort_order': 2,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        movement.refresh_from_db()
        self.assertEqual(movement.movement_slug, 'power-clean')
        self.assertEqual(movement.movement_label, 'Power Clean')
        self.assertEqual(movement.load_type, WorkoutLoadType.FIXED_KG)
        self.assertEqual(movement.sort_order, 2)

    def test_template_management_can_create_and_remove_block_and_movement(self):
        template = WorkoutTemplate.objects.create(
            name='Template persistente base',
            created_by=self.coach,
            is_active=True,
        )

        response = self.client.post(
            reverse('workout-template-create-block', args=[template.id]),
            data={
                'title': 'Metcon final',
                'kind': 'metcon',
                'notes': 'Ritmo alto.',
                'sort_order': 1,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        block = template.blocks.get(title='Metcon final')
        self.assertEqual(block.kind, 'metcon')

        response = self.client.post(
            reverse('workout-template-create-movement', args=[block.id]),
            data={
                'movement_slug': 'row',
                'movement_label': 'Row',
                'sets': 4,
                'reps': 500,
                'load_type': WorkoutLoadType.FREE,
                'sort_order': 1,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        movement = block.movements.get(movement_slug='row')
        self.assertEqual(movement.movement_label, 'Row')

        response = self.client.post(
            reverse('workout-template-delete-movement', args=[movement.id]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(WorkoutTemplateMovement.objects.filter(id=movement.id).exists())

        response = self.client.post(
            reverse('workout-template-delete-block', args=[block.id]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(WorkoutTemplateBlock.objects.filter(id=block.id).exists())

    def test_template_management_can_duplicate_and_delete_template(self):
        template = WorkoutTemplate.objects.create(
            name='Template persistente base',
            description='Descricao base',
            created_by=self.coach,
            is_active=True,
            is_featured=True,
        )
        block = WorkoutTemplateBlock.objects.create(
            template=template,
            title='Primeiro bloco',
            kind='strength',
            sort_order=1,
        )
        WorkoutTemplateMovement.objects.create(
            block=block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sets=5,
            reps=3,
            load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            load_value=Decimal('70.00'),
            sort_order=1,
        )

        response = self.client.post(
            reverse('workout-template-duplicate', args=[template.id]),
            data={'name': 'Template persistente base copia'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        duplicated = WorkoutTemplate.objects.get(name='Template persistente base copia')
        self.assertEqual(duplicated.description, 'Descricao base')
        self.assertFalse(duplicated.is_featured)
        self.assertEqual(duplicated.blocks.count(), 1)
        self.assertEqual(duplicated.blocks.first().movements.count(), 1)
        self.assertContains(response, 'duplicado com sucesso')

        response = self.client.post(
            reverse('workout-template-delete', args=[duplicated.id]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(WorkoutTemplate.objects.filter(id=duplicated.id).exists())
        self.assertContains(response, 'removido do catalogo')

    def test_template_management_supports_search_and_featured_filters(self):
        WorkoutTemplate.objects.create(
            name='Forca base',
            created_by=self.coach,
            is_active=True,
            is_featured=True,
        )
        WorkoutTemplate.objects.create(
            name='Metcon livre',
            created_by=self.coach,
            is_active=False,
            is_featured=False,
        )

        response = self.client.get(reverse('workout-template-management'), data={'q': 'Forca', 'featured': '1'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Catalogo')
        self.assertContains(response, 'Busca: Forca')
        self.assertContains(response, 'Forca base')
        self.assertNotContains(response, 'Metcon livre')
        self.assertContains(response, 'So destaque')

    def test_template_management_can_move_block_and_movement_up_and_down(self):
        template = WorkoutTemplate.objects.create(
            name='Template persistente base',
            created_by=self.coach,
            is_active=True,
        )
        first_block = WorkoutTemplateBlock.objects.create(
            template=template,
            title='Primeiro bloco',
            kind='warmup',
            sort_order=1,
        )
        second_block = WorkoutTemplateBlock.objects.create(
            template=template,
            title='Segundo bloco',
            kind='strength',
            sort_order=2,
        )
        first_movement = WorkoutTemplateMovement.objects.create(
            block=second_block,
            movement_slug='row',
            movement_label='Row',
            sort_order=1,
            load_type=WorkoutLoadType.FREE,
        )
        second_movement = WorkoutTemplateMovement.objects.create(
            block=second_block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sort_order=2,
            load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            load_value=Decimal('70.00'),
        )

        response = self.client.post(
            reverse('workout-template-move-block', args=[second_block.id, 'up']),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        first_block.refresh_from_db()
        second_block.refresh_from_db()
        self.assertEqual(second_block.sort_order, 1)
        self.assertEqual(first_block.sort_order, 2)

        response = self.client.post(
            reverse('workout-template-move-movement', args=[second_movement.id, 'up']),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        first_movement.refresh_from_db()
        second_movement.refresh_from_db()
        self.assertEqual(second_movement.sort_order, 1)
        self.assertEqual(first_movement.sort_order, 2)

    def test_coach_editor_shows_rm_preview_for_booked_students(self):
        workout = self._create_workout()
        block = self._create_block(workout, title='Forca guiada')
        self._create_movement(
            block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sets=5,
            reps=3,
            load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            load_value=Decimal('70.00'),
        )
        Attendance.objects.create(student=self.student_alpha, session=self.session, status=AttendanceStatus.BOOKED)
        Attendance.objects.create(student=self.student_beta, session=self.session, status=AttendanceStatus.CHECKED_IN)
        StudentExerciseMax.objects.create(
            student=self.student_alpha,
            exercise_slug='deadlift',
            exercise_label='Deadlift',
            one_rep_max_kg=Decimal('100.00'),
        )

        response = self.client.get(self._editor_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Preview do impacto nos alunos')
        self.assertContains(response, '2 aluno(s) no radar')
        self.assertContains(response, '1/2 alunos com RM registrado')
        self.assertContains(response, 'Aluno Alpha')
        self.assertContains(response, '70.00 kg')
        self.assertContains(response, 'Aluno Beta')
        self.assertContains(response, 'Sem RM registrado')

    def test_coach_editor_exposes_local_movement_catalog_for_autocomplete(self):
        Attendance.objects.create(student=self.student_alpha, session=self.session, status=AttendanceStatus.BOOKED)
        StudentExerciseMax.objects.create(
            student=self.student_alpha,
            exercise_slug='deadlift',
            exercise_label='Deadlift',
            one_rep_max_kg=Decimal('100.00'),
        )

        response = self.client.get(self._editor_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'wod-movement-catalog')
        self.assertContains(response, 'wod-movement-catalog-slugs')
        self.assertContains(response, 'wod-movement-catalog-labels')
        self.assertContains(response, 'deadlift')
        self.assertContains(response, 'Deadlift')
        self.assertContains(response, '"has_rm_data": true')
        self.assertContains(response, 'wod-movement-rm-roster')

    def test_coach_editor_renders_local_prescription_preview_panel(self):
        workout = self._create_workout()
        block = self._create_block(workout, title='Forca guiada')
        self._create_movement(
            block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sets=5,
            reps=3,
            load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            load_value=Decimal('70.00'),
        )

        response = self.client.get(self._editor_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Preview local da prescricao')
        self.assertContains(response, 'wod_prescription_preview.js')
        self.assertContains(response, 'Sugestao automatica: %RM')
        self.assertContains(response, 'data-wod-prescription-students')
        self.assertContains(response, 'coach-wod-prescription-preview__label')
        self.assertContains(response, 'coach-wod-prescription-preview__context')

    def test_prescription_preview_endpoint_returns_backend_payload(self):
        Attendance.objects.create(student=self.student_alpha, session=self.session, status=AttendanceStatus.BOOKED)
        StudentExerciseMax.objects.create(
            student=self.student_alpha,
            exercise_slug='deadlift',
            exercise_label='Deadlift',
            one_rep_max_kg=Decimal('100.00'),
        )

        response = self.client.get(
            reverse('workout-prescription-preview', args=[self.session.id]),
            data={
                'movement_slug': 'deadlift',
                'load_type': WorkoutLoadType.PERCENTAGE_OF_RM,
                'load_value': '70.00',
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['summary'], '1/1 alunos com RM pronto para este movimento.')
        self.assertEqual(payload['students'][0]['name'], 'Aluno Alpha')
        self.assertEqual(payload['students'][0]['rounded_load_label'], '70.00 kg')

    def test_coach_editor_explains_when_no_percentage_rm_is_configured(self):
        workout = self._create_workout()
        block = self._create_block(workout, title='Metcon livre')
        self._create_movement(
            block,
            movement_slug='row',
            movement_label='Row',
            sets=4,
            reps=500,
            load_type=WorkoutLoadType.FREE,
        )
        Attendance.objects.create(student=self.student_alpha, session=self.session, status=AttendanceStatus.BOOKED)

        response = self.client.get(self._editor_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1 aluno(s) no radar')
        self.assertContains(
            response,
            'Ainda nao existe movimento com % do RM neste WOD. Quando voce usar esse tipo de carga, mostramos aqui o impacto na turma.',
        )


class WorkoutApprovalPolicyPersistenceTests(WorkoutFlowBaseTestCase):
    def test_can_persist_policy_for_box_and_resolve_it(self):
        setting = update_workout_approval_policy_setting(
            actor=self.owner,
            approval_policy='trusted_template',
            preferred_box_id=77,
        )

        self.assertIsNotNone(setting)
        self.assertEqual(setting.box_id, 77)
        self.assertEqual(setting.approval_policy, 'trusted_template')
        self.assertEqual(
            resolve_workout_approval_policy(preferred_box_id=77),
            'trusted_template',
        )

    @patch('operations.workout_approval_policy.resolve_actor_box_id', return_value=88)
    def test_owner_can_update_box_policy_from_management_ui(self, _resolve_box_id):
        self.login_as_owner()

        response = self.client.post(
            reverse('workout-approval-policy-update'),
            data={'approval_policy': 'coach_autonomy'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        setting = WorkoutApprovalPolicySetting.objects.get(box_id=88)
        self.assertEqual(setting.approval_policy, 'coach_autonomy')
        self.assertContains(response, 'Politica de aprovacao do box atualizada com sucesso.')

class WorkoutApprovalPolicyTests(WorkoutFlowBaseTestCase):
    def test_should_require_workout_approval_respects_strict_policy(self):
        workout = SimpleNamespace(session=SimpleNamespace(box=SimpleNamespace(wod_approval_policy='strict')))

        self.assertTrue(
            should_require_workout_approval(
                workout=workout,
                coach=SimpleNamespace(is_trusted_author=True),
                source='manual',
            )
        )

    def test_should_require_workout_approval_respects_trusted_template_policy(self):
        workout = SimpleNamespace(session=SimpleNamespace(box=SimpleNamespace(wod_approval_policy='trusted_template')))

        self.assertFalse(
            should_require_workout_approval(
                workout=workout,
                coach=SimpleNamespace(is_trusted_author=False),
                source='template',
                source_template=SimpleNamespace(is_trusted=True),
            )
        )
        self.assertTrue(
            should_require_workout_approval(
                workout=workout,
                coach=SimpleNamespace(is_trusted_author=False),
                source='template',
                source_template=SimpleNamespace(is_trusted=False),
            )
        )

    def test_should_require_workout_approval_respects_coach_autonomy_policy(self):
        workout = SimpleNamespace(session=SimpleNamespace(box=SimpleNamespace(wod_approval_policy='coach_autonomy')))

        self.assertFalse(
            should_require_workout_approval(
                workout=workout,
                coach=SimpleNamespace(is_trusted_author=True),
                source='manual',
            )
        )
        self.assertTrue(
            should_require_workout_approval(
                workout=workout,
                coach=SimpleNamespace(is_trusted_author=False),
                source='manual',
            )
        )
