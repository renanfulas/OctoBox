"""Coverage for role-aware progress projections and the NULL rollout window."""
from datetime import date, datetime, timezone as dt_timezone
from io import StringIO
from decimal import Decimal

from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutLoadLog, PublicWorkoutLoadLogSetRole as Role
from public_workouts.progress_snapshot import build_progress_snapshots


class ProgressSnapshotTests(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='curve@example.com')

    def log(self, *, role, weight, day=date(2026, 9, 1), key):
        return PublicWorkoutLoadLog.objects.create(
            account=self.account,
            movement_slug='squat',
            weight_kg=Decimal(str(weight)),
            reps=5,
            rir=Decimal('1'),
            performed_on=day,
            idempotency_key=key,
            set_role=role,
        )

    def test_warmups_do_not_enter_curve_and_nulls_remain_visible_as_legacy(self):
        top = self.log(role=Role.TOP_SET, weight=80, key='top')
        warmup = self.log(role=Role.WARMUP, weight=120, key='warmup')
        legacy = self.log(role=None, weight=60, key='legacy')

        snapshot = build_progress_snapshots(account_id=self.account.pk, as_of=date(2026, 9, 24))['squat']

        self.assertEqual([point.weight_kg for point in snapshot.curve_points], [top.weight_kg])
        self.assertEqual([point.weight_kg for point in snapshot.legacy_points], [legacy.weight_kg])
        self.assertEqual(snapshot.latest_top_set.weight_kg, top.weight_kg)
        self.assertTrue(snapshot.has_legacy_history)
        self.assertLessEqual(snapshot.y_scale['min_kg'], legacy.weight_kg)
        self.assertGreaterEqual(snapshot.y_scale['max_kg'], top.weight_kg)
        self.assertNotIn(warmup.weight_kg, [point.weight_kg for point in snapshot.curve_points])

    def test_curve_uses_most_recent_record_per_day_not_heaviest(self):
        first = self.log(role=Role.TOP_SET, weight=110, key='first')
        second = self.log(role=Role.TOP_SET, weight=90, key='correction')
        PublicWorkoutLoadLog.objects.filter(pk=first.pk).update(
            created_at=datetime(2026, 9, 1, 10, tzinfo=dt_timezone.utc),
        )
        PublicWorkoutLoadLog.objects.filter(pk=second.pk).update(
            created_at=datetime(2026, 9, 1, 11, tzinfo=dt_timezone.utc),
        )

        snapshot = build_progress_snapshots(account_id=self.account.pk, as_of=date(2026, 9, 24))['squat']

        self.assertEqual(len(snapshot.curve_points), 1)
        self.assertEqual(snapshot.curve_points[0].weight_kg, second.weight_kg)


    def test_backfill_marks_nulls_as_legacy_and_is_idempotent(self):
        legacy = self.log(role=None, weight=70, key='backfill-me')

        call_command('backfill_public_workout_load_log_set_role', stdout=StringIO())
        legacy.refresh_from_db()
        self.assertEqual(legacy.set_role, Role.LEGACY_UNKNOWN)

        call_command('backfill_public_workout_load_log_set_role', stdout=StringIO())
        legacy.refresh_from_db()
        self.assertEqual(legacy.set_role, Role.LEGACY_UNKNOWN)

    def test_database_rejects_role_outside_the_enum(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.log(role='not-a-role', weight=70, key='invalid-role')

    def test_old_records_stay_in_legacy_presence_but_outside_chart_window(self):
        old = self.log(role=Role.LEGACY_UNKNOWN, weight=60, day=date(2026, 1, 1), key='old')

        snapshot = build_progress_snapshots(account_id=self.account.pk, as_of=date(2026, 9, 24))['squat']

        self.assertTrue(snapshot.has_legacy_history)
        self.assertEqual(snapshot.legacy_points, [])
