from datetime import date

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from student_app.models import (
    DayPlan,
    PlanBlock,
    PlanBlockKind,
    PlanMovement,
    ReplicationBatch,
    WeeklyWodPlan,
    WeeklyWodPlanStatus,
    WeeklyWodPlanWeekday,
)


class WeeklyWodPlanModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='planner-wave2',
            email='planner-wave2@example.com',
            password='senha-forte-123',
        )

    def test_weekly_plan_orders_days_blocks_and_movements_by_sort_order(self):
        plan = WeeklyWodPlan.objects.create(
            week_start=date(2026, 4, 20),
            label='Semana 20/04',
            status=WeeklyWodPlanStatus.DRAFT,
            created_by=self.user,
        )
        friday = DayPlan.objects.create(
            weekly_plan=plan,
            weekday=WeeklyWodPlanWeekday.FRIDAY,
            sort_order=2,
        )
        monday = DayPlan.objects.create(
            weekly_plan=plan,
            weekday=WeeklyWodPlanWeekday.MONDAY,
            sort_order=1,
        )
        metcon = PlanBlock.objects.create(
            day_plan=monday,
            kind=PlanBlockKind.METCON,
            title='WOD principal',
            sort_order=2,
            timecap_min=12,
        )
        warmup = PlanBlock.objects.create(
            day_plan=monday,
            kind=PlanBlockKind.WARMUP,
            title='Aquecimento',
            sort_order=1,
        )
        burpee = PlanMovement.objects.create(
            plan_block=metcon,
            movement_slug='burpee',
            movement_label_raw='Burpee',
            sort_order=2,
            reps_spec='12',
        )
        run = PlanMovement.objects.create(
            plan_block=metcon,
            movement_slug='run',
            movement_label_raw='Run',
            sort_order=1,
            reps_spec='200m',
        )

        self.assertEqual(list(plan.days.values_list('id', flat=True)), [monday.id, friday.id])
        self.assertEqual(list(monday.blocks.values_list('id', flat=True)), [warmup.id, metcon.id])
        self.assertEqual(list(metcon.movements.values_list('id', flat=True)), [run.id, burpee.id])

    def test_day_plan_is_unique_per_weekday_inside_a_weekly_plan(self):
        plan = WeeklyWodPlan.objects.create(
            week_start=date(2026, 4, 20),
            label='Semana unica',
            created_by=self.user,
        )
        DayPlan.objects.create(
            weekly_plan=plan,
            weekday=WeeklyWodPlanWeekday.MONDAY,
            sort_order=1,
        )

        with self.assertRaises(IntegrityError):
            DayPlan.objects.create(
                weekly_plan=plan,
                weekday=WeeklyWodPlanWeekday.MONDAY,
                sort_order=2,
            )

    def test_replication_batch_stays_isolated_from_session_workout(self):
        plan = WeeklyWodPlan.objects.create(
            week_start=date(2026, 4, 20),
            label='Semana pronta para replicar',
            status=WeeklyWodPlanStatus.CONFIRMED,
            created_by=self.user,
        )

        batch = ReplicationBatch.objects.create(
            weekly_plan=plan,
            created_by=self.user,
            class_type_filter=['cross', 'mobility'],
            sessions_targeted=8,
            sessions_created=0,
        )

        self.assertEqual(batch.weekly_plan, plan)
        self.assertEqual(batch.class_type_filter, ['cross', 'mobility'])
        self.assertEqual(batch.sessions_created, 0)
