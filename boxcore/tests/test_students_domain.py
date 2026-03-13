"""
ARQUIVO: testes unitarios das regras puras do dominio de alunos.

POR QUE ELE EXISTE:
- Protege politicas de negocio que nao devem voltar para dentro do adapter Django.

O QUE ESTE ARQUIVO FAZ:
1. Verifica a decisao de sincronizacao comercial da matricula.
2. Verifica a composicao de notas comerciais sem depender de ORM.
3. Verifica o plano puro de cobranca e a progressao de regeneracao.

PONTOS CRITICOS:
- Se estes testes quebrarem, o dominio pode voltar a vazar para infrastructure.
"""

from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from students.domain import (
    DEFAULT_INTAKE_CONVERSION_NOTE,
    append_enrollment_note,
    append_intake_note,
    build_enrollment_action_decision,
    build_enrollment_cancellation_decision,
    build_enrollment_reactivation_decision,
    build_enrollment_sync_decision,
    build_intake_conversion_decision,
    build_intake_lookup_decision,
    build_payment_mutation_decision,
    build_payment_regeneration_decision,
    build_payment_schedule_plan,
    resolve_enrollment_sync_defaults,
    resolve_regeneration_enrollment_id,
)


class StudentEnrollmentDomainTests(SimpleTestCase):
    def test_resolve_enrollment_sync_defaults_applies_commercial_fallbacks(self):
        defaults = resolve_enrollment_sync_defaults(
            enrollment_status='',
            due_date=None,
            payment_method='',
            billing_strategy='',
            installment_total=0,
            recurrence_cycles=0,
            initial_payment_amount=None,
            selected_plan_price=Decimal('289.90'),
            today=date(2026, 3, 12),
        )

        self.assertEqual(defaults.enrollment_status, 'pending')
        self.assertEqual(defaults.due_date, date(2026, 3, 12))
        self.assertEqual(defaults.payment_method, 'pix')
        self.assertEqual(defaults.billing_strategy, 'single')
        self.assertEqual(defaults.installment_total, 1)
        self.assertEqual(defaults.recurrence_cycles, 1)
        self.assertEqual(defaults.base_amount, Decimal('289.90'))

    def test_build_sync_decision_for_first_enrollment(self):
        decision = build_enrollment_sync_decision(
            has_current_enrollment=False,
            same_plan=False,
            previous_price=None,
            selected_price=Decimal('289.90'),
        )

        self.assertEqual(decision.movement, 'created')
        self.assertEqual(decision.new_enrollment_note, 'Plano conectado pela tela leve do aluno.')
        self.assertEqual(decision.payment_note, 'Primeira cobranca criada no fluxo leve do aluno.')

    def test_build_sync_decision_for_same_plan_status_adjustment(self):
        decision = build_enrollment_sync_decision(
            has_current_enrollment=True,
            same_plan=True,
            previous_price=Decimal('289.90'),
            selected_price=Decimal('289.90'),
        )

        self.assertEqual(decision.movement, 'status_adjusted')
        self.assertIsNone(decision.current_enrollment_closing_note)
        self.assertIsNone(decision.new_enrollment_note)

    def test_build_sync_decision_for_upgrade(self):
        decision = build_enrollment_sync_decision(
            has_current_enrollment=True,
            same_plan=False,
            previous_price=Decimal('289.90'),
            selected_price=Decimal('349.90'),
        )

        self.assertEqual(decision.movement, 'upgrade')
        self.assertEqual(decision.current_enrollment_closing_note, 'Encerrada por upgrade na tela leve do aluno.')
        self.assertEqual(decision.new_enrollment_note, 'Upgrade aplicada pela tela leve do aluno.')
        self.assertEqual(decision.payment_note, 'Cobranca criada apos upgrade de plano.')

    def test_append_enrollment_note_preserves_existing_text(self):
        self.assertEqual(
            append_enrollment_note('Observacao anterior.  ', 'Encerrada por upgrade na tela leve do aluno.'),
            'Observacao anterior.\nEncerrada por upgrade na tela leve do aluno.',
        )

    def test_append_enrollment_note_handles_empty_existing_note(self):
        self.assertEqual(
            append_enrollment_note('', 'Encerrada por downgrade na tela leve do aluno.'),
            'Encerrada por downgrade na tela leve do aluno.',
        )

    def test_build_enrollment_cancellation_decision_uses_reason_fallback(self):
        decision = build_enrollment_cancellation_decision(
            action_date=date(2026, 3, 12),
            reason='',
        )

        self.assertEqual(decision.status, 'canceled')
        self.assertEqual(decision.end_date, date(2026, 3, 12))
        self.assertEqual(decision.note, 'Cancelada pela tela do aluno. Motivo: nao informado.')
        self.assertEqual(decision.cancel_payment_status, 'canceled')

    def test_build_enrollment_reactivation_decision_returns_single_pix_charge(self):
        decision = build_enrollment_reactivation_decision(
            action_date=date(2026, 3, 12),
            reason='Retorno ao box.',
        )

        self.assertEqual(decision.expire_current_active_status, 'expired')
        self.assertEqual(decision.cancel_payment_statuses, ('pending', 'overdue'))
        self.assertEqual(decision.new_enrollment_status, 'active')
        self.assertEqual(decision.new_enrollment_note, 'Reativada pela tela do aluno. Motivo: Retorno ao box..')
        self.assertEqual(decision.payment_method, 'pix')
        self.assertFalse(decision.confirm_payment_now)
        self.assertEqual(decision.billing_strategy, 'single')


class StudentPaymentDomainTests(SimpleTestCase):
    def test_build_payment_mutation_decision_for_mark_paid(self):
        decision = build_payment_mutation_decision('mark-paid')

        self.assertIsNotNone(decision)
        self.assertEqual(decision.status, 'paid')
        self.assertTrue(decision.update_paid_at)
        self.assertEqual(decision.audit_method, 'record_payment_marked_paid')

    def test_build_payment_mutation_decision_for_unsupported_action(self):
        self.assertIsNone(build_payment_mutation_decision('regenerate-payment'))

    def test_build_payment_schedule_plan_for_installments_preserves_total_amount(self):
        plan = build_payment_schedule_plan(
            due_date=date(2026, 3, 12),
            amount=Decimal('300.00'),
            billing_strategy='installments',
            installment_total=3,
            recurrence_cycles=1,
            billing_cycle='monthly',
            confirm_payment_now=True,
        )

        self.assertEqual(len(plan), 3)
        self.assertEqual([item.amount for item in plan], [Decimal('100.00'), Decimal('100.00'), Decimal('100.00')])
        self.assertEqual(plan[0].installment_number, 1)
        self.assertEqual(plan[-1].installment_total, 3)
        self.assertTrue(plan[0].charge_now)
        self.assertFalse(plan[1].charge_now)

    def test_build_payment_schedule_plan_for_recurring_advances_cycle(self):
        plan = build_payment_schedule_plan(
            due_date=date(2026, 3, 12),
            amount=Decimal('289.90'),
            billing_strategy='recurring',
            installment_total=1,
            recurrence_cycles=3,
            billing_cycle='weekly',
            confirm_payment_now=False,
        )

        self.assertEqual(len(plan), 3)
        self.assertEqual(plan[0].due_date, date(2026, 3, 12))
        self.assertEqual(plan[1].due_date, date(2026, 3, 19))
        self.assertEqual(plan[2].due_date, date(2026, 3, 26))
        self.assertTrue(all(item.amount == Decimal('289.90') for item in plan))

    def test_build_payment_schedule_plan_for_single_charge(self):
        plan = build_payment_schedule_plan(
            due_date=date(2026, 3, 12),
            amount=Decimal('159.90'),
            billing_strategy='single',
            installment_total=7,
            recurrence_cycles=9,
            billing_cycle='monthly',
            confirm_payment_now=True,
        )

        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0].amount, Decimal('159.90'))
        self.assertEqual(plan[0].installment_total, 1)
        self.assertTrue(plan[0].charge_now)

    def test_build_payment_regeneration_decision_advances_installment(self):
        decision = build_payment_regeneration_decision(
            current_due_date=date(2026, 3, 12),
            current_installment_number=2,
            current_installment_total=2,
            billing_cycle='monthly',
        )

        self.assertEqual(decision.due_date, date(2026, 4, 1))
        self.assertEqual(decision.installment_number, 3)
        self.assertEqual(decision.installment_total, 3)
        self.assertEqual(decision.note, 'Cobranca regenerada pela tela do aluno.')

    def test_resolve_regeneration_enrollment_id_prefers_payment_enrollment(self):
        self.assertEqual(
            resolve_regeneration_enrollment_id(payment_enrollment_id=10, latest_enrollment_id=20),
            10,
        )

    def test_resolve_regeneration_enrollment_id_falls_back_to_latest_enrollment(self):
        self.assertEqual(
            resolve_regeneration_enrollment_id(payment_enrollment_id=None, latest_enrollment_id=20),
            20,
        )


class StudentActionDomainTests(SimpleTestCase):
    def test_build_enrollment_action_decision_for_reactivation(self):
        decision = build_enrollment_action_decision('reactivate-enrollment')

        self.assertIsNotNone(decision)
        self.assertEqual(decision.handler_name, 'reactivate_student_enrollment_command')
        self.assertEqual(decision.audit_method, 'record_enrollment_reactivated')
        self.assertTrue(decision.use_action_result_enrollment)

    def test_build_enrollment_action_decision_for_unknown_action(self):
        self.assertIsNone(build_enrollment_action_decision('noop'))


class StudentIntakeDomainTests(SimpleTestCase):
    def test_build_intake_lookup_decision_prefers_explicit_record(self):
        decision = build_intake_lookup_decision(
            intake_record_id=15,
            student_phone='(11) 97000-0000',
        )

        self.assertEqual(decision.explicit_intake_id, 15)
        self.assertFalse(decision.should_try_phone_fallback)
        self.assertEqual(decision.normalized_student_phone, '11970000000')

    def test_build_intake_lookup_decision_enables_phone_fallback_when_no_explicit_record(self):
        decision = build_intake_lookup_decision(
            intake_record_id=None,
            student_phone='(11) 97000-0000',
        )

        self.assertTrue(decision.should_try_phone_fallback)
        self.assertIn('11970000000', decision.fallback_phone_candidates)
        self.assertIn('5511970000000', decision.fallback_phone_candidates)

    def test_build_intake_conversion_decision_normalizes_phone_and_appends_default_note(self):
        decision = build_intake_conversion_decision(
            existing_phone='(11) 97000-0000',
            existing_notes='Lead quente.',
            normalized_student_phone='5511970000000',
        )

        self.assertEqual(decision.normalized_phone, '5511970000000')
        self.assertEqual(decision.status, 'approved')
        self.assertEqual(decision.notes, 'Lead quente.\nConvertido em aluno definitivo pela tela leve.')

    def test_append_intake_note_handles_empty_existing_note(self):
        self.assertEqual(
            append_intake_note('', DEFAULT_INTAKE_CONVERSION_NOTE),
            'Convertido em aluno definitivo pela tela leve.',
        )