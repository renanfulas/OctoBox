from datetime import date, datetime, timedelta

from django import forms
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from operations.forms import WeeklyWodProjectionForm, WeeklyWodSmartPasteForm
from operations.models import ClassSession, ClassType, WorkoutTemplate
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

    def test_surface_does_not_auto_bind_latest_plan_from_another_week(self):
        WeeklyWodPlan.objects.create(
            week_start='2027-04-19',
            label='Plano futuro',
            source_text='Segunda\\nCardio',
            parsed_payload={'week_label': None, 'parse_warnings': [], 'days': []},
            created_by=self.coach,
            status=WeeklyWodPlanStatus.CONFIRMED,
        )

        response = self.client.get(reverse('workout-smart-paste'))

        self.assertEqual(response.status_code, 200)
        current_week_start = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        self.assertIsNone(response.context['weekly_plan'])
        self.assertEqual(
            response.context['smart_paste_form'].initial['week_start'],
            current_week_start.strftime('%d/%m/%Y'),
        )
        self.assertEqual(
            response.context['projection_form'].initial['target_week_start'],
            current_week_start.strftime('%d/%m/%Y'),
        )
        self.assertNotContains(response, 'Plano futuro')

    def test_coach_can_parse_text_into_weekly_plan_draft(self):
        response = self.client.post(
            reverse('workout-smart-paste'),
            data={
                'week_start': '20/04',
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
        self.assertNotContains(response, 'smart-paste-projection-panel')

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
                'week_start': '20/04',
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
        self.assertContains(response, 'Salvar como template')

    def test_coach_can_save_confirmed_weekly_plan_as_stored_template(self):
        plan = WeeklyWodPlan.objects.create(
            week_start='2026-04-20',
            label='Semana template',
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
                                'kind': 'strength',
                                'title': 'Forca base',
                                'notes': 'Subir com tecnica.',
                                'movements': [
                                    {
                                        'movement_slug': 'deadlift',
                                        'movement_label_raw': 'Deadlift',
                                        'reps_spec': '5',
                                        'load_spec': '70%',
                                        'notes': 'Controlar a descida.',
                                        'sort_order': 0,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
            created_by=self.coach,
            status=WeeklyWodPlanStatus.CONFIRMED,
        )

        response = self.client.post(
            reverse('workout-smart-paste'),
            data={
                'plan_id': plan.id,
                'template_name': 'Template criado do Smart Paste',
                'action': 'create_stored_template',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        template = WorkoutTemplate.objects.get(name='Template criado do Smart Paste')
        self.assertEqual(template.created_by, self.coach)
        self.assertFalse(template.is_trusted)
        self.assertEqual(template.blocks.count(), 1)
        movement = template.blocks.first().movements.first()
        self.assertEqual(movement.movement_slug, 'deadlift')
        self.assertEqual(movement.reps, 5)
        self.assertEqual(movement.load_type, 'percentage_of_rm')
        self.assertContains(response, 'Template criado do Smart Paste')
        self.assertContains(response, 'criado a partir do Smart Paste.')
        self.assertContains(response, 'Biblioteca oficial de templates de WOD.')

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
        self.assertNotContains(response, 'Revise um item por vez')
        self.assertNotContains(response, 'Salvar e revisar proximo')

    def test_preview_focuses_first_unresolved_item_in_review_corridor(self):
        current_week_start = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        plan = WeeklyWodPlan.objects.create(
            week_start=current_week_start,
            label='Semana fila',
            source_text='Segunda\nWod\nrum\nbike',
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
                                    },
                                    {
                                        'movement_slug': None,
                                        'movement_label_raw': 'bike',
                                        'reps_spec': None,
                                        'load_spec': '',
                                        'notes': None,
                                        'sort_order': 1,
                                    },
                                ],
                            }
                        ],
                    }
                ],
            },
            created_by=self.coach,
        )

        response = self.client.get(reverse('workout-smart-paste'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'pendencia')
        self.assertContains(response, 'rum')
        self.assertContains(response, 'bike')
        self.assertContains(response, 'Salvar e revisar proximo')

    def test_inline_review_partial_auto_opens_next_unresolved_item(self):
        plan = WeeklyWodPlan.objects.create(
            week_start='2026-04-20',
            label='Semana revisar duas vezes',
            source_text='Segunda\nWod\nrum\njum',
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
                                    },
                                    {
                                        'movement_slug': None,
                                        'movement_label_raw': 'jum',
                                        'reps_spec': None,
                                        'load_spec': '',
                                        'notes': None,
                                        'sort_order': 1,
                                    },
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
        self.assertContains(response, 'data-smart-paste-auto-open-target="review-item-0-0-1"')

    def test_unresolved_items_block_weekly_confirmation(self):
        WeeklyWodPlan.objects.create(
            week_start='2026-04-27',
            label='Semana com pendencia',
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
                                        'movement_label_raw': 'movimento inventado xyz',
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
        response = self.client.get(reverse('workout-smart-paste'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Feche as pendencias antes de confirmar.')
        self.assertContains(response, 'disabled aria-disabled="true"')

    def test_coach_can_preview_and_create_projection_as_drafts(self):
        target_week_start = WeeklyWodProjectionForm(
            data={
                'plan_id': 1,
                'target_week_start': '27/04',
                'class_types': [ClassType.CROSS],
            }
        )
        self.assertTrue(target_week_start.is_valid(), target_week_start.errors)
        resolved_week_start = target_week_start.cleaned_data['target_week_start']
        weekday_labels = {
            0: 'Segunda',
            1: 'Terca',
            2: 'Quarta',
            3: 'Quinta',
            4: 'Sexta',
            5: 'Sabado',
            6: 'Domingo',
        }
        resolved_weekday = resolved_week_start.weekday()

        plan = WeeklyWodPlan.objects.create(
            week_start='2026-04-20',
            label='Semana pronta',
            source_text=SMART_PASTE_SAMPLE,
            parsed_payload={
                'week_label': None,
                'parse_warnings': [],
                'days': [
                    {
                        'weekday': resolved_weekday,
                        'weekday_label': weekday_labels[resolved_weekday],
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
        self.session.scheduled_at = timezone.make_aware(
            datetime.combine(resolved_week_start, datetime.min.time()).replace(hour=12)
        )
        self.session.save(update_fields=['class_type', 'scheduled_at'])

        preview_response = self.client.post(
            reverse('workout-smart-paste'),
            data={
                'plan_id': plan.id,
                'target_week_start': '27/04',
                'class_types': [ClassType.CROSS],
                'action': 'preview_projection',
            },
            follow=True,
        )

        self.assertEqual(preview_response.status_code, 200)
        self.assertContains(preview_response, 'Preview de replicacao montado sem criar WODs ainda.')
        self.assertContains(preview_response, '1 aula(s) pronta(s) para criar')
        self.assertContains(preview_response, '1 aula(s) encontrada(s)')
        self.assertContains(preview_response, '0 aula(s) com colisao')
        self.assertContains(preview_response, 'Carga alvo preservada em nota: 40/25')

        create_response = self.client.post(
            reverse('workout-smart-paste'),
            data={
                'plan_id': plan.id,
                'target_week_start': '27/04',
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
        self.session.scheduled_at = timezone.make_aware(datetime(2026, 4, 27, 12, 0))
        self.session.save(update_fields=['class_type', 'scheduled_at'])

        response = self.client.post(
            reverse('workout-smart-paste'),
            data={
                'plan_id': plan.id,
                'target_week_start': '27/04',
                'class_types': [ClassType.CROSS],
                'action': 'preview_projection',
            },
            HTTP_HX_REQUEST='true',
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<html')
        self.assertContains(response, 'smart-paste-projection-panel')

    def test_unconfirmed_plan_cannot_open_projection(self):
        plan = WeeklyWodPlan.objects.create(
            week_start='2026-04-20',
            label='Semana draft',
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
            status=WeeklyWodPlanStatus.DRAFT,
        )

        response = self.client.post(
            reverse('workout-smart-paste'),
            data={
                'plan_id': plan.id,
                'target_week_start': '27/04',
                'class_types': [ClassType.CROSS],
                'action': 'preview_projection',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirme o rascunho semanal antes de montar a replicacao.')

    def test_smart_paste_date_prefers_selected_week_in_same_year_when_it_is_closer(self):
        today = timezone.localdate()
        current_year_candidate = date(today.year, 4, 26)
        expected_current_year_date = current_year_candidate - timedelta(days=current_year_candidate.weekday())

        current_year_form = WeeklyWodSmartPasteForm(
            data={
                'week_start': '26/04',
                'label': 'Semana atual',
                'source_text': SMART_PASTE_SAMPLE,
            }
        )
        self.assertTrue(current_year_form.is_valid(), current_year_form.errors)
        self.assertEqual(
            current_year_form.cleaned_data['week_start'].isoformat(),
            expected_current_year_date.isoformat(),
        )

        next_year_candidate = date(today.year, 1, 1)
        expected_next_year_date = next_year_candidate - timedelta(days=next_year_candidate.weekday())
        next_year_form = WeeklyWodSmartPasteForm(
            data={
                'week_start': '01/01',
                'label': 'Virada',
                'source_text': SMART_PASTE_SAMPLE,
            }
        )
        self.assertTrue(next_year_form.is_valid(), next_year_form.errors)
        self.assertEqual(
            next_year_form.cleaned_data['week_start'].isoformat(),
            expected_next_year_date.isoformat(),
        )

    @patch('operations.forms.timezone.localdate', return_value=date(2026, 4, 28))
    def test_smart_paste_date_accepts_explicit_past_week_in_current_year(self, mocked_today):
        past_form = WeeklyWodSmartPasteForm(
            data={
                'week_start': '20/04/2026',
                'label': 'Semana passada',
                'source_text': SMART_PASTE_SAMPLE,
            }
        )
        self.assertTrue(past_form.is_valid(), past_form.errors)
        self.assertEqual(past_form.cleaned_data['week_start'].isoformat(), '2026-04-20')

    @patch('operations.forms.timezone.localdate', return_value=date(2026, 4, 28))
    def test_smart_paste_date_rejects_years_outside_previous_current_next_window(self, mocked_today):
        far_future_form = WeeklyWodSmartPasteForm(
            data={
                'week_start': '01/01/2030',
                'label': 'Longe demais',
                'source_text': SMART_PASTE_SAMPLE,
            }
        )
        self.assertFalse(far_future_form.is_valid())
        self.assertIn('A data precisa ficar no ano anterior, atual ou no proximo ano.', far_future_form.errors['week_start'])

    def test_projection_target_week_accepts_calendar_year_and_past_week(self):
        projection_form = WeeklyWodProjectionForm(
            data={
                'plan_id': 1,
                'target_week_start': '27/04/2025',
                'class_types': [ClassType.CROSS],
            }
        )
        self.assertTrue(projection_form.is_valid(), projection_form.errors)
        self.assertEqual(projection_form.cleaned_data['target_week_start'].isoformat(), '2025-04-21')

    def test_smart_paste_snaps_non_monday_to_previous_monday(self):
        # Find a future Wednesday so the snapped Monday is also in the future.
        today = date.today()
        days_ahead = (2 - today.weekday()) % 7 or 7  # next Wednesday, never today
        wednesday = today + timedelta(days=days_ahead)
        expected_monday = wednesday - timedelta(days=2)

        form = WeeklyWodSmartPasteForm(
            data={
                'week_start': wednesday.strftime('%d/%m/%Y'),
                'label': 'Snap para segunda',
                'source_text': SMART_PASTE_SAMPLE,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['week_start'], expected_monday)
        self.assertEqual(form.cleaned_data['week_start'].weekday(), 0)


class WodSlugResolverTests(WorkoutFlowBaseTestCase):
    """Testa o resolvedor LLM de slugs (wod_slug_resolver.py)."""

    def _make_slug_dict(self):
        return [
            ('pull_up', ('pull-up', 'pull up', 'barra')),
            ('push_up', ('push-up', 'push up', 'flexão')),
            ('run', ('corrida', 'run')),
            ('box_jump', ('box jump', 'salto na caixa')),
        ]

    def test_resolve_unknown_slugs_returns_empty_when_no_api_key(self):
        from operations.services.wod_slug_resolver import resolve_unknown_slugs
        with patch.dict('os.environ', {}, clear=True):
            # Garante que nenhuma chave está configurada
            import os
            os.environ.pop('OPENAI_API_KEY', None)
            os.environ.pop('ANTHROPIC_API_KEY', None)
            result = resolve_unknown_slugs(
                unrecognized_names=['Pistol Squat', 'Burpee'],
                slug_dictionary=self._make_slug_dict(),
            )
        self.assertEqual(result, {})

    def test_resolve_unknown_slugs_returns_empty_for_empty_input(self):
        from operations.services.wod_slug_resolver import resolve_unknown_slugs
        result = resolve_unknown_slugs(
            unrecognized_names=[],
            slug_dictionary=self._make_slug_dict(),
        )
        self.assertEqual(result, {})

    def test_resolve_rejects_invalid_slugs_from_llm_response(self):
        from operations.services.wod_slug_resolver import _parse_and_validate
        valid_slugs = {'pull_up', 'push_up', 'run'}
        raw_json = '{"Pistol Squat": "pistol_squat", "Pull-up": "pull_up", "Invented": "fake_slug_xyz"}'
        result = _parse_and_validate(
            raw_text=raw_json,
            valid_slugs=valid_slugs,
            unrecognized_names=['Pistol Squat', 'Pull-up', 'Invented'],
        )
        # pistol_squat não está em valid_slugs → rejeitado
        self.assertNotIn('Pistol Squat', result)
        # pull_up está → aceito
        self.assertEqual(result.get('Pull-up'), 'pull_up')
        # fake_slug_xyz não está → rejeitado
        self.assertNotIn('Invented', result)

    def test_apply_llm_slug_resolution_fills_unresolved_movements(self):
        from operations.services.wod_slug_resolver import apply_llm_slug_resolution
        parsed_payload = {
            'days': [
                {
                    'weekday': 0,
                    'weekday_label': 'Segunda',
                    'blocks': [
                        {
                            'kind': 'metcon',
                            'movements': [
                                {'movement_label_raw': 'PullUp', 'movement_slug': None},
                                {'movement_label_raw': 'corrida', 'movement_slug': 'run'},
                            ],
                        }
                    ],
                }
            ]
        }
        slug_dict = self._make_slug_dict()

        mock_resolved = {'PullUp': 'pull_up'}
        with patch('operations.services.wod_slug_resolver.resolve_unknown_slugs', return_value=mock_resolved):
            apply_llm_slug_resolution(parsed_payload, slug_dict)

        movements = parsed_payload['days'][0]['blocks'][0]['movements']
        self.assertEqual(movements[0]['movement_slug'], 'pull_up')
        # Movimento já resolvido não deve ser alterado
        self.assertEqual(movements[1]['movement_slug'], 'run')

    def test_apply_llm_slug_resolution_does_nothing_when_resolver_returns_empty(self):
        from operations.services.wod_slug_resolver import apply_llm_slug_resolution
        parsed_payload = {
            'days': [
                {
                    'weekday': 0,
                    'weekday_label': 'Segunda',
                    'blocks': [
                        {
                            'kind': 'metcon',
                            'movements': [
                                {'movement_label_raw': 'movimento xyz', 'movement_slug': None},
                            ],
                        }
                    ],
                }
            ]
        }
        with patch('operations.services.wod_slug_resolver.resolve_unknown_slugs', return_value={}):
            apply_llm_slug_resolution(parsed_payload, self._make_slug_dict())

        # Slug permanece None — comportamento original preservado
        self.assertIsNone(parsed_payload['days'][0]['blocks'][0]['movements'][0]['movement_slug'])

    def test_parse_text_action_calls_llm_resolver(self):
        """Garante que a view chama apply_llm_slug_resolution após parsear o texto."""
        with patch('operations.workout_board_views.apply_llm_slug_resolution') as mock_resolver:
            response = self.client.post(reverse('workout-smart-paste'), {
                'action': 'parse_text',
                'week_start': '28/04/2026',
                'label': 'Semana teste resolver',
                'source_text': 'Segunda\nWod\n10 pistol squats',
            })
        self.assertIn(response.status_code, [200, 302])
        mock_resolver.assert_called_once()
