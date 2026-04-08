"""
ARQUIVO: testes unitarios das regras puras do dominio operacional.

POR QUE ELE EXISTE:
- Protege politicas de workspace e grade que nao devem voltar para dentro dos adapters Django.

O QUE ESTE ARQUIVO FAZ:
1. Verifica a nota padrao do vinculo operacional de pagamento.
2. Verifica a validacao da ocorrencia tecnica.
3. Verifica as decisoes puras de presenca.
4. Verifica o planejamento recorrente puro da grade de aulas.

PONTOS CRITICOS:
- Se estes testes quebrarem, o dominio operacional pode voltar a vazar para infrastructure.
"""

from datetime import date, datetime, time

from django.test import SimpleTestCase

from operations.domain import (
    build_attendance_action_decision,
    build_class_grid_create_execution_plan,
    build_class_grid_create_slot_decision,
    build_class_grid_schedule_plan,
    build_class_grid_session_policy,
    build_payment_enrollment_note,
    build_technical_behavior_note_decision,
    collect_changed_field_names,
    iter_schedule_dates,
    ScheduledClassGridSlot,
    should_enforce_schedule_limits_for_status,
)


class OperationWorkspaceDomainTests(SimpleTestCase):
    def test_build_payment_enrollment_note_uses_default_when_blank(self):
        self.assertEqual(
            build_payment_enrollment_note(''),
            'Vinculo operacional aplicado pela area do manager.',
        )

    def test_build_payment_enrollment_note_preserves_existing_text(self):
        self.assertEqual(
            build_payment_enrollment_note('Observacao manual.'),
            'Observacao manual.',
        )

    def test_build_technical_behavior_note_decision_validates_category_and_description(self):
        decision = build_technical_behavior_note_decision(
            category='support',
            description='  Aluno relatou desconforto no ombro.  ',
            valid_categories={'support', 'warning'},
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.description, 'Aluno relatou desconforto no ombro.')

    def test_build_technical_behavior_note_decision_rejects_invalid_payload(self):
        self.assertIsNone(
            build_technical_behavior_note_decision(
                category='unknown',
                description='   ',
                valid_categories={'support', 'warning'},
            )
        )

    def test_build_attendance_action_decision_for_check_out(self):
        decision = build_attendance_action_decision('check-out')

        self.assertIsNotNone(decision)
        self.assertEqual(decision.status, 'checked_out')
        self.assertFalse(decision.set_check_in_now)
        self.assertTrue(decision.set_check_out_now)
        self.assertTrue(decision.ensure_check_in_when_missing)

    def test_build_attendance_action_decision_for_invalid_action(self):
        self.assertIsNone(build_attendance_action_decision('invalid'))


class OperationClassGridDomainTests(SimpleTestCase):
    def test_build_class_grid_create_slot_decision_skips_existing_slot_when_requested(self):
        decision = build_class_grid_create_slot_decision(
            has_existing=True,
            skip_existing=True,
        )

        self.assertFalse(decision.should_create)
        self.assertTrue(decision.should_skip)

    def test_build_class_grid_create_execution_plan_marks_skips_and_remaining_pending_counts(self):
        execution_plan = build_class_grid_create_execution_plan(
            scheduled_slots=(
                ScheduledClassGridSlot(
                    scheduled_date=date(2026, 3, 16),
                    scheduled_at=datetime(2026, 3, 16, 7, 0),
                ),
                ScheduledClassGridSlot(
                    scheduled_date=date(2026, 3, 16),
                    scheduled_at=datetime(2026, 3, 16, 8, 0),
                ),
                ScheduledClassGridSlot(
                    scheduled_date=date(2026, 3, 18),
                    scheduled_at=datetime(2026, 3, 18, 7, 0),
                ),
            ),
            existing_scheduled_ats=frozenset({datetime(2026, 3, 16, 8, 0)}),
            skip_existing=True,
        )

        self.assertEqual(execution_plan.skipped_slots, (datetime(2026, 3, 16, 8, 0),))
        self.assertEqual(len(execution_plan.slots_to_create), 2)
        self.assertEqual(execution_plan.slots_to_create[0].pending_day, 0)
        self.assertEqual(execution_plan.slots_to_create[0].pending_week, 1)
        self.assertEqual(execution_plan.slots_to_create[0].pending_month, 1)
        self.assertEqual(execution_plan.slots_to_create[1].pending_day, 0)
        self.assertEqual(execution_plan.slots_to_create[1].pending_week, 0)
        self.assertEqual(execution_plan.slots_to_create[1].pending_month, 0)

    def test_collect_changed_field_names_returns_only_effective_changes(self):
        changed_fields = collect_changed_field_names(
            current_values={
                'title': 'Cross 7h',
                'capacity': 20,
                'status': 'scheduled',
            },
            target_values={
                'title': 'Cross 7h',
                'capacity': 24,
                'status': 'canceled',
            },
        )

        self.assertEqual(changed_fields, ('capacity', 'status'))

    def test_should_enforce_schedule_limits_for_status_ignores_canceled(self):
        self.assertFalse(should_enforce_schedule_limits_for_status('canceled'))
        self.assertTrue(should_enforce_schedule_limits_for_status('scheduled'))

    def test_build_class_grid_session_policy_blocks_reopening_completed_session(self):
        policy = build_class_grid_session_policy(
            initial_status='completed',
            has_attendance=False,
        )

        with self.assertRaisesMessage(
            ValueError,
            'Aulas concluidas nao podem voltar para agendada por esta edicao rapida.',
        ):
            policy.validate_quick_edit_status('scheduled')

    def test_build_class_grid_session_policy_blocks_delete_when_attendance_exists(self):
        policy = build_class_grid_session_policy(
            initial_status='scheduled',
            has_attendance=True,
        )

        with self.assertRaisesMessage(
            ValueError,
            'Nao exclua uma aula que ja tenha reservas ou presencas. Cancele a aula para preservar o historico.',
        ):
            policy.ensure_can_delete()

    def test_iter_schedule_dates_filters_by_weekdays(self):
        dates = iter_schedule_dates(
            start_date=date(2026, 3, 16),
            end_date=date(2026, 3, 22),
            weekdays=(0, 2),
        )

        self.assertEqual(dates, (date(2026, 3, 16), date(2026, 3, 18)))

    def test_build_class_grid_schedule_plan_creates_sequence_slots(self):
        plan = build_class_grid_schedule_plan(
            start_date=date(2026, 3, 16),
            end_date=date(2026, 3, 16),
            weekdays=(0,),
            start_time=time(7, 0),
            duration_minutes=60,
            sequence_count=3,
        )

        self.assertEqual(len(plan), 4)
        self.assertEqual([slot.start_at.strftime('%H:%M') for slot in plan], ['07:00', '08:00', '09:00', '10:00'])
        self.assertTrue(all(slot.scheduled_date == date(2026, 3, 16) for slot in plan))

    def test_build_class_grid_schedule_plan_handles_multiple_days(self):
        plan = build_class_grid_schedule_plan(
            start_date=date(2026, 3, 16),
            end_date=date(2026, 3, 19),
            weekdays=(0, 2),
            start_time=time(6, 0),
            duration_minutes=60,
            sequence_count=0,
        )

        self.assertEqual([slot.scheduled_date for slot in plan], [date(2026, 3, 16), date(2026, 3, 18)])

    def test_iter_schedule_dates_supports_weekend_rotation_by_interval(self):
        dates = iter_schedule_dates(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
            weekdays=(5, 6),
            anchor_date=date(2026, 4, 11),
            interval_days=14,
        )

        self.assertEqual(
            dates,
            (
                date(2026, 4, 11),
                date(2026, 4, 12),
                date(2026, 4, 25),
                date(2026, 4, 26),
            ),
        )
