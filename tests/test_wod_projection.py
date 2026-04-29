from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from operations.models import ClassSession, ClassType
from operations.services.wod_projection import build_projection_preview, project_plan_to_sessions
from student_app.models import SessionWorkout, SessionWorkoutStatus, WeeklyWodPlan


class WodProjectionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='projection-wave5',
            email='projection-wave5@example.com',
            password='senha-forte-123',
        )
        monday = timezone.make_aware(timezone.datetime(2026, 4, 20, 12, 0))
        tuesday = timezone.make_aware(timezone.datetime(2026, 4, 21, 18, 0))
        self.cross_session = ClassSession.objects.create(
            title='Cross 12h',
            scheduled_at=monday,
            duration_minutes=60,
            capacity=14,
            class_type=ClassType.CROSS,
        )
        self.mobility_session = ClassSession.objects.create(
            title='Mobilidade 18h',
            scheduled_at=tuesday,
            duration_minutes=60,
            capacity=14,
            class_type=ClassType.MOBILITY,
        )
        self.plan = WeeklyWodPlan.objects.create(
            week_start=date(2026, 4, 20),
            label='Semana de teste',
            status='confirmed',
            created_by=self.user,
            parsed_payload={
                'week_label': None,
                'parse_warnings': [],
                'days': [
                    {
                        'weekday': 0,
                        'weekday_label': 'Segunda',
                        'blocks': [
                            {
                                'kind': 'warmup',
                                'title': 'Aquecimento',
                                'notes': '',
                                'movements': [
                                    {
                                        'movement_slug': 'lunge',
                                        'movement_label_raw': '10 lunges',
                                        'reps_spec': '10',
                                        'load_spec': '',
                                    }
                                ],
                            },
                            {
                                'kind': 'metcon',
                                'title': 'WOD',
                                'notes': '',
                                'movements': [
                                    {
                                        'movement_slug': 'push_press',
                                        'movement_label_raw': '50 push press 40/25',
                                        'reps_spec': '50',
                                        'load_spec': '40/25',
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        'weekday': 1,
                        'weekday_label': 'Terca',
                        'blocks': [
                            {
                                'kind': 'mobility',
                                'title': 'Mobilidade',
                                'notes': '',
                                'movements': [],
                            },
                            {
                                'kind': 'metcon',
                                'title': 'WOD pesado',
                                'notes': '',
                                'movements': [],
                            },
                        ],
                    },
                ],
            },
        )

    def test_preview_exposes_collisions_compatibility_and_load_warnings(self):
        SessionWorkout.objects.create(
            session=self.cross_session,
            title='Existente',
            status=SessionWorkoutStatus.DRAFT,
            created_by=self.user,
        )

        preview = build_projection_preview(
            weekly_plan=self.plan,
            target_week_start=date(2026, 4, 20),
            class_types=[ClassType.CROSS, ClassType.MOBILITY],
        )

        self.assertEqual(preview['totals']['sessions_found'], 2)
        statuses = {entry['session_id']: entry['status'] for entry in preview['entries']}
        self.assertEqual(statuses[self.cross_session.id], 'skip_existing_workout')
        self.assertEqual(statuses[self.mobility_session.id], 'ready')
        mobility_entry = next(entry for entry in preview['entries'] if entry['session_id'] == self.mobility_session.id)
        self.assertEqual(len(mobility_entry['discarded_blocks']), 1)
        self.assertIn('metcon', mobility_entry['discarded_blocks'][0]['kind'])

    def test_projection_creates_batch_and_draft_workout(self):
        preview = build_projection_preview(
            weekly_plan=self.plan,
            target_week_start=date(2026, 4, 20),
            class_types=[ClassType.CROSS],
        )
        self.assertEqual(preview['totals']['sessions_creatable'], 1)

        batch, created_preview = project_plan_to_sessions(
            weekly_plan=self.plan,
            target_week_start=date(2026, 4, 20),
            class_types=[ClassType.CROSS],
            actor=self.user,
        )

        self.assertEqual(batch.sessions_created, 1)
        workout = SessionWorkout.objects.get(session=self.cross_session)
        self.assertEqual(workout.status, SessionWorkoutStatus.DRAFT)
        self.assertEqual(workout.replication_batch, batch)
        self.assertEqual(workout.blocks.count(), 2)
        projected_movement = workout.blocks.order_by('sort_order').last().movements.first()
        self.assertEqual(projected_movement.load_type, 'free')
        self.assertEqual(projected_movement.notes, '40/25')
        self.assertEqual(created_preview['collision_policy'], 'skip_existing_workout')

    def test_cross_filter_includes_legacy_other_sessions(self):
        self.cross_session.class_type = ClassType.OTHER
        self.cross_session.save(update_fields=['class_type'])

        preview = build_projection_preview(
            weekly_plan=self.plan,
            target_week_start=date(2026, 4, 20),
            class_types=[ClassType.CROSS],
        )

        self.assertEqual(preview['totals']['sessions_found'], 1)
        self.assertEqual(preview['totals']['sessions_creatable'], 1)
        self.assertEqual(preview['totals']['sessions_skipped'], 0)
        self.assertEqual(preview['entries'][0]['session_id'], self.cross_session.id)
        self.assertEqual(preview['entries'][0]['status'], 'ready')
