from datetime import datetime

from django.test import TestCase
from django.utils import timezone

from catalog.form_definitions.class_grid_forms import ClassScheduleRecurringForm, ClassSessionQuickEditForm
from operations.application.commands import ClassScheduleCreateCommand
from operations.infrastructure.django_class_grid import DjangoClassGridWriter
from operations.infrastructure.django_class_grid_sessions import DjangoClassGridSessionStore
from operations.models import ClassSession, ClassType, WorkoutProgram
from operations.workout_program_catalog import ensure_default_workout_programs
from student_app.models import SessionWorkout


class ClassGridModalityRoutingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_default_workout_programs()
        cls.crossfit = WorkoutProgram.objects.get(slug='crossfit')
        cls.hyrox = WorkoutProgram.objects.get(slug='hyrox')

    def _schedule_form(self, *, workout_program=''):
        return ClassScheduleRecurringForm(data={
            'title': 'Aula 19h',
            'workout_program': str(workout_program),
            'start_date': '01/10/2026',
            'end_date': '01/10/2026',
            'weekdays': ['3'],
            'start_time': '19:00',
            'sequence_count': '0',
            'duration_minutes': '60',
            'capacity': '20',
        })

    def test_new_recurring_schedule_requires_a_visible_explicit_program(self):
        form = self._schedule_form()

        self.assertTrue(form.fields['workout_program'].required)
        self.assertIn('Escolha a trilha', form.fields['workout_program'].help_text)
        self.assertFalse(form.is_valid())
        self.assertIn('workout_program', form.errors)

    def test_schedule_form_accepts_hyrox_independent_of_class_title(self):
        form = self._schedule_form(workout_program=self.hyrox.pk)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['workout_program'], self.hyrox)

    def test_same_name_and_time_are_distinct_when_program_differs(self):
        scheduled_at = timezone.make_aware(datetime(2026, 10, 1, 19, 0))
        ClassSession.objects.create(
            title='Aula 19h', scheduled_at=scheduled_at, duration_minutes=60,
            capacity=20, class_type=ClassType.HYROX, workout_program=self.hyrox,
        )
        store = DjangoClassGridSessionStore()

        crossfit_existing = store.find_existing_scheduled_ats(
            title='Aula 19h', workout_program_id=self.crossfit.pk, scheduled_ats=[scheduled_at],
        )
        hyrox_existing = store.find_existing_scheduled_ats(
            title='Aula 19h', workout_program_id=self.hyrox.pk, scheduled_ats=[scheduled_at],
        )

        self.assertEqual(crossfit_existing, frozenset())
        self.assertEqual(hyrox_existing, frozenset({scheduled_at}))

    def test_duplicate_of_same_program_still_matches_existing_schedule(self):
        scheduled_at = timezone.make_aware(datetime(2026, 10, 1, 19, 0))
        ClassSession.objects.create(
            title='Aula 19h', scheduled_at=scheduled_at, duration_minutes=60,
            capacity=20, class_type=ClassType.CROSS, workout_program=self.crossfit,
        )

        existing = DjangoClassGridSessionStore().find_existing_scheduled_ats(
            title='Aula 19h', workout_program_id=self.crossfit.pk, scheduled_ats=[scheduled_at],
        )

        self.assertEqual(existing, frozenset({scheduled_at}))

    def test_session_with_workout_cannot_be_reclassified(self):
        session = ClassSession.objects.create(
            title='Aula 19h', scheduled_at=timezone.make_aware(datetime(2026, 10, 1, 19, 0)),
            duration_minutes=60, capacity=20, class_type=ClassType.CROSS,
            workout_program=self.crossfit,
        )
        SessionWorkout.objects.create(session=session)
        form = ClassSessionQuickEditForm(instance=session, data={
            'title': session.title,
            'workout_program': str(self.hyrox.pk),
            'coach': '',
            'start_time': '19:00',
            'duration_minutes': '60',
            'capacity': '20',
            'status': session.status,
            'notes': '',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('workout_program', form.errors)
        self.assertIn('WOD associado', str(form.errors['workout_program']))

    def test_writer_rejects_missing_program_even_when_called_without_form(self):
        command = ClassScheduleCreateCommand(
            actor_id=None, title='Aula', coach_id=None, start_date=datetime(2026, 10, 1).date(),
            end_date=datetime(2026, 10, 1).date(), anchor_date=None, interval_days=None,
            weekdays=(3,), start_time=datetime(2026, 10, 1, 19).time(), sequence_count=0,
            duration_minutes=60, capacity=20, status='scheduled', notes='', skip_existing=True,
        )
        writer = DjangoClassGridWriter(clock=None, coach_resolver=None, session_store=None)

        with self.assertRaisesMessage(ValueError, 'Escolha a modalidade'):
            writer.create_schedule(command)
