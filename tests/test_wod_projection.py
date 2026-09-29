from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from operations.models import ClassSession, ClassType, SessionStatus, WorkoutProgram
from operations.services.wod_projection import (
    _summarize_load_projection,
    build_projection_preview,
    project_plan_to_sessions,
)
from student_app.models import ReplicationBatch, SessionWorkout, SessionWorkoutStatus, WeeklyWodPlan


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
                                'timecap_min': 12,
                                'rounds': 3,
                                'score_type': 'for_time',
                                'format_spec': '21/15/9',
                                'movements': [
                                    {
                                        'movement_slug': 'push_press',
                                        'movement_label_raw': '50 push press 40/25',
                                        'reps_spec': '50',
                                        'load_spec': '40/25',
                                        'is_scaled_alternative': True,
                                        'notes': 'Carga por categoria.',
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

    def test_distribution_revalidates_if_a_target_becomes_occupied_after_preview(self):
        second_cross_session = ClassSession.objects.create(
            title='Cross 13h',
            scheduled_at=self.cross_session.scheduled_at + timedelta(hours=1),
            duration_minutes=60,
            capacity=14,
            class_type=ClassType.CROSS,
        )
        preview_before_confirmation = build_projection_preview(
            weekly_plan=self.plan,
            target_week_start=date(2026, 4, 20),
            class_types=[ClassType.CROSS],
        )
        self.assertEqual(preview_before_confirmation['totals']['sessions_creatable'], 2)

        # Another operator fills the first destination after the coach sees
        # the preview but before they confirm distribution.
        existing_workout = SessionWorkout.objects.create(
            session=self.cross_session,
            title='WOD salvo por outra pessoa',
            status=SessionWorkoutStatus.DRAFT,
            created_by=self.user,
        )

        batch, refreshed_preview = project_plan_to_sessions(
            weekly_plan=self.plan,
            target_week_start=date(2026, 4, 20),
            class_types=[ClassType.CROSS],
            actor=self.user,
        )

        statuses = {entry['session_id']: entry['status'] for entry in refreshed_preview['entries']}
        self.assertEqual(statuses[self.cross_session.id], 'skip_existing_workout')
        self.assertEqual(statuses[second_cross_session.id], 'ready')
        self.assertEqual(refreshed_preview['totals']['sessions_creatable'], 1)
        self.assertEqual(batch.sessions_targeted, 2)
        self.assertEqual(batch.sessions_created, 1)
        self.assertEqual(SessionWorkout.objects.get(session=self.cross_session).id, existing_workout.id)
        self.assertEqual(SessionWorkout.objects.filter(session=second_cross_session).count(), 1)

    def test_load_projection_preserves_pair_and_personalizes_percent_rm(self):
        paired_type, paired_value, paired_note = _summarize_load_projection({'load_spec': '40/25 kg'})
        rm_type, rm_value, rm_note = _summarize_load_projection({'load_spec': '65% RM'})

        self.assertEqual(paired_type, 'free')
        self.assertIsNone(paired_value)
        self.assertEqual(paired_note, '')
        self.assertEqual(rm_type, 'percentage_of_rm')
        self.assertEqual(rm_value, Decimal('65'))
        self.assertEqual(rm_note, '')

    def test_projection_creates_batch_and_submits_workout_for_approval(self):
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
        self.assertEqual(workout.status, SessionWorkoutStatus.PENDING_APPROVAL)
        self.assertEqual(workout.submitted_by, self.user)
        self.assertEqual(workout.replication_batch, batch)
        self.assertEqual(workout.blocks.count(), 2)
        projected_movement = workout.blocks.order_by('sort_order').last().movements.first()
        self.assertEqual(projected_movement.load_type, 'free')
        self.assertEqual(projected_movement.load_spec, '40/25')
        self.assertEqual(projected_movement.reps_spec, '50')
        self.assertTrue(projected_movement.is_scaled_alternative)
        self.assertEqual(projected_movement.notes, 'Carga por categoria.')
        projected_block = projected_movement.block
        self.assertEqual(projected_block.timecap_min, 12)
        self.assertEqual(projected_block.rounds, 3)
        self.assertEqual(projected_block.score_type, 'for_time')
        self.assertEqual(projected_block.format_spec, '21/15/9')
        self.assertFalse(workout.is_normalized)
        self.assertEqual(workout.structured_payload['source'], 'weekly_smart_paste')
        self.assertEqual(created_preview['collision_policy'], 'skip_existing_workout')
        self.assertEqual(created_preview['totals']['sessions_pending_approval'], 1)

        with self.assertRaisesMessage(ValidationError, 'Nenhuma aula nova esta pronta'):
            project_plan_to_sessions(
                weekly_plan=self.plan,
                target_week_start=date(2026, 4, 20),
                class_types=[ClassType.CROSS],
                actor=self.user,
            )

        self.assertEqual(ReplicationBatch.objects.filter(weekly_plan=self.plan).count(), 1)
        self.assertEqual(SessionWorkout.objects.filter(session=self.cross_session).count(), 1)

    def test_same_idempotency_key_replays_the_committed_distribution(self):
        request_key = uuid4()
        kwargs = {
            'weekly_plan': self.plan,
            'target_week_start': date(2026, 4, 20),
            'class_types': [ClassType.CROSS],
            'actor': self.user,
            'idempotency_key': request_key,
        }

        original_batch, _ = project_plan_to_sessions(**kwargs)
        replayed_batch, replayed_preview = project_plan_to_sessions(**kwargs)

        self.assertEqual(replayed_batch.pk, original_batch.pk)
        self.assertTrue(replayed_preview['idempotent_replay'])
        self.assertEqual(replayed_preview['totals']['sessions_pending_approval'], 1)
        self.assertEqual(ReplicationBatch.objects.filter(weekly_plan=self.plan).count(), 1)
        self.assertEqual(SessionWorkout.objects.filter(session=self.cross_session).count(), 1)

    def test_idempotency_key_cannot_be_reused_for_another_target_week(self):
        request_key = uuid4()
        project_plan_to_sessions(
            weekly_plan=self.plan,
            target_week_start=date(2026, 4, 20),
            class_types=[ClassType.CROSS],
            actor=self.user,
            idempotency_key=request_key,
        )

        with self.assertRaisesMessage(ValidationError, 'já foi usada para outra semana'):
            project_plan_to_sessions(
                weekly_plan=self.plan,
                target_week_start=date(2026, 4, 27),
                class_types=[ClassType.CROSS],
                actor=self.user,
                idempotency_key=request_key,
            )

        self.assertEqual(ReplicationBatch.objects.filter(weekly_plan=self.plan).count(), 1)

    def test_failure_on_later_destination_rolls_back_the_whole_distribution_batch(self):
        second_session = ClassSession.objects.create(
            title='Cross 14h',
            scheduled_at=timezone.make_aware(timezone.datetime(2026, 4, 20, 14, 0)),
            duration_minutes=60,
            capacity=14,
            class_type=ClassType.CROSS,
        )

        with patch(
            'operations.services.wod_projection.route_workout_submission',
            side_effect=[
                {'status': 'pending_approval'},
                ValidationError('Falha simulada ao submeter o segundo destino.'),
            ],
        ) as submit_workout:
            with self.assertRaisesMessage(ValidationError, 'Falha simulada ao submeter o segundo destino.'):
                project_plan_to_sessions(
                    weekly_plan=self.plan,
                    target_week_start=date(2026, 4, 20),
                    class_types=[ClassType.CROSS],
                    actor=self.user,
                )

        self.assertEqual(submit_workout.call_count, 2)
        self.assertFalse(ReplicationBatch.objects.filter(weekly_plan=self.plan).exists())
        self.assertFalse(SessionWorkout.objects.filter(session__in=[self.cross_session, second_session]).exists())

    def test_database_rejects_a_second_workout_for_the_same_session(self):
        SessionWorkout.objects.create(
            session=self.cross_session,
            title='Primeiro WOD',
            status=SessionWorkoutStatus.DRAFT,
            created_by=self.user,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SessionWorkout.objects.create(
                    session=self.cross_session,
                    title='Duplicação concorrente',
                    status=SessionWorkoutStatus.DRAFT,
                    created_by=self.user,
                )

        self.assertEqual(SessionWorkout.objects.filter(session=self.cross_session).count(), 1)

    def test_cross_filter_does_not_include_legacy_other_sessions(self):
        self.cross_session.class_type = ClassType.OTHER
        self.cross_session.save(update_fields=['class_type'])

        preview = build_projection_preview(
            weekly_plan=self.plan,
            target_week_start=date(2026, 4, 20),
            class_types=[ClassType.CROSS],
        )

        self.assertEqual(preview['totals']['sessions_found'], 0)
        self.assertEqual(preview['totals']['sessions_creatable'], 0)

    def test_program_track_routes_only_to_matching_sessions(self):
        crossfit = WorkoutProgram.objects.create(slug='test-crossfit', name='CrossFit', allowed_block_kinds=['warmup', 'metcon'])
        hyrox = WorkoutProgram.objects.create(slug='test-hyrox', name='HYROX', allowed_block_kinds=['warmup', 'metcon'])
        self.cross_session.workout_program = crossfit
        self.cross_session.save(update_fields=['workout_program'])
        other_session = ClassSession.objects.create(
            title='HYROX 12h',
            scheduled_at=self.cross_session.scheduled_at,
            duration_minutes=60,
            capacity=14,
            class_type=ClassType.HYROX,
            workout_program=hyrox,
        )
        self.plan.workout_program = crossfit

        preview = build_projection_preview(
            weekly_plan=self.plan,
            target_week_start=date(2026, 4, 20),
            class_types=[ClassType.CROSS],
        )

        self.assertEqual([entry['session_id'] for entry in preview['entries']], [self.cross_session.id])
        self.assertNotIn(other_session.id, {entry['session_id'] for entry in preview['entries']})

        mobility = WorkoutProgram.objects.get(slug='mobility')
        mobility_plan = WeeklyWodPlan.objects.create(
            week_start=date(2026, 4, 20),
            workout_program=mobility,
            label='Semana de mobilidade',
            status='confirmed',
            created_by=self.user,
            parsed_payload=self.plan.parsed_payload,
        )
        mobility_preview = build_projection_preview(
            weekly_plan=mobility_plan,
            target_week_start=date(2026, 4, 20),
            class_types=[ClassType.MOBILITY],
        )
        self.assertEqual([entry['session_id'] for entry in mobility_preview['entries']], [self.mobility_session.id])
        self.assertNotIn(self.cross_session.id, {entry['session_id'] for entry in mobility_preview['entries']})

    def test_canceled_sessions_are_not_projection_targets_or_week_coverage(self):
        canceled_session = ClassSession.objects.create(
            title='Mobilidade cancelada',
            scheduled_at=timezone.make_aware(timezone.datetime(2026, 4, 21, 19, 0)),
            duration_minutes=60,
            capacity=14,
            class_type=ClassType.MOBILITY,
            status=SessionStatus.CANCELED,
        )

        preview = build_projection_preview(
            weekly_plan=self.plan,
            target_week_start=date(2026, 4, 20),
            class_types=[ClassType.MOBILITY],
        )

        self.assertEqual(preview['sessions_in_week_total'], 3)
        self.assertEqual(preview['sessions_active_in_week_total'], 2)
        self.assertEqual(preview['sessions_canceled_total'], 1)
        self.assertEqual(preview['sessions_canceled_selected_total'], 1)
        self.assertEqual(preview['totals']['sessions_found'], 1)
        self.assertNotIn(canceled_session.id, {entry['session_id'] for entry in preview['entries']})

        self.mobility_session.status = SessionStatus.CANCELED
        self.mobility_session.save(update_fields=['status'])
        self.cross_session.status = SessionStatus.CANCELED
        self.cross_session.save(update_fields=['status'])
        canceled_only_preview = build_projection_preview(
            weekly_plan=self.plan,
            target_week_start=date(2026, 4, 20),
            class_types=[ClassType.MOBILITY],
        )
        self.assertEqual(canceled_only_preview['sessions_in_week_total'], 3)
        self.assertEqual(canceled_only_preview['sessions_active_in_week_total'], 0)
        self.assertEqual(canceled_only_preview['sessions_canceled_total'], 3)
        self.assertEqual(canceled_only_preview['sessions_canceled_selected_total'], 2)
        self.assertEqual(canceled_only_preview['totals']['sessions_found'], 0)
        with self.assertRaisesMessage(ValidationError, 'Nenhuma aula nova esta pronta'):
            project_plan_to_sessions(
                weekly_plan=self.plan,
                target_week_start=date(2026, 4, 20),
                class_types=[ClassType.MOBILITY],
                actor=self.user,
            )
        self.assertFalse(ReplicationBatch.objects.filter(weekly_plan=self.plan).exists())
        self.assertFalse(SessionWorkout.objects.filter(session__in=[self.mobility_session, canceled_session]).exists())
