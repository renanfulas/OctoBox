from datetime import datetime

from django.urls import reverse
from django.utils import timezone

from operations.models import ClassSession, ClassType
from student_app.models import SessionWorkout, SessionWorkoutStatus, WeeklyWodPlan, WeeklyWodPlanStatus
from tests.workout_test_support import WorkoutFlowBaseTestCase


SMART_PASTE_SAMPLE = """
Segunda
Mobilidade

Aquecimento
3x
10 lunges
8 front squat
20 sit up
""".strip()


class WorkoutSmartPasteFlowTests(WorkoutFlowBaseTestCase):
    def test_coach_can_open_smart_paste_surface(self):
        response = self.client.get(reverse('workout-smart-paste'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Smart Paste')
        self.assertContains(response, 'Cole o WOD semanal e revise antes de replicar.')

    def test_coach_can_parse_text_into_weekly_plan_draft(self):
        response = self.client.post(
            reverse('workout-smart-paste'),
            data={
                'week_start': '2026-04-20',
                'label': 'Semana base',
                'source_text': SMART_PASTE_SAMPLE,
                'action': 'parse_text',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        plan = WeeklyWodPlan.objects.get()
        self.assertEqual(plan.status, WeeklyWodPlanStatus.DRAFT)
        self.assertEqual(plan.label, 'Semana base')
        self.assertEqual(plan.source_text, SMART_PASTE_SAMPLE)
        self.assertEqual(plan.parsed_payload['days'][0]['weekday_label'], 'Segunda')
        self.assertContains(response, 'Texto organizado em rascunho semanal.')
        self.assertContains(response, 'Aquecimento')
        self.assertContains(response, 'lunge')

    def test_coach_can_confirm_existing_weekly_plan_after_preview(self):
        plan = WeeklyWodPlan.objects.create(
            week_start='2026-04-20',
            label='Semana pronta',
            source_text=SMART_PASTE_SAMPLE,
            parsed_payload={
                'week_label': None,
                'parse_warnings': [],
                'days': [
                    {
                        'weekday': 0,
                        'weekday_label': 'Segunda',
                        'blocks': [],
                    }
                ],
            },
            created_by=self.coach,
        )

        response = self.client.post(
            reverse('workout-smart-paste'),
            data={
                'plan_id': plan.id,
                'week_start': '2026-04-20',
                'label': 'Semana pronta',
                'source_text': SMART_PASTE_SAMPLE,
                'action': 'confirm_plan',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(plan.status, WeeklyWodPlanStatus.CONFIRMED)
        self.assertContains(response, 'Plano semanal confirmado.')

    def test_coach_can_inline_review_unresolved_item_with_htmx_partial(self):
        plan = WeeklyWodPlan.objects.create(
            week_start='2026-04-20',
            label='Semana revisar',
            source_text='Segunda\nWod\nrum',
            parsed_payload={
                'week_label': None,
                'parse_warnings': [],
                'days': [
                    {
                        'weekday': 0,
                        'weekday_label': 'Segunda',
                        'blocks': [
                            {
                                'kind': 'metcon',
                                'title': 'WOD',
                                'notes': '',
                                'movements': [
                                    {
                                        'movement_slug': None,
                                        'movement_label_raw': 'rum',
                                        'reps_spec': None,
                                        'load_spec': '',
                                        'notes': None,
                                        'sort_order': 0,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
            created_by=self.coach,
        )

        response = self.client.post(
            reverse('workout-smart-paste'),
            data={
                'action': 'update_review_item',
                'plan_id': plan.id,
                'day_index': 0,
                'block_index': 0,
                'movement_index': 0,
                'movement_label_raw': 'run',
                'movement_slug': '',
                'reps_spec': '400',
                'load_spec': '',
                'notes': 'Corrigido no preview',
            },
            HTTP_HX_REQUEST='true',
        )

        self.assertEqual(response.status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(plan.parsed_payload['days'][0]['blocks'][0]['movements'][0]['movement_slug'], 'run')
        self.assertEqual(plan.parsed_payload['days'][0]['blocks'][0]['movements'][0]['reps_spec'], '400')
        self.assertEqual(plan.parsed_payload['days'][0]['blocks'][0]['movements'][0]['notes'], 'Corrigido no preview')
        self.assertNotContains(response, '<html')
        self.assertContains(response, 'run')

    def test_coach_can_preview_and_create_projection_as_drafts(self):
        plan = WeeklyWodPlan.objects.create(
            week_start='2026-04-20',
            label='Semana pronta',
            source_text=SMART_PASTE_SAMPLE,
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
                                'title': None,
                                'notes': None,
                                'timecap_min': None,
                                'rounds': 3,
                                'interval_seconds': None,
                                'score_type': None,
                                'format_spec': '3x',
                                'movements': [
                                    {
                                        'movement_slug': 'lunge',
                                        'movement_label_raw': '10 lunges',
                                        'reps_spec': '10',
                                        'load_spec': None,
                                        'notes': None,
                                        'sort_order': 0,
                                    }
                                ],
                                'sort_order': 0,
                            },
                            {
                                'kind': 'metcon',
                                'title': 'WOD',
                                'notes': None,
                                'timecap_min': 12,
                                'rounds': None,
                                'interval_seconds': None,
                                'score_type': 'for_time',
                                'format_spec': None,
                                'movements': [
                                    {
                                        'movement_slug': 'push_press',
                                        'movement_label_raw': '50 push press 40/25',
                                        'reps_spec': '50',
                                        'load_spec': '40/25',
                                        'notes': None,
                                        'sort_order': 0,
                                    }
                                ],
                                'sort_order': 1,
                            },
                        ],
                    }
                ],
            },
            created_by=self.coach,
            status=WeeklyWodPlanStatus.CONFIRMED,
        )
        self.session.class_type = ClassType.CROSS
        self.session.scheduled_at = timezone.make_aware(datetime(2026, 4, 20, 12, 0))
        self.session.save(update_fields=['class_type', 'scheduled_at'])

        preview_response = self.client.post(
            reverse('workout-smart-paste'),
            data={
                'plan_id': plan.id,
                'target_week_start': '2026-04-20',
                'class_types': [ClassType.CROSS],
                'action': 'preview_projection',
            },
            follow=True,
        )

        self.assertEqual(preview_response.status_code, 200)
        self.assertContains(preview_response, 'Preview de replicacao montado sem criar WODs ainda.')
        self.assertContains(preview_response, 'ready')
        self.assertContains(preview_response, '0 aula(s) com colisao')
        self.assertContains(preview_response, 'Carga alvo preservada em nota: 40/25')

        create_response = self.client.post(
            reverse('workout-smart-paste'),
            data={
                'plan_id': plan.id,
                'target_week_start': '2026-04-20',
                'class_types': [ClassType.CROSS],
                'action': 'create_projection',
            },
            follow=True,
        )

        self.assertEqual(create_response.status_code, 200)
        workout = SessionWorkout.objects.get(session=self.session)
        self.assertEqual(workout.status, SessionWorkoutStatus.DRAFT)
        self.assertIsNotNone(workout.replication_batch)
        self.assertEqual(workout.replication_batch.sessions_created, 1)
        self.assertEqual(workout.blocks.count(), 2)
        self.assertContains(create_response, '1 WOD(s) criado(s) em DRAFT.')

        undo_response = self.client.post(
            reverse('workout-smart-paste'),
            data={
                'plan_id': plan.id,
                'batch_id': workout.replication_batch.id,
                'action': 'undo_projection',
            },
            follow=True,
        )

        self.assertEqual(undo_response.status_code, 200)
        self.assertFalse(SessionWorkout.objects.filter(session=self.session).exists())
        plan.refresh_from_db()
        latest_batch = plan.replication_batches.order_by('-created_at', '-id').first()
        self.assertIsNotNone(latest_batch.undone_at)
        self.assertContains(undo_response, 'registro(s) relacionados ao lote foram desfeitos.')

    def test_projection_preview_can_render_partial_panel_with_htmx(self):
        plan = WeeklyWodPlan.objects.create(
            week_start='2026-04-20',
            label='Semana htmx',
            source_text=SMART_PASTE_SAMPLE,
            parsed_payload={
                'week_label': None,
                'parse_warnings': [],
                'days': [
                    {
                        'weekday': 0,
                        'weekday_label': 'Segunda',
                        'blocks': [],
                    }
                ],
            },
            created_by=self.coach,
            status=WeeklyWodPlanStatus.CONFIRMED,
        )
        self.session.class_type = ClassType.CROSS
        self.session.scheduled_at = timezone.make_aware(datetime(2026, 4, 20, 12, 0))
        self.session.save(update_fields=['class_type', 'scheduled_at'])

        response = self.client.post(
            reverse('workout-smart-paste'),
            data={
                'plan_id': plan.id,
                'target_week_start': '2026-04-20',
                'class_types': [ClassType.CROSS],
                'action': 'preview_projection',
            },
            HTTP_HX_REQUEST='true',
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<html')
        self.assertContains(response, 'smart-paste-projection-panel')
