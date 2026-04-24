from datetime import timedelta

from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from operations.models import ClassSession, WorkoutPlannerTemplatePickerEvent, WorkoutTemplate, WorkoutTemplateBlock, WorkoutTemplateMovement
from operations.workout_planner_builders import build_planner_cell, build_planner_week, load_planner_sessions, resolve_week_start
from student_app.models import SessionWorkout, SessionWorkoutRevision, SessionWorkoutRevisionEvent, SessionWorkoutStatus, WorkoutLoadType
from tests.workout_test_support import WorkoutFlowBaseTestCase


class WorkoutPlannerBuilderTests(WorkoutFlowBaseTestCase):
    def test_build_planner_week_groups_sessions_and_states(self):
        week_start = resolve_week_start(self.session.scheduled_at.date())
        SessionWorkout.objects.create(
            session=self.session,
            title='WOD publicado',
            status=SessionWorkoutStatus.PUBLISHED,
            created_by=self.coach,
        )

        sessions = load_planner_sessions(
            week_start=week_start,
            current_role_slug='Owner',
            actor=self.owner,
        )
        planner_week = build_planner_week(week_start=week_start, sessions=sessions)

        self.assertEqual(planner_week.total_sessions, 1)
        self.assertEqual(planner_week.published_count, 1)
        self.assertEqual(planner_week.days[self.session.scheduled_at.weekday()].cells[0].state, 'published')
        self.assertEqual(planner_week.initial_focus_session_id, self.session.id)

    def test_initial_focus_prefers_pending_over_empty_or_published(self):
        week_start = resolve_week_start(self.session.scheduled_at.date())
        published_session = ClassSession.objects.create(
            title='Cross publicado',
            coach=self.coach,
            scheduled_at=self.session.scheduled_at - timedelta(days=1),
            duration_minutes=60,
            capacity=16,
        )
        SessionWorkout.objects.create(
            session=published_session,
            title='WOD publicado',
            status=SessionWorkoutStatus.PUBLISHED,
            created_by=self.coach,
        )
        SessionWorkout.objects.create(
            session=self.session,
            title='WOD pendente',
            status=SessionWorkoutStatus.PENDING_APPROVAL,
            created_by=self.coach,
        )

        sessions = load_planner_sessions(
            week_start=week_start,
            current_role_slug='Owner',
            actor=self.owner,
        )
        planner_week = build_planner_week(week_start=week_start, sessions=sessions)

        self.assertEqual(planner_week.initial_focus_session_id, self.session.id)

    def test_build_planner_cell_exposes_safe_navigation_actions(self):
        draft_workout = SessionWorkout.objects.create(
            session=self.session,
            title='WOD rascunho',
            status=SessionWorkoutStatus.DRAFT,
            created_by=self.coach,
        )

        cell = build_planner_cell(session=self.session)

        self.assertEqual(cell.workout_id, draft_workout.id)
        self.assertEqual(cell.state, 'draft')
        self.assertEqual(cell.actions[0].key, 'edit')
        self.assertEqual(cell.actions[0].href, reverse('coach-session-workout-editor', args=[self.session.id]))

    def test_pending_cell_links_to_filtered_approval_board_for_session(self):
        pending_workout = SessionWorkout.objects.create(
            session=self.session,
            title='WOD pendente',
            status=SessionWorkoutStatus.PENDING_APPROVAL,
            created_by=self.coach,
        )

        cell = build_planner_cell(session=self.session)

        self.assertEqual(cell.workout_id, pending_workout.id)
        self.assertIn(f'session_id={self.session.id}', cell.actions[0].href)

    def test_published_cell_links_to_filtered_history_for_session(self):
        published_workout = SessionWorkout.objects.create(
            session=self.session,
            title='WOD publicado',
            status=SessionWorkoutStatus.PUBLISHED,
            created_by=self.coach,
        )

        cell = build_planner_cell(session=self.session)

        self.assertEqual(cell.workout_id, published_workout.id)
        self.assertEqual(cell.actions[1].key, 'history')
        self.assertIn(f'session_id={self.session.id}', cell.actions[1].href)

    def test_published_cell_exposes_policy_label_when_available(self):
        published_workout = SessionWorkout.objects.create(
            session=self.session,
            title='WOD publicado',
            status=SessionWorkoutStatus.PUBLISHED,
            created_by=self.coach,
        )
        SessionWorkoutRevision.objects.create(
            workout=published_workout,
            version=published_workout.version,
            event=SessionWorkoutRevisionEvent.PUBLISHED,
            created_by=self.owner,
            snapshot={
                'approval_policy': 'trusted_template',
                'submission_source': 'template',
                'source_template_trusted': True,
                'bypass_approval': True,
            },
        )

        cell = build_planner_cell(session=self.session)

        self.assertEqual(cell.policy_label, 'Trusted template')
        self.assertIn('Trusted template', cell.summary)

    def test_empty_cell_exposes_trusted_template_action_for_owner_manager(self):
        template = WorkoutTemplate.objects.create(
            name='Template cockpit',
            created_by=self.owner,
            is_active=True,
            is_trusted=True,
        )

        cell = build_planner_cell(
            session=self.session,
            current_role_slug='Owner',
            trusted_template_options=({'id': template.id, 'label': template.name},),
        )

        self.assertEqual(cell.actions[1].key, 'open-template-picker')
        self.assertEqual(cell.trusted_template_label, 'Escolher template')
        self.assertTrue(cell.trusted_template_picker_enabled)

    def test_empty_cell_can_expose_duplicate_previous_slot_action(self):
        previous_session = ClassSession.objects.create(
            title=self.session.title,
            coach=self.coach,
            scheduled_at=self.session.scheduled_at - timedelta(days=7),
            duration_minutes=60,
            capacity=16,
        )
        previous_workout = SessionWorkout.objects.create(
            session=previous_session,
            title='WOD semana anterior',
            status=SessionWorkoutStatus.PUBLISHED,
            created_by=self.coach,
        )

        cell = build_planner_cell(session=self.session, previous_slot_source=previous_workout)

        self.assertEqual(cell.state, 'empty')
        self.assertTrue(cell.can_duplicate_previous)
        self.assertIn('WOD semana anterior', cell.duplicate_previous_label)
        self.assertEqual(
            cell.duplicate_previous_url,
            reverse('workout-planner-duplicate-previous-slot', args=[self.session.id]),
        )


class WorkoutPlannerViewTests(WorkoutFlowBaseTestCase):
    def test_planner_renders_week_grid_for_coach(self):
        WorkoutTemplate.objects.create(
            name='Template coach confiavel',
            created_by=self.coach,
            is_active=True,
            is_trusted=True,
        )

        response = self.client.get(reverse('workout-planner'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Semana de WOD em uma so grade.')
        self.assertContains(response, self.session.title)
        self.assertContains(response, reverse('coach-session-workout-editor', args=[self.session.id]))
        self.assertContains(response, 'Criar WOD')
        self.assertContains(response, 'Teclado:')
        self.assertContains(response, 'data-wod-planner-cell')
        self.assertContains(response, 'data-planner-day-index')
        self.assertContains(response, 'data-planner-row-index')
        self.assertContains(response, 'Spotlight')
        self.assertContains(response, 'data-planner-spotlight-session')
        self.assertContains(response, 'tabindex="0"')

    def test_owner_planner_renders_template_picker_when_trusted_templates_exist(self):
        WorkoutTemplate.objects.create(
            name='Template owner confiavel',
            created_by=self.owner,
            is_active=True,
            is_trusted=True,
        )
        self.login_as_owner()

        response = self.client.get(reverse('workout-planner'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Escolha a base da celula')
        self.assertContains(response, 'data-wod-planner-template-picker')

    def test_owner_planner_renders_template_usage_panel(self):
        WorkoutTemplate.objects.create(
            name='Template quente',
            created_by=self.owner,
            is_active=True,
            is_trusted=True,
            usage_count=5,
        )
        WorkoutTemplate.objects.create(
            name='Template frio',
            created_by=self.owner,
            is_active=True,
            is_trusted=True,
            usage_count=0,
        )
        self.login_as_owner()

        response = self.client.get(reverse('workout-planner'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Templates no radar')
        self.assertContains(response, 'Templates mais quentes do cockpit')
        self.assertContains(response, 'Template quente')
        self.assertContains(response, '5 uso(s)')
        self.assertContains(response, 'Template frio')
        self.assertContains(response, 'Frio')

    def test_owner_planner_template_picker_shows_preview_cards(self):
        template = WorkoutTemplate.objects.create(
            name='Template preview',
            created_by=self.owner,
            is_active=True,
            is_trusted=True,
            description='Base curta para treino forte.',
        )
        block = WorkoutTemplateBlock.objects.create(
            template=template,
            title='Forca base',
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
            load_value='70.00',
            sort_order=1,
        )
        self.login_as_owner()

        response = self.client.get(reverse('workout-planner'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Base curta para treino forte.')
        self.assertContains(response, 'Forca base')
        self.assertContains(response, 'Deadlift')
        self.assertContains(response, 'Tem %RM')

    def test_planner_filters_coach_to_own_sessions(self):
        other_session = ClassSession.objects.create(
            title='Cross outro coach',
            scheduled_at=timezone.now() + timedelta(hours=2),
            duration_minutes=60,
            capacity=16,
        )

        response = self.client.get(reverse('workout-planner'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.session.title)
        self.assertNotContains(response, other_session.title)

    @override_settings(WOD_APPROVAL_POLICY='trusted_template')
    def test_owner_planner_template_picker_shows_publish_direct_hint(self):
        template = WorkoutTemplate.objects.create(
            name='Template publish now',
            created_by=self.owner,
            is_active=True,
            is_trusted=True,
        )
        self.login_as_owner()

        response = self.client.get(reverse('workout-planner'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Publica direto')
        self.assertContains(response, 'template confiavel tende a publicar direto')

    @override_settings(WOD_APPROVAL_POLICY='strict')
    def test_owner_planner_template_picker_shows_goes_to_approval_hint(self):
        template = WorkoutTemplate.objects.create(
            name='Template goes queue',
            created_by=self.owner,
            is_active=True,
            is_trusted=True,
        )
        self.login_as_owner()

        response = self.client.get(reverse('workout-planner'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vai para aprovacao')
        self.assertContains(response, 'ainda cai na fila de aprovacao')

    @patch('operations.workout_planner_views.emit_wod_planner_picker_event')
    def test_owner_planner_picker_telemetry_endpoint_emits_opened_event(self, emit_picker_event):
        self.login_as_owner()

        response = self.client.post(
            reverse('workout-planner-template-picker-telemetry'),
            data={'event_name': 'opened', 'session_id': self.session.id},
        )

        self.assertEqual(response.status_code, 204)
        emit_picker_event.assert_called_once_with(
            actor=self.owner,
            event_name='opened',
            session_id=str(self.session.id),
            template_id=None,
        )

    @override_settings(WOD_APPROVAL_POLICY='trusted_template')
    def test_owner_planner_renders_short_picker_funnel_from_persisted_events(self):
        template = WorkoutTemplate.objects.create(
            name='Template funnel',
            created_by=self.owner,
            is_active=True,
            is_trusted=True,
        )
        WorkoutTemplateBlock.objects.create(
            template=template,
            title='Base',
            kind='strength',
            sort_order=1,
        )
        self.login_as_owner()

        self.client.post(
            reverse('workout-planner-template-picker-telemetry'),
            data={'event_name': 'opened', 'session_id': self.session.id},
        )
        self.client.post(
            reverse('workout-planner-template-picker-telemetry'),
            data={'event_name': 'selected', 'session_id': self.session.id, 'template_id': template.id},
        )
        self.client.post(
            reverse('workout-planner-apply-trusted-template', args=[self.session.id, template.id]),
            follow=True,
        )

        response = self.client.get(reverse('workout-planner'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Funil curto')
        self.assertContains(response, 'Abriu')
        self.assertContains(response, 'Escolheu')
        self.assertContains(response, 'Aplicou')
        self.assertContains(response, 'Publicou')
        self.assertContains(response, 'Templates que mais convertem')
        self.assertContains(response, 'Template funnel')
        self.assertContains(response, '1 publicacoes')
        self.assertGreaterEqual(WorkoutPlannerTemplatePickerEvent.objects.filter(template=template).count(), 3)

    @patch('operations.workout_planner_views.emit_wod_planner_picker_event')
    def test_owner_can_apply_trusted_template_directly_from_planner(self, emit_picker_event):
        template = WorkoutTemplate.objects.create(
            name='Template cockpit',
            created_by=self.owner,
            is_active=True,
            is_trusted=True,
        )
        block = WorkoutTemplateBlock.objects.create(
            template=template,
            title='Forca base',
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
            load_value='70.00',
            sort_order=1,
        )
        self.login_as_owner()

        response = self.client.post(
            reverse('workout-planner-apply-trusted-template', args=[self.session.id, template.id]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        workout = SessionWorkout.objects.get(session=self.session)
        self.assertIn(workout.status, {SessionWorkoutStatus.PUBLISHED, SessionWorkoutStatus.PENDING_APPROVAL})
        self.assertTrue(
            'Template confiavel aplicado direto no planner e publicado pela politica ativa.' in response.content.decode()
            or 'Template confiavel aplicado no planner e enviado para aprovacao pela politica ativa.' in response.content.decode()
        )
        self.assertEqual(emit_picker_event.call_count, 2)
        self.assertEqual(emit_picker_event.call_args_list[0].kwargs['event_name'], 'applied')
        self.assertEqual(emit_picker_event.call_args_list[1].kwargs['event_name'], 'completed')

    def test_owner_can_duplicate_previous_slot_from_planner(self):
        previous_session = ClassSession.objects.create(
            title=self.session.title,
            coach=self.coach,
            scheduled_at=self.session.scheduled_at - timedelta(days=7),
            duration_minutes=60,
            capacity=16,
        )
        SessionWorkout.objects.create(
            session=previous_session,
            title='WOD semana anterior',
            coach_notes='Base replicavel.',
            status=SessionWorkoutStatus.PUBLISHED,
            created_by=self.coach,
            version=3,
        )
        self.login_as_owner()

        response = self.client.post(
            reverse('workout-planner-duplicate-previous-slot', args=[self.session.id]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        duplicated_workout = SessionWorkout.objects.get(session=self.session)
        self.assertEqual(duplicated_workout.title, 'WOD semana anterior')
        self.assertEqual(duplicated_workout.status, SessionWorkoutStatus.DRAFT)
        self.assertContains(response, 'WOD da semana anterior duplicado como rascunho para esta aula.')
