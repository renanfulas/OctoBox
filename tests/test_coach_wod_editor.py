from datetime import timedelta
from decimal import Decimal

from django.urls import reverse

from auditing.models import AuditEvent
from operations.models import Attendance, AttendanceStatus, ClassSession
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
