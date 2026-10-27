from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time

from operations.models import ClassSession, ClassType, SessionStatus, WorkoutProgram, WorkoutTemplate, WorkoutTemplateBlock, WorkoutTemplateMovement
from student_app.models import SessionWorkout, SessionWorkoutBlock, SessionWorkoutMovement, SessionWorkoutStatus
from tests.workout_test_support import WorkoutFlowBaseTestCase
from operations.workout_templates import apply_persisted_workout_template


class DayApplyFlowTests(WorkoutFlowBaseTestCase):
    def setUp(self):
        super().setUp()
        self.template = WorkoutTemplate.objects.create(name='Base CrossFit', created_by=self.coach)
        block = WorkoutTemplateBlock.objects.create(template=self.template, title='Treino novo', kind='strength', sort_order=1)
        WorkoutTemplateMovement.objects.create(block=block, movement_slug='deadlift', movement_label='Deadlift', reps=8, sort_order=1)

    def apply(self, **overrides):
        data = dict(target_date=timezone.localdate().isoformat(), template_id=self.template.id, mode='replace_empty', class_type=ClassType.CROSS)
        data.update(overrides)
        return self.client.post(reverse('wod-day-apply'), data)

    def preview(self, **overrides):
        data = dict(target_date=timezone.localdate().isoformat(), template_id=self.template.id, mode='replace_empty', class_type=ClassType.CROSS)
        data.update(overrides)
        return self.client.post(reverse('wod-day-apply-preview'), data)

    def test_day_preview_shows_distinct_programs_without_mutation(self):
        first = WorkoutProgram.objects.create(slug='cross-a2-first', name='Cross A')
        second = WorkoutProgram.objects.create(slug='cross-a2-second', name='Cross B')
        self.session.workout_program = first
        self.session.save(update_fields=['workout_program'])
        other = ClassSession.objects.create(
            title='Cross B 18h', class_type=ClassType.CROSS,
            workout_program=second, coach=self.coach,
            scheduled_at=self.session.scheduled_at, duration_minutes=60, capacity=12,
            status=SessionStatus.COMPLETED,
        )
        response = self.preview()
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['mixed_programs'])
        self.assertEqual(payload['ready_count'], 2)
        self.assertEqual(payload['completed_count'], 1)
        self.assertEqual({row['session_id'] for row in payload['entries']}, {self.session.id, other.id})
        self.assertEqual(set(payload['programs']), {'Cross A', 'Cross B'})
        self.assertFalse(SessionWorkout.objects.exists())

    def test_program_preview_rejects_ambiguous_class_type_only_scope(self):
        first = WorkoutProgram.objects.create(slug='cross-explicit-a', name='Cross A')
        second = WorkoutProgram.objects.create(slug='cross-explicit-b', name='Cross B')
        self.session.workout_program = first
        self.session.save(update_fields=['workout_program'])
        other = ClassSession.objects.create(
            title='Cross B 18h', class_type=ClassType.CROSS,
            workout_program=second, coach=self.coach,
            scheduled_at=self.session.scheduled_at, duration_minutes=60, capacity=12,
        )

        response = self.client.post(reverse('wod-day-program-preview'), {
            'target_date': timezone.localdate().isoformat(),
            'template_id': self.template.id,
            'class_type': ClassType.CROSS,
            'mode': 'replace_empty',
        })

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload['code'], 'invalid_payload')
        self.assertIn('workout_program_id', payload['errors'])
        self.assertFalse(SessionWorkout.objects.exists())
        self.assertEqual(ClassSession.objects.filter(pk__in=(self.session.pk, other.pk)).count(), 2)

    def test_legacy_day_apply_keeps_class_type_scope_for_shared_programs(self):
        first = WorkoutProgram.objects.create(slug='cross-legacy-a', name='Cross Legado A')
        second = WorkoutProgram.objects.create(slug='cross-legacy-b', name='Cross Legado B')
        self.session.class_type = ClassType.CROSS
        self.session.workout_program = first
        self.session.save(update_fields=['class_type', 'workout_program'])
        other_program_session = ClassSession.objects.create(
            title='Cross Legado B', class_type=ClassType.CROSS,
            workout_program=second, coach=self.coach,
            scheduled_at=self.session.scheduled_at, duration_minutes=60, capacity=12,
        )

        response = self.apply()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['applied_count'], 2)
        self.assertTrue(SessionWorkout.objects.filter(session=self.session).exists())
        self.assertTrue(SessionWorkout.objects.filter(session=other_program_session).exists())

    def test_day_preview_preserves_existing_workout_and_coach_scope(self):
        self.create_existing()
        ClassSession.objects.create(
            title='Outro coach', class_type=ClassType.CROSS, coach=self.owner,
            scheduled_at=self.session.scheduled_at, duration_minutes=60, capacity=12,
        )
        response = self.preview()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['preserved_count'], 1)
        self.assertEqual(len(response.json()['entries']), 1)
        self.assertEqual(response.json()['entries'][0]['status'], 'preserved')
        self.assertEqual(self.preview(mode='overwrite').json()['ready_count'], 1)

    def test_day_preview_reuses_template_ownership_rule(self):
        self.template.created_by = self.owner
        self.template.save(update_fields=['created_by'])
        self.assertEqual(self.preview().status_code, 403)
        self.assertFalse(SessionWorkout.objects.exists())

    def create_existing(self, **overrides):
        data = dict(session=self.session, title='Original', coach_notes='Preservar estas notas', created_by=self.coach, version=4)
        data.update(overrides)
        workout = SessionWorkout.objects.create(**data)
        block = SessionWorkoutBlock.objects.create(workout=workout, title='Bloco original', kind='metcon', rounds=5, sort_order=1)
        movement = SessionWorkoutMovement.objects.create(block=block, movement_slug='push_up', movement_label='Flexão', reps_spec='10-8-6', sort_order=1)
        return workout, block, movement

    def undo(self, token):
        return self.client.post(reverse('wod-day-apply-undo'), {'undo_token': token})

    def test_day_apply_only_changes_selected_modality_and_coachs_own_active_sessions(self):
        neighbour = ClassSession.objects.create(title='HYROX', class_type=ClassType.HYROX, coach=self.coach, scheduled_at=self.session.scheduled_at, duration_minutes=60, capacity=12)
        other = ClassSession.objects.create(title='Outro coach', class_type=ClassType.CROSS, coach=self.owner, scheduled_at=self.session.scheduled_at, duration_minutes=60, capacity=12)
        canceled = ClassSession.objects.create(title='Cancelada', class_type=ClassType.CROSS, coach=self.coach, status=SessionStatus.CANCELED, scheduled_at=self.session.scheduled_at, duration_minutes=60, capacity=12)
        tomorrow = ClassSession.objects.create(title='Amanhã', class_type=ClassType.CROSS, coach=self.coach, scheduled_at=self.session.scheduled_at + timedelta(days=1), duration_minutes=60, capacity=12)
        response = self.apply()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['applied_count'], 1)
        self.assertTrue(SessionWorkout.objects.filter(session=self.session).exists())
        self.assertFalse(SessionWorkout.objects.filter(session__in=(neighbour, other, canceled, tomorrow)).exists())
        self.template.refresh_from_db()
        self.assertEqual(self.template.usage_count, 1)

    def test_manager_can_apply_day_template_but_cannot_use_individual_coach_editor(self):
        self.login_as_manager()

        apply_response = self.apply()

        self.assertEqual(apply_response.status_code, 200)
        self.assertEqual(apply_response.json()['applied_count'], 1)
        workout = SessionWorkout.objects.get(session=self.session)
        original_title = workout.title

        editor_response = self.client.post(
            reverse('coach-session-workout-editor', args=[self.session.id]),
            {'intent': 'save_workout', 'title': 'Manager tentou alterar pelo editor'},
        )

        self.assertIn(editor_response.status_code, (403, 404))
        workout.refresh_from_db()
        self.assertEqual(workout.title, original_title)

    def test_owner_can_apply_day_template(self):
        self.login_as_owner()

        response = self.apply()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['applied_count'], 1)
        self.assertTrue(SessionWorkout.objects.filter(session=self.session).exists())

    def test_day_apply_requires_explicit_modality(self):
        response = self.apply(class_type='')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SessionWorkout.objects.exists())

    def test_coach_cannot_apply_another_authors_template(self):
        self.template.created_by = self.owner
        self.template.save()
        response = self.apply()
        self.assertEqual(response.status_code, 403)
        self.assertFalse(SessionWorkout.objects.exists())

    def test_overwrite_undo_restores_original_content_and_advances_revision(self):
        workout, block, movement = self.create_existing()
        response = self.apply(mode='overwrite')
        self.assertEqual(response.json()['applied_count'], 1)
        workout.refresh_from_db()
        applied_version = workout.version
        self.assertEqual(workout.title, 'Base CrossFit')
        result = self.undo(response.json()['undo_token'])
        self.assertTrue(result.json()['ok'])
        workout.refresh_from_db()
        self.assertEqual(workout.title, 'Original')
        self.assertEqual(workout.coach_notes, 'Preservar estas notas')
        self.assertGreater(workout.version, applied_version)
        block.refresh_from_db()
        movement.refresh_from_db()
        self.assertEqual(block.rounds, 5)
        self.assertEqual(movement.reps_spec, '10-8-6')
        self.assertFalse(self.undo(response.json()['undo_token']).json()['ok'])

    def test_undo_cannot_be_used_by_a_different_actor(self):
        response = self.apply()
        self.login_as_owner()
        result = self.undo(response.json()['undo_token'])
        self.assertFalse(result.json()['ok'])
        self.assertTrue(SessionWorkout.objects.filter(session=self.session).exists())

    def test_undo_preserves_edits_made_after_apply(self):
        response = self.apply()
        workout = SessionWorkout.objects.get(session=self.session)
        movement = workout.blocks.get().movements.get()
        movement.notes = 'Edição posterior que deve ser preservada'
        movement.save()
        result = self.undo(response.json()['undo_token'])
        self.assertFalse(result.json()['ok'])
        movement.refresh_from_db()
        self.assertEqual(movement.notes, 'Edição posterior que deve ser preservada')

    def test_overwrite_preserves_published_pending_and_rejected_workouts(self):
        for status in (
            SessionWorkoutStatus.PUBLISHED,
            SessionWorkoutStatus.PENDING_APPROVAL,
            SessionWorkoutStatus.REJECTED,
        ):
            with self.subTest(status=str(status)):
                SessionWorkout.objects.all().delete()
                workout, block, movement = self.create_existing(status=status)
                response = self.apply(mode='overwrite')
                self.assertEqual(response.json()['applied_count'], 0)
                workout.refresh_from_db()
                self.assertEqual(workout.status, status)
                self.assertTrue(SessionWorkoutMovement.objects.filter(pk=movement.pk).exists())

    def test_undo_removes_only_workouts_created_by_the_apply(self):
        response = self.apply()
        result = self.undo(response.json()['undo_token'])
        self.assertEqual(result.json()['undone_count'], 1)
        self.assertFalse(SessionWorkout.objects.filter(session=self.session).exists())

    def test_undo_token_expires_after_sixty_seconds_without_mutating_workout(self):
        response = self.apply()
        token = response.json()['undo_token']
        workout = SessionWorkout.objects.get(session=self.session)

        with freeze_time(timezone.now() + timedelta(seconds=61)):
            result = self.undo(token)

        self.assertFalse(result.json()['ok'])
        self.assertIn('expirado', result.json()['reason'])
        self.assertTrue(SessionWorkout.objects.filter(pk=workout.pk).exists())

    def test_daily_editor_and_preview_are_limited_to_coachs_own_session(self):
        other = ClassSession.objects.create(title='Outro coach', coach=self.owner, scheduled_at=self.session.scheduled_at, duration_minutes=60, capacity=12)
        url = reverse('coach-session-workout-editor', args=[other.id])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, {'intent': 'save_workout', 'title': 'Inválido'}).status_code, 404)
        self.assertEqual(self.client.get(reverse('workout-prescription-preview', args=[other.id])).status_code, 404)
        self.assertFalse(SessionWorkout.objects.filter(session=other).exists())

    def test_daily_editor_has_movement_suggestions_without_students_or_rm(self):
        response = self.client.get(reverse('coach-session-workout-editor', args=[self.session.id]))
        catalog = response.context['movement_catalog']
        entry = next(item for item in catalog if item['slug'] == 'deadlift')
        self.assertEqual(entry['label'], 'Deadlift')
        self.assertFalse(entry['has_rm_data'])

    def test_daily_editor_uses_html_decimal_format_when_editing_load(self):
        workout, block, movement = self.create_existing()
        movement.load_type = 'fixed_kg'
        movement.load_value = Decimal('40.50')
        movement.save()
        response = self.client.get(reverse('coach-session-workout-editor', args=[self.session.id]))
        self.assertContains(response, 'name="load_value" min="0" step="0.01" value="40.50"')

    def test_undo_does_not_partially_undo_a_batch_after_one_workout_changes(self):
        second = ClassSession.objects.create(title='Outra aula própria', class_type=ClassType.CROSS, coach=self.coach, scheduled_at=self.session.scheduled_at, duration_minutes=60, capacity=12)
        response = self.apply()
        self.assertEqual(response.json()['applied_count'], 2)
        SessionWorkout.objects.filter(session=second).update(title='Editado depois')
        self.assertFalse(self.undo(response.json()['undo_token']).json()['ok'])
        self.assertEqual(SessionWorkout.objects.count(), 2)

    def test_failed_apply_rolls_back_the_whole_batch(self):
        second = ClassSession.objects.create(title='Outra aula própria', class_type=ClassType.CROSS, coach=self.coach, scheduled_at=self.session.scheduled_at, duration_minutes=60, capacity=12)
        def apply_one(**kwargs):
            if kwargs['target_session'].pk == second.pk:
                return {'ok': False, 'reason': 'falha simulada'}
            return apply_persisted_workout_template(**kwargs)
        with patch('operations.services.wod_day_apply_executor.apply_persisted_workout_template', side_effect=apply_one):
            response = self.apply()
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SessionWorkout.objects.exists())
        self.template.refresh_from_db()
        self.assertEqual(self.template.usage_count, 0)
