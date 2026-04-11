from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from catalog.finance_snapshot import build_financial_churn_foundation, build_finance_snapshot
from catalog.finance_snapshot.ai import (
    build_contextual_recommendation_map,
    build_finance_follow_up_analytics,
    build_turn_priority_tension_context_map,
    build_timing_recommendation_override_map,
)
from catalog.services.finance_communication_actions import handle_finance_communication_action
from communications.models import MessageDirection, MessageKind, WhatsAppContact, WhatsAppMessageLog
from django.contrib.auth import get_user_model
from finance.follow_up_tracker import evaluate_finance_follow_up_outcome, evaluate_pending_finance_follow_ups
from finance.models import (
    Enrollment,
    EnrollmentStatus,
    FinanceFollowUp,
    FinanceFollowUpOutcomeStatus,
    FinanceFollowUpStatus,
    MembershipPlan,
    Payment,
    PaymentMethod,
    PaymentStatus,
)
from students.models import Student


class FinanceChurnFoundationTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.plan = MembershipPlan.objects.create(name='Cross Prime', price='299.90', billing_cycle='monthly')
        self.user = get_user_model().objects.create_superuser(
            username='followup-owner',
            email='followup-owner@example.com',
            password='senha-forte-123',
        )

    def _create_finance_touch(self, *, student, action_kind, days_ago=0):
        contact = WhatsAppContact.objects.create(
            phone=f'55119999{student.id:06d}',
            display_name=student.full_name,
            linked_student=student,
        )
        touch_time = timezone.now() - timezone.timedelta(days=days_ago)
        return WhatsAppMessageLog.objects.create(
            contact=contact,
            direction=MessageDirection.OUTBOUND,
            kind=MessageKind.SYSTEM,
            body=f'Mensagem {action_kind}',
            delivered_at=touch_time,
            raw_payload={
                'source': 'operational-message',
                'action_kind': action_kind,
                'student_id': student.id,
            },
        )

    def test_financial_churn_foundation_marks_real_churn_when_student_is_inactive(self):
        student = Student.objects.create(full_name='Rafa Inativo', phone='5511910000001', status='inactive')
        enrollment = Enrollment.objects.create(
            student=student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=120),
            end_date=self.today - timezone.timedelta(days=5),
            status=EnrollmentStatus.CANCELED,
        )
        Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=self.today - timezone.timedelta(days=18),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )
        Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=self.today - timezone.timedelta(days=42),
            amount='299.90',
            status=PaymentStatus.OVERDUE,
            method=PaymentMethod.PIX,
        )
        self._create_finance_touch(student=student, action_kind='overdue', days_ago=2)

        foundation = build_financial_churn_foundation(
            students=Student.objects.filter(pk=student.pk),
            payments=Payment.objects.all(),
            enrollments=Enrollment.objects.all(),
            today=self.today,
        )

        self.assertEqual(foundation['summary']['actual_churn_count'], 1)
        row = foundation['rows'][0]
        self.assertTrue(row['actual_churn_event'])
        self.assertEqual(row['signal_bucket'], 'already_inactive')
        self.assertEqual(row['financial_signal']['overdue_payment_count_60d'], 2)
        self.assertEqual(str(row['financial_signal']['total_open_amount']), '599.80')
        self.assertEqual(row['operational_state']['latest_enrollment_status'], EnrollmentStatus.CANCELED)
        self.assertEqual(row['communication_state']['last_finance_touch_action_kind'], 'overdue')
        self.assertIn('student_inactive', row['reason_codes'])
        self.assertEqual(row['recommended_action'], 'review_winback')
        self.assertEqual(row['confidence'], 'high')
        self.assertEqual(row['prediction_window'], 'next_30_days')
        self.assertEqual(row['recommendation_momentum']['decay_stage'], 'fresh')
        self.assertEqual(row['operational_state']['latest_plan_name'], 'Cross Prime')
        self.assertIsNotNone(row['financial_signal']['oldest_open_due_date'])

    def test_financial_churn_foundation_does_not_treat_paid_active_student_as_churn(self):
        student = Student.objects.create(full_name='Paula Recuperada', phone='5511910000002', status='active')
        enrollment = Enrollment.objects.create(
            student=student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=90),
            status=EnrollmentStatus.ACTIVE,
        )
        Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=self.today - timezone.timedelta(days=9),
            paid_at=timezone.now() - timezone.timedelta(days=6),
            amount='299.90',
            status=PaymentStatus.PAID,
            method=PaymentMethod.PIX,
        )

        foundation = build_financial_churn_foundation(
            students=Student.objects.filter(pk=student.pk),
            payments=Payment.objects.all(),
            enrollments=Enrollment.objects.all(),
            today=self.today,
        )

        row = foundation['rows'][0]
        self.assertFalse(row['actual_churn_event'])
        self.assertEqual(row['signal_bucket'], 'stable')
        self.assertEqual(str(row['financial_signal']['total_open_amount']), '0.00')
        self.assertEqual(row['financial_signal']['overdue_payment_count_30d'], 0)
        self.assertEqual(row['operational_state']['latest_enrollment_status'], EnrollmentStatus.ACTIVE)
        self.assertEqual(row['reason_codes'], ['stable_base'])
        self.assertEqual(row['recommended_action'], 'maintain_relationship')
        self.assertEqual(row['confidence'], 'low')

    def test_financial_churn_foundation_keeps_expired_enrollment_distinct_from_real_churn(self):
        student = Student.objects.create(full_name='Lia Expirada', phone='5511910000003', status='active')
        Enrollment.objects.create(
            student=student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=40),
            end_date=self.today - timezone.timedelta(days=1),
            status=EnrollmentStatus.EXPIRED,
        )

        foundation = build_financial_churn_foundation(
            students=Student.objects.filter(pk=student.pk),
            payments=Payment.objects.all(),
            enrollments=Enrollment.objects.all(),
            today=self.today,
        )

        row = foundation['rows'][0]
        self.assertFalse(row['actual_churn_event'])
        self.assertEqual(row['signal_bucket'], 'watch')
        self.assertEqual(row['operational_state']['latest_enrollment_status'], EnrollmentStatus.EXPIRED)
        self.assertIn('enrollment_expired', row['reason_codes'])
        self.assertEqual(row['recommended_action'], 'monitor_and_nudge')
        self.assertEqual(row['confidence'], 'medium')

    def test_financial_churn_foundation_marks_recovery_after_reactivation(self):
        student = Student.objects.create(full_name='Nina Voltou', phone='5511910000004', status='active')
        Enrollment.objects.create(
            student=student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=120),
            end_date=self.today - timezone.timedelta(days=70),
            status=EnrollmentStatus.CANCELED,
        )
        Enrollment.objects.create(
            student=student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=15),
            status=EnrollmentStatus.ACTIVE,
        )
        self._create_finance_touch(student=student, action_kind='reactivation', days_ago=1)

        foundation = build_financial_churn_foundation(
            students=Student.objects.filter(pk=student.pk),
            payments=Payment.objects.all(),
            enrollments=Enrollment.objects.all(),
            today=self.today,
        )

        row = foundation['rows'][0]
        self.assertFalse(row['actual_churn_event'])
        self.assertEqual(row['signal_bucket'], 'recovered')
        self.assertTrue(row['operational_state']['reactivated_after_inactive'])
        self.assertEqual(row['communication_state']['finance_touches_30d'], 1)
        self.assertIn('reactivated_after_inactive', row['reason_codes'])
        self.assertEqual(row['recommended_action'], 'monitor_recent_reactivation')
        self.assertEqual(row['confidence'], 'medium')

    def test_build_finance_snapshot_exposes_financial_churn_foundation_contract(self):
        student = Student.objects.create(full_name='Maya Snapshot', phone='5511910000005', status='inactive')
        enrollment = Enrollment.objects.create(
            student=student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=80),
            end_date=self.today - timezone.timedelta(days=4),
            status=EnrollmentStatus.CANCELED,
        )
        Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=self.today - timezone.timedelta(days=10),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        snapshot = build_finance_snapshot()

        self.assertIn('financial_churn_foundation', snapshot)
        contract = snapshot['financial_churn_foundation']['contract']
        self.assertEqual(contract['actual_churn_rule'], 'student.status == inactive')
        self.assertIn('recommended_action', contract['queue_contract'])
        self.assertIn('historical_score', contract['queue_contract'])
        self.assertIn('prediction_window', contract['queue_contract'])
        self.assertIn('financial_risk_score', contract['future_inference_contract'])

    def test_build_finance_snapshot_persists_suggested_follow_up(self):
        student = Student.objects.create(full_name='Teo Follow', phone='5511910000011', status='inactive')
        enrollment = Enrollment.objects.create(
            student=student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=80),
            end_date=self.today - timezone.timedelta(days=3),
            status=EnrollmentStatus.CANCELED,
        )
        Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=self.today - timezone.timedelta(days=14),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        build_finance_snapshot(persist_follow_ups=True)

        follow_up = FinanceFollowUp.objects.get(student=student)
        self.assertEqual(follow_up.status, FinanceFollowUpStatus.SUGGESTED)
        self.assertEqual(follow_up.recommended_action, 'review_winback')
        self.assertEqual(follow_up.source_surface, 'finance_queue')
        self.assertEqual(follow_up.suggestion_window_stage, 'fresh')
        self.assertEqual(follow_up.suggestion_window_label, 'Janela pronta para agir')
        self.assertEqual(follow_up.suggestion_window_age_days, 3)
        self.assertEqual(str(follow_up.suggestion_queue_assist_score), '0.0')
        self.assertIn('recommendation_momentum', follow_up.payload)
        self.assertEqual(follow_up.outcome_status, FinanceFollowUpOutcomeStatus.PENDING)
        self.assertEqual(follow_up.outcome_window, '30d')

    def test_finance_follow_up_is_marked_realized_after_operational_action(self):
        student = Student.objects.create(full_name='Yara Realizada', phone='5511910000012', status='active')
        enrollment = Enrollment.objects.create(
            student=student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=50),
            end_date=self.today - timezone.timedelta(days=1),
            status=EnrollmentStatus.EXPIRED,
        )
        payment = Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=self.today - timezone.timedelta(days=8),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        build_finance_snapshot(persist_follow_ups=True)
        follow_up = FinanceFollowUp.objects.get(student=student)
        self.assertEqual(follow_up.status, FinanceFollowUpStatus.SUGGESTED)

        result = handle_finance_communication_action(
            actor=self.user,
            action_kind='overdue',
            student_id=student.id,
            payment_id=payment.id,
            enrollment_id=enrollment.id,
        )

        self.assertFalse(result['blocked'])
        follow_up.refresh_from_db()
        self.assertEqual(follow_up.status, FinanceFollowUpStatus.REALIZED)
        self.assertEqual(follow_up.realized_action_kind, 'overdue')
        self.assertEqual(follow_up.resolved_by, self.user)
        self.assertEqual(follow_up.outcome_status, FinanceFollowUpOutcomeStatus.PENDING)

    def test_build_finance_snapshot_reuses_existing_suggestion_key_after_status_transition(self):
        student = Student.objects.create(full_name='Kai Reaparece', phone='5511910000099', status='inactive')
        enrollment = Enrollment.objects.create(
            student=student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=90),
            end_date=self.today - timezone.timedelta(days=4),
            status=EnrollmentStatus.CANCELED,
        )
        Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=self.today - timezone.timedelta(days=12),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        build_finance_snapshot(persist_follow_ups=True)
        follow_up = FinanceFollowUp.objects.get(student=student)
        original_id = follow_up.id
        follow_up.status = FinanceFollowUpStatus.SUPERSEDED
        follow_up.resolved_at = timezone.now()
        follow_up.outcome_reason = 'queue_shifted'
        follow_up.save(update_fields=['status', 'resolved_at', 'outcome_reason', 'updated_at'])

        build_finance_snapshot(persist_follow_ups=True)

        follow_up.refresh_from_db()
        self.assertEqual(follow_up.id, original_id)
        self.assertEqual(follow_up.status, FinanceFollowUpStatus.SUGGESTED)
        self.assertIsNone(follow_up.resolved_at)
        self.assertEqual(follow_up.outcome_reason, '')
        self.assertEqual(follow_up.outcome_status, FinanceFollowUpOutcomeStatus.PENDING)
        self.assertEqual(FinanceFollowUp.objects.filter(student=student).count(), 1)

    def test_evaluate_finance_follow_up_outcome_marks_payment_recovered(self):
        student = Student.objects.create(full_name='Nico Pago', phone='5511910000013', status='active')
        enrollment = Enrollment.objects.create(
            student=student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=30),
            status=EnrollmentStatus.ACTIVE,
        )
        payment = Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=self.today - timezone.timedelta(days=6),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        build_finance_snapshot(persist_follow_ups=True)
        follow_up = FinanceFollowUp.objects.get(student=student)
        payment.status = PaymentStatus.PAID
        payment.paid_at = timezone.now()
        payment.save(update_fields=['status', 'paid_at', 'updated_at'])

        updated = evaluate_finance_follow_up_outcome(follow_up_id=follow_up.id)

        self.assertEqual(updated.outcome_status, FinanceFollowUpOutcomeStatus.SUCCEEDED)
        self.assertEqual(updated.outcome_reason, 'payment_recovered')
        self.assertIsNotNone(updated.outcome_checked_at)

    def test_evaluate_finance_follow_up_outcome_marks_student_still_inactive(self):
        student = Student.objects.create(full_name='Luna Parada', phone='5511910000014', status='inactive')
        enrollment = Enrollment.objects.create(
            student=student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=90),
            end_date=self.today - timezone.timedelta(days=2),
            status=EnrollmentStatus.CANCELED,
        )
        Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=self.today - timezone.timedelta(days=10),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        build_finance_snapshot(persist_follow_ups=True)
        follow_up = FinanceFollowUp.objects.get(student=student)

        updated = evaluate_finance_follow_up_outcome(follow_up_id=follow_up.id)

        self.assertEqual(updated.outcome_status, FinanceFollowUpOutcomeStatus.FAILED)
        self.assertEqual(updated.outcome_reason, 'student_still_inactive')

    def test_evaluate_pending_finance_follow_ups_respects_window(self):
        student = Student.objects.create(full_name='Otto Janela', phone='5511910000015', status='active')
        enrollment = Enrollment.objects.create(
            student=student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=40),
            status=EnrollmentStatus.ACTIVE,
        )
        payment = Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=self.today - timezone.timedelta(days=10),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        build_finance_snapshot(persist_follow_ups=True)
        follow_up = FinanceFollowUp.objects.get(student=student)
        self.assertEqual(follow_up.outcome_window, '15d')

        handle_finance_communication_action(
            actor=self.user,
            action_kind='overdue',
            student_id=student.id,
            payment_id=payment.id,
            enrollment_id=enrollment.id,
        )
        follow_up.refresh_from_db()
        follow_up.resolved_at = timezone.now() - timezone.timedelta(days=16)
        follow_up.save(update_fields=['resolved_at', 'updated_at'])

        evaluated = evaluate_pending_finance_follow_ups(window='15d')

        self.assertEqual(evaluated, 1)
        follow_up.refresh_from_db()
        self.assertEqual(follow_up.outcome_status, FinanceFollowUpOutcomeStatus.FAILED)
        self.assertEqual(follow_up.outcome_reason, 'still_overdue')

    def test_evaluate_finance_followups_command_processes_matured_records(self):
        student = Student.objects.create(full_name='Mia Command', phone='5511910000016', status='active')
        enrollment = Enrollment.objects.create(
            student=student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=20),
            end_date=self.today - timezone.timedelta(days=1),
            status=EnrollmentStatus.EXPIRED,
        )
        payment = Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=self.today - timezone.timedelta(days=12),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        build_finance_snapshot(persist_follow_ups=True)
        follow_up = FinanceFollowUp.objects.get(student=student)
        handle_finance_communication_action(
            actor=self.user,
            action_kind='overdue',
            student_id=student.id,
            payment_id=payment.id,
            enrollment_id=enrollment.id,
        )
        follow_up.refresh_from_db()
        follow_up.resolved_at = timezone.now() - timezone.timedelta(days=8)
        follow_up.save(update_fields=['resolved_at', 'updated_at'])

        stdout = StringIO()
        call_command('evaluate_finance_followups', '--window', '7d', stdout=stdout)

        follow_up.refresh_from_db()
        self.assertEqual(follow_up.outcome_status, FinanceFollowUpOutcomeStatus.FAILED)
        self.assertIn('Follow-ups financeiros avaliados: 1', stdout.getvalue())

    def test_financial_churn_foundation_sorts_by_operational_priority(self):
        inactive = Student.objects.create(full_name='Alice Inativa', phone='5511910000006', status='inactive')
        high_signal = Student.objects.create(full_name='Beto Alerta', phone='5511910000007', status='active')
        watch = Student.objects.create(full_name='Caio Observa', phone='5511910000008', status='active')

        inactive_enrollment = Enrollment.objects.create(
            student=inactive,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=90),
            end_date=self.today - timezone.timedelta(days=2),
            status=EnrollmentStatus.CANCELED,
        )
        high_signal_enrollment = Enrollment.objects.create(
            student=high_signal,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=60),
            end_date=self.today - timezone.timedelta(days=1),
            status=EnrollmentStatus.EXPIRED,
        )
        watch_enrollment = Enrollment.objects.create(
            student=watch,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=45),
            end_date=self.today - timezone.timedelta(days=1),
            status=EnrollmentStatus.EXPIRED,
        )

        Payment.objects.create(
            student=inactive,
            enrollment=inactive_enrollment,
            due_date=self.today - timezone.timedelta(days=20),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )
        Payment.objects.create(
            student=high_signal,
            enrollment=high_signal_enrollment,
            due_date=self.today - timezone.timedelta(days=20),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )
        Payment.objects.create(
            student=high_signal,
            enrollment=high_signal_enrollment,
            due_date=self.today - timezone.timedelta(days=12),
            amount='299.90',
            status=PaymentStatus.OVERDUE,
            method=PaymentMethod.PIX,
        )
        Payment.objects.create(
            student=watch,
            enrollment=watch_enrollment,
            due_date=self.today - timezone.timedelta(days=8),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        foundation = build_financial_churn_foundation(
            students=Student.objects.filter(id__in=[inactive.id, high_signal.id, watch.id]),
            payments=Payment.objects.all(),
            enrollments=Enrollment.objects.all(),
            today=self.today,
        )

        self.assertEqual([row['student_name'] for row in foundation['queue_preview'][:3]], ['Alice Inativa', 'Beto Alerta', 'Caio Observa'])
        self.assertEqual(foundation['queue_preview'][0]['priority_label'], 'Winback imediato')
        self.assertEqual(foundation['queue_preview'][1]['priority_label'], 'Ataque imediato')

    def test_financial_churn_foundation_filters_queue_focus(self):
        inactive = Student.objects.create(full_name='Duda Inativa', phone='5511910000009', status='inactive')
        recovered = Student.objects.create(full_name='Eva Recuperada', phone='5511910000010', status='active')
        inactive_enrollment = Enrollment.objects.create(
            student=inactive,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=100),
            end_date=self.today - timezone.timedelta(days=5),
            status=EnrollmentStatus.CANCELED,
        )
        Enrollment.objects.create(
            student=recovered,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=120),
            end_date=self.today - timezone.timedelta(days=60),
            status=EnrollmentStatus.CANCELED,
        )
        Enrollment.objects.create(
            student=recovered,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=12),
            status=EnrollmentStatus.ACTIVE,
        )
        Payment.objects.create(
            student=inactive,
            enrollment=inactive_enrollment,
            due_date=self.today - timezone.timedelta(days=10),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        foundation = build_financial_churn_foundation(
            students=Student.objects.filter(id__in=[inactive.id, recovered.id]),
            payments=Payment.objects.all(),
            enrollments=Enrollment.objects.all(),
            today=self.today,
            queue_focus='recovered',
        )

        self.assertEqual(foundation['queue_focus'], 'recovered')
        self.assertEqual(foundation['filtered_count'], 1)
        self.assertEqual(foundation['queue_preview'][0]['student_name'], 'Eva Recuperada')

    def test_financial_churn_foundation_uses_historical_score_as_transparent_tiebreaker(self):
        stable_student = Student.objects.create(full_name='Bia Regulariza', phone='5511910000021', status='active')
        recovered_student = Student.objects.create(full_name='Ciro Retorna', phone='5511910000022', status='active')

        stable_enrollment = Enrollment.objects.create(
            student=stable_student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=40),
            status=EnrollmentStatus.ACTIVE,
        )
        Enrollment.objects.create(
            student=recovered_student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=120),
            end_date=self.today - timezone.timedelta(days=60),
            status=EnrollmentStatus.CANCELED,
        )
        recovered_enrollment = Enrollment.objects.create(
            student=recovered_student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=12),
            status=EnrollmentStatus.ACTIVE,
        )

        Payment.objects.create(
            student=stable_student,
            enrollment=stable_enrollment,
            due_date=self.today - timezone.timedelta(days=40),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )
        self._create_finance_touch(student=stable_student, action_kind='overdue', days_ago=0)
        Payment.objects.create(
            student=recovered_student,
            enrollment=recovered_enrollment,
            due_date=self.today - timezone.timedelta(days=5),
            amount='299.90',
            status=PaymentStatus.PAID,
            method=PaymentMethod.PIX,
        )

        foundation = build_financial_churn_foundation(
            students=Student.objects.filter(id__in=[stable_student.id, recovered_student.id]),
            payments=Payment.objects.all(),
            enrollments=Enrollment.objects.all(),
            today=self.today,
            historical_score_map={
                'observe_payment_resolution': 82.5,
                'monitor_recent_reactivation': 41.0,
            },
            recommendation_timing_map={
                'fresh': {
                    'recommended_action': 'observe_payment_resolution',
                    'success_rate': 82.5,
                    'realized_count': 4,
                    'suggestion_window_label': 'Janela pronta para agir',
                },
                'cooling': {
                    'recommended_action': 'monitor_recent_reactivation',
                    'success_rate': 41.0,
                    'realized_count': 2,
                    'suggestion_window_label': 'Janela esfriando',
                },
            },
        )

        self.assertEqual([row['student_name'] for row in foundation['queue_preview'][:2]], ['Bia Regulariza', 'Ciro Retorna'])
        self.assertEqual(foundation['queue_preview'][0]['historical_score'], 82.5)
        self.assertEqual(foundation['queue_preview'][0]['queue_assist_score'], 82.5)
        self.assertEqual(foundation['queue_preview'][0]['priority_rank'], 4)
        self.assertEqual(foundation['queue_preview'][1]['priority_rank'], 4)
        self.assertEqual(foundation['queue_preview'][0]['priority_order_reason'], 'missao_operacional_then_historical_score_then_contextual_score')
        self.assertEqual(foundation['queue_preview'][0]['timing_guidance']['best_action_for_stage'], 'observe_payment_resolution')
        self.assertTrue(foundation['queue_preview'][0]['timing_guidance']['is_aligned_with_best_action'])

    def test_financial_churn_foundation_exposes_contextual_score_as_transparent_tiebreaker_signal(self):
        left_student = Student.objects.create(full_name='Yuri Contexto Forte', phone='5511910000044', status='active')
        right_student = Student.objects.create(full_name='Zeca Contexto Forte', phone='5511910000045', status='active')

        left_enrollment = Enrollment.objects.create(
            student=left_student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=30),
            status=EnrollmentStatus.ACTIVE,
        )
        right_enrollment = Enrollment.objects.create(
            student=right_student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=30),
            status=EnrollmentStatus.ACTIVE,
        )

        Payment.objects.create(
            student=left_student,
            enrollment=left_enrollment,
            due_date=self.today - timezone.timedelta(days=4),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )
        Payment.objects.create(
            student=right_student,
            enrollment=right_enrollment,
            due_date=self.today - timezone.timedelta(days=4),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        foundation = build_financial_churn_foundation(
            students=Student.objects.filter(id__in=[left_student.id, right_student.id]),
            payments=Payment.objects.all(),
            enrollments=Enrollment.objects.all(),
            today=self.today,
            historical_score_map={'monitor_and_nudge': 60.0},
            contextual_recommendation_map={
                ('monitor_and_nudge', 'fresh', 'watch'): {
                    'suggested_action_kind': 'reactivation',
                    'suggested_recommended_action': 'review_winback',
                    'success_rate': 90.0,
                    'realized_count': 3,
                    'rule_name': 'contextual_compound_guidance_v1',
                    'min_success_rate': 70.0,
                },
            },
        )

        row = next(row for row in foundation['queue_preview'] if row['student_name'] == 'Yuri Contexto Forte')
        self.assertEqual(row['priority_order_reason'], 'missao_operacional_then_historical_score_then_contextual_score')
        self.assertEqual(row['contextual_priority_score'], 20.0)
        self.assertEqual(row['contextual_conviction']['level'], 'high')
        self.assertEqual(row['contextual_conviction']['label'], 'Conviccao contextual alta')
        self.assertEqual(row['operational_band']['level'], 'act_with_caution')
        self.assertEqual(row['operational_band']['label'], 'Agir com cautela')

    def test_financial_churn_foundation_reduces_queue_assist_score_when_window_gets_stale(self):
        stale_student = Student.objects.create(full_name='Luca Esfria', phone='5511910000023', status='active')
        fresh_student = Student.objects.create(full_name='Mila Quente', phone='5511910000024', status='active')

        stale_enrollment = Enrollment.objects.create(
            student=stale_student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=60),
            status=EnrollmentStatus.ACTIVE,
        )
        fresh_enrollment = Enrollment.objects.create(
            student=fresh_student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=20),
            status=EnrollmentStatus.ACTIVE,
        )

        Payment.objects.create(
            student=stale_student,
            enrollment=stale_enrollment,
            due_date=self.today - timezone.timedelta(days=16),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )
        Payment.objects.create(
            student=fresh_student,
            enrollment=fresh_enrollment,
            due_date=self.today - timezone.timedelta(days=11),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )
        self._create_finance_touch(student=fresh_student, action_kind='overdue', days_ago=0)

        foundation = build_financial_churn_foundation(
            students=Student.objects.filter(id__in=[stale_student.id, fresh_student.id]),
            payments=Payment.objects.all(),
            enrollments=Enrollment.objects.all(),
            today=self.today,
            historical_score_map={'monitor_and_nudge': 70.0},
        )

        self.assertEqual([row['student_name'] for row in foundation['queue_preview'][:2]], ['Mila Quente', 'Luca Esfria'])
        self.assertEqual(foundation['queue_preview'][0]['recommendation_momentum']['decay_stage'], 'fresh')
        self.assertEqual(foundation['queue_preview'][1]['recommendation_momentum']['decay_stage'], 'stale')
        self.assertLess(
            foundation['queue_preview'][1]['queue_assist_score'],
            foundation['queue_preview'][0]['queue_assist_score'],
        )

    def test_timing_recommendation_override_prefers_action_with_best_windowed_success(self):
        override_map = build_timing_recommendation_override_map(
            {
                'recommendation_timing_matrix': [
                    {
                        'recommended_action': 'monitor_and_nudge',
                        'suggestion_window_stage': 'fresh',
                        'suggestion_window_label': 'Janela pronta para agir',
                        'realized_count': 6,
                        'success_rate': 88.0,
                        'average_queue_assist_score': 60.0,
                    },
                    {
                        'recommended_action': 'send_financial_followup',
                        'suggestion_window_stage': 'fresh',
                        'suggestion_window_label': 'Janela pronta para agir',
                        'realized_count': 6,
                        'success_rate': 84.0,
                        'average_queue_assist_score': 58.0,
                    },
                ],
                'recommendation_window_matrix': [
                    {
                        'recommended_action': 'monitor_and_nudge',
                        'outcome_window': '15d',
                        'realized_count': 6,
                        'success_rate': 71.0,
                    },
                    {
                        'recommended_action': 'send_financial_followup',
                        'outcome_window': '7d',
                        'realized_count': 6,
                        'success_rate': 92.0,
                    },
                ],
            }
        )

        self.assertEqual(override_map['fresh']['recommended_action'], 'send_financial_followup')
        self.assertEqual(override_map['fresh']['preferred_outcome_window'], '7d')
        self.assertEqual(override_map['fresh']['preferred_window_success_rate'], 92.0)

    def test_financial_churn_foundation_adjusts_recommendation_when_timing_history_is_strong(self):
        student = Student.objects.create(full_name='Dani Ajusta', phone='5511910000025', status='active')
        enrollment = Enrollment.objects.create(
            student=student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=45),
            status=EnrollmentStatus.ACTIVE,
        )
        Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=self.today - timezone.timedelta(days=3),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        foundation = build_financial_churn_foundation(
            students=Student.objects.filter(pk=student.pk),
            payments=Payment.objects.all(),
            enrollments=Enrollment.objects.all(),
            today=self.today,
            historical_score_map={
                'monitor_and_nudge': 41.0,
                'send_financial_followup': 84.0,
            },
            recommendation_timing_map={
                'fresh': {
                    'recommended_action': 'send_financial_followup',
                    'success_rate': 84.0,
                    'realized_count': 5,
                    'suggestion_window_label': 'Janela pronta para agir',
                },
            },
            recommendation_timing_lookup_map={
                ('fresh', 'monitor_and_nudge'): {
                    'recommended_action': 'monitor_and_nudge',
                    'success_rate': 52.0,
                    'realized_count': 4,
                },
            },
            recommendation_override_map={
                'fresh': {
                    'recommended_action': 'send_financial_followup',
                    'success_rate': 84.0,
                    'realized_count': 5,
                    'suggestion_window_label': 'Janela pronta para agir',
                    'min_realized_count': 3,
                    'min_success_rate': 70.0,
                    'rule_name': 'timing_override_v1',
                },
            },
        )

        row = foundation['rows'][0]
        self.assertEqual(row['recommended_action_base'], 'monitor_and_nudge')
        self.assertEqual(row['recommended_action'], 'send_financial_followup')
        self.assertTrue(row['recommendation_adjustment']['applied'])
        self.assertEqual(row['recommendation_adjustment']['reason'], 'timing_history_override')
        self.assertEqual(row['recommendation_adjustment']['success_rate_lift'], 32.0)
        self.assertEqual(row['rule_version'], 'finance_queue_v1+timing_override_v1')
        self.assertEqual(row['historical_score'], 84.0)
        self.assertTrue(row['timing_guidance']['is_aligned_with_best_action'])

    def test_financial_churn_foundation_keeps_base_recommendation_when_timing_history_is_weak(self):
        student = Student.objects.create(full_name='Eli Segura', phone='5511910000026', status='active')
        enrollment = Enrollment.objects.create(
            student=student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=45),
            status=EnrollmentStatus.ACTIVE,
        )
        Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=self.today - timezone.timedelta(days=3),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        foundation = build_financial_churn_foundation(
            students=Student.objects.filter(pk=student.pk),
            payments=Payment.objects.all(),
            enrollments=Enrollment.objects.all(),
            today=self.today,
            historical_score_map={
                'monitor_and_nudge': 41.0,
                'send_financial_followup': 84.0,
            },
            recommendation_timing_map={
                'fresh': {
                    'recommended_action': 'send_financial_followup',
                    'success_rate': 84.0,
                    'realized_count': 2,
                    'suggestion_window_label': 'Janela pronta para agir',
                },
            },
            recommendation_timing_lookup_map={
                ('fresh', 'monitor_and_nudge'): {
                    'recommended_action': 'monitor_and_nudge',
                    'success_rate': 52.0,
                    'realized_count': 4,
                },
            },
            recommendation_override_map={},
        )

        row = foundation['rows'][0]
        self.assertEqual(row['recommended_action_base'], 'monitor_and_nudge')
        self.assertEqual(row['recommended_action'], 'monitor_and_nudge')
        self.assertFalse(row['recommendation_adjustment']['applied'])
        self.assertEqual(row['historical_score'], 41.0)
        self.assertFalse(row['timing_guidance']['is_aligned_with_best_action'])

    def test_financial_churn_foundation_promotes_confidence_when_history_is_strong(self):
        student = Student.objects.create(full_name='Fabi Confia', phone='5511910000027', status='active')
        enrollment = Enrollment.objects.create(
            student=student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=45),
            status=EnrollmentStatus.ACTIVE,
        )
        Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=self.today - timezone.timedelta(days=3),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        foundation = build_financial_churn_foundation(
            students=Student.objects.filter(pk=student.pk),
            payments=Payment.objects.all(),
            enrollments=Enrollment.objects.all(),
            today=self.today,
            historical_score_map={
                'monitor_and_nudge': 41.0,
                'send_financial_followup': 84.0,
            },
            recommendation_timing_map={
                'fresh': {
                    'recommended_action': 'send_financial_followup',
                    'success_rate': 84.0,
                    'realized_count': 5,
                    'suggestion_window_label': 'Janela pronta para agir',
                },
            },
            recommendation_timing_lookup_map={
                ('fresh', 'monitor_and_nudge'): {
                    'recommended_action': 'monitor_and_nudge',
                    'success_rate': 52.0,
                    'realized_count': 4,
                },
            },
            recommendation_override_map={
                'fresh': {
                    'recommended_action': 'send_financial_followup',
                    'success_rate': 84.0,
                    'realized_count': 5,
                    'suggestion_window_label': 'Janela pronta para agir',
                    'min_realized_count': 3,
                    'min_success_rate': 70.0,
                    'rule_name': 'timing_override_v1',
                },
            },
        )

        row = foundation['rows'][0]
        self.assertEqual(row['confidence_base'], 'medium')
        self.assertEqual(row['confidence'], 'high')
        self.assertTrue(row['confidence_adjustment']['applied'])
        self.assertEqual(row['confidence_adjustment']['reason'], 'timing_override_with_strong_history')
        self.assertEqual(row['confidence_adjustment']['rule_name'], 'confidence_history_lift_v1')

    def test_financial_churn_foundation_reduces_confidence_when_history_is_low_and_window_is_stale(self):
        student = Student.objects.create(full_name='Guto Frio', phone='5511910000028', status='active')
        enrollment = Enrollment.objects.create(
            student=student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=90),
            status=EnrollmentStatus.ACTIVE,
        )
        Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=self.today - timezone.timedelta(days=20),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        foundation = build_financial_churn_foundation(
            students=Student.objects.filter(pk=student.pk),
            payments=Payment.objects.all(),
            enrollments=Enrollment.objects.all(),
            today=self.today,
            historical_score_map={'monitor_and_nudge': 20.0},
        )

        row = foundation['rows'][0]
        self.assertEqual(row['confidence_base'], 'medium')
        self.assertEqual(row['recommendation_momentum']['decay_stage'], 'stale')
        self.assertEqual(row['confidence'], 'low')
        self.assertTrue(row['confidence_adjustment']['applied'])
        self.assertEqual(row['confidence_adjustment']['reason'], 'stale_window_with_low_history')
        self.assertEqual(row['confidence_adjustment']['rule_name'], 'confidence_history_decay_v1')

    def test_financial_churn_foundation_adjusts_prediction_window_when_action_history_is_strong(self):
        student = Student.objects.create(full_name='Hugo Janela', phone='5511910000029', status='inactive')
        enrollment = Enrollment.objects.create(
            student=student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=80),
            end_date=self.today - timezone.timedelta(days=4),
            status=EnrollmentStatus.CANCELED,
        )
        Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=self.today - timezone.timedelta(days=10),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        foundation = build_financial_churn_foundation(
            students=Student.objects.filter(pk=student.pk),
            payments=Payment.objects.all(),
            enrollments=Enrollment.objects.all(),
            today=self.today,
            prediction_window_override_map={
                'review_winback': {
                    'outcome_window': '15d',
                    'success_rate': 78.0,
                    'realized_count': 4,
                    'rule_name': 'prediction_window_override_v1',
                }
            },
        )

        row = foundation['rows'][0]
        self.assertEqual(row['prediction_window_base'], 'next_30_days')
        self.assertEqual(row['prediction_window'], 'next_15_days')
        self.assertTrue(row['prediction_window_adjustment']['applied'])
        self.assertEqual(row['prediction_window_adjustment']['reason'], 'historical_window_override')
        self.assertEqual(row['prediction_window_adjustment']['rule_name'], 'prediction_window_override_v1')

    def test_financial_churn_foundation_keeps_prediction_window_when_history_does_not_change_it(self):
        student = Student.objects.create(full_name='Iris Janela', phone='5511910000030', status='inactive')
        enrollment = Enrollment.objects.create(
            student=student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=80),
            end_date=self.today - timezone.timedelta(days=4),
            status=EnrollmentStatus.CANCELED,
        )
        Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=self.today - timezone.timedelta(days=10),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        foundation = build_financial_churn_foundation(
            students=Student.objects.filter(pk=student.pk),
            payments=Payment.objects.all(),
            enrollments=Enrollment.objects.all(),
            today=self.today,
            prediction_window_override_map={},
        )

        row = foundation['rows'][0]
        self.assertEqual(row['prediction_window_base'], 'next_30_days')
        self.assertEqual(row['prediction_window'], 'next_30_days')
        self.assertFalse(row['prediction_window_adjustment']['applied'])

    def test_build_finance_snapshot_exposes_follow_up_analytics(self):
        recovered_student = Student.objects.create(full_name='Pietra Pago', phone='5511910000017', status='active')
        inactive_student = Student.objects.create(full_name='Quim Inativo', phone='5511910000018', status='inactive')

        recovered_enrollment = Enrollment.objects.create(
            student=recovered_student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=30),
            status=EnrollmentStatus.ACTIVE,
        )
        inactive_enrollment = Enrollment.objects.create(
            student=inactive_student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=90),
            end_date=self.today - timezone.timedelta(days=2),
            status=EnrollmentStatus.CANCELED,
        )

        recovered_payment = Payment.objects.create(
            student=recovered_student,
            enrollment=recovered_enrollment,
            due_date=self.today - timezone.timedelta(days=10),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )
        inactive_payment = Payment.objects.create(
            student=inactive_student,
            enrollment=inactive_enrollment,
            due_date=self.today - timezone.timedelta(days=20),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        build_finance_snapshot(persist_follow_ups=True)

        handle_finance_communication_action(
            actor=self.user,
            action_kind='overdue',
            student_id=recovered_student.id,
            payment_id=recovered_payment.id,
            enrollment_id=recovered_enrollment.id,
        )
        handle_finance_communication_action(
            actor=self.user,
            action_kind='reactivation',
            student_id=inactive_student.id,
            payment_id=inactive_payment.id,
            enrollment_id=inactive_enrollment.id,
        )

        recovered_payment.status = PaymentStatus.PAID
        recovered_payment.paid_at = timezone.now()
        recovered_payment.save(update_fields=['status', 'paid_at', 'updated_at'])
        inactive_student.status = 'active'
        inactive_student.save(update_fields=['status', 'updated_at'])

        for follow_up in FinanceFollowUp.objects.all():
            follow_up.resolved_at = timezone.now() - timezone.timedelta(days=31)
            follow_up.outcome_window = '30d'
            follow_up.save(update_fields=['resolved_at', 'outcome_window', 'updated_at'])
            evaluate_finance_follow_up_outcome(follow_up_id=follow_up.id)

        snapshot = build_finance_snapshot()
        analytics = snapshot['finance_follow_up_analytics']

        self.assertEqual(analytics['summary']['total_follow_ups'], 2)
        self.assertEqual(analytics['summary']['succeeded_count'], 2)
        self.assertEqual(analytics['recommendation_performance'][0]['success_rate'], 100.0)
        stage_labels = {item['suggestion_window_label'] for item in analytics['window_stage_performance']}
        self.assertIn('Janela pronta para agir', stage_labels)
        self.assertIn('Janela esfriando', stage_labels)
        self.assertTrue(all(item['success_rate'] == 100.0 for item in analytics['window_stage_performance']))
        timing_actions = {
            (item['recommended_action'], item['suggestion_window_label'])
            for item in analytics['recommendation_timing_matrix']
        }
        self.assertIn(('monitor_and_nudge', 'Janela esfriando'), timing_actions)
        self.assertIn(('review_winback', 'Janela pronta para agir'), timing_actions)
        action_kinds = {item['action_kind'] for item in analytics['realized_action_performance']}
        self.assertIn('overdue', action_kinds)
        self.assertIn('reactivation', action_kinds)
        self.assertEqual(analytics['window_performance'][0]['outcome_window'], '30d')

    def test_finance_follow_up_analytics_measures_turn_recommendation_adherence(self):
        aligned_student = Student.objects.create(full_name='Jo Aderente', phone='5511910000031', status='active')
        divergent_student = Student.objects.create(full_name='Kai Diverge', phone='5511910000032', status='active')
        aligned_enrollment = Enrollment.objects.create(student=aligned_student, plan=self.plan, status=EnrollmentStatus.ACTIVE)
        divergent_enrollment = Enrollment.objects.create(student=divergent_student, plan=self.plan, status=EnrollmentStatus.ACTIVE)
        aligned_payment = Payment.objects.create(
            student=aligned_student,
            enrollment=aligned_enrollment,
            due_date=self.today - timezone.timedelta(days=8),
            amount='299.90',
            status=PaymentStatus.PAID,
            method=PaymentMethod.PIX,
            paid_at=timezone.now(),
        )
        divergent_payment = Payment.objects.create(
            student=divergent_student,
            enrollment=divergent_enrollment,
            due_date=self.today - timezone.timedelta(days=8),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        FinanceFollowUp.objects.create(
            student=aligned_student,
            payment=aligned_payment,
            enrollment=aligned_enrollment,
            suggestion_key='aligned',
            source_surface='finance_queue',
            recommended_action='send_financial_followup',
            confidence='high',
            prediction_window='next_7_days',
            rule_version='finance_queue_v1',
            status=FinanceFollowUpStatus.REALIZED,
            realized_action_kind='overdue',
            outcome_status=FinanceFollowUpOutcomeStatus.SUCCEEDED,
            outcome_window='7d',
            payload={'turn_recommendation': {'action_kind': 'overdue'}},
        )
        FinanceFollowUp.objects.create(
            student=divergent_student,
            payment=divergent_payment,
            enrollment=divergent_enrollment,
            suggestion_key='divergent',
            source_surface='finance_queue',
            recommended_action='review_winback',
            confidence='high',
            prediction_window='next_30_days',
            rule_version='finance_queue_v1',
            status=FinanceFollowUpStatus.REALIZED,
            realized_action_kind='reactivation',
            outcome_status=FinanceFollowUpOutcomeStatus.FAILED,
            outcome_window='30d',
            payload={'turn_recommendation': {'action_kind': 'overdue'}},
        )

        analytics = build_finance_follow_up_analytics(
            follow_ups=FinanceFollowUp.objects.filter(source_surface='finance_queue')
        )

        self.assertEqual(analytics['turn_recommendation_adherence']['tracked_realized_count'], 2)
        self.assertEqual(analytics['turn_recommendation_adherence']['aligned_count'], 1)
        self.assertEqual(analytics['turn_recommendation_adherence']['divergent_count'], 1)
        self.assertEqual(analytics['turn_recommendation_adherence']['adherence_rate'], 50.0)
        self.assertEqual(analytics['turn_recommendation_outcome']['aligned']['success_rate'], 100.0)
        self.assertEqual(analytics['turn_recommendation_outcome']['aligned']['succeeded_count'], 1)
        self.assertEqual(analytics['turn_recommendation_outcome']['divergent']['success_rate'], 0.0)
        self.assertEqual(analytics['turn_recommendation_outcome']['divergent']['failed_count'], 1)
        self.assertEqual(analytics['turn_recommendation_learning']['smart_divergence']['realized_count'], 0)
        self.assertEqual(analytics['turn_recommendation_learning']['smart_divergence']['success_rate'], 0.0)
        self.assertEqual(analytics['turn_recommendation_learning']['bad_divergence']['realized_count'], 1)
        self.assertEqual(analytics['turn_recommendation_learning']['bad_divergence']['failure_rate'], 100.0)

    def test_finance_follow_up_analytics_identifies_smart_and_bad_divergence(self):
        smart_student = Student.objects.create(full_name='Lia Fora da Curva', phone='5511910000033', status='active')
        bad_student = Student.objects.create(full_name='Miro Saiu Mal', phone='5511910000034', status='active')
        smart_enrollment = Enrollment.objects.create(student=smart_student, plan=self.plan, status=EnrollmentStatus.ACTIVE)
        bad_enrollment = Enrollment.objects.create(student=bad_student, plan=self.plan, status=EnrollmentStatus.ACTIVE)
        smart_payment = Payment.objects.create(
            student=smart_student,
            enrollment=smart_enrollment,
            due_date=self.today - timezone.timedelta(days=6),
            amount='299.90',
            status=PaymentStatus.PAID,
            method=PaymentMethod.PIX,
            paid_at=timezone.now(),
        )
        bad_payment = Payment.objects.create(
            student=bad_student,
            enrollment=bad_enrollment,
            due_date=self.today - timezone.timedelta(days=6),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        FinanceFollowUp.objects.create(
            student=smart_student,
            payment=smart_payment,
            enrollment=smart_enrollment,
            suggestion_key='smart-divergence',
            source_surface='finance_queue',
            recommended_action='send_financial_followup',
            confidence='medium',
            prediction_window='next_7_days',
            rule_version='finance_queue_v1',
            status=FinanceFollowUpStatus.REALIZED,
            realized_action_kind='reactivation',
            outcome_status=FinanceFollowUpOutcomeStatus.SUCCEEDED,
            outcome_window='7d',
            payload={'turn_recommendation': {'action_kind': 'overdue'}},
        )
        FinanceFollowUp.objects.create(
            student=bad_student,
            payment=bad_payment,
            enrollment=bad_enrollment,
            suggestion_key='bad-divergence',
            source_surface='finance_queue',
            recommended_action='send_financial_followup',
            confidence='medium',
            prediction_window='next_7_days',
            rule_version='finance_queue_v1',
            status=FinanceFollowUpStatus.REALIZED,
            realized_action_kind='reactivation',
            outcome_status=FinanceFollowUpOutcomeStatus.FAILED,
            outcome_window='7d',
            payload={'turn_recommendation': {'action_kind': 'overdue'}},
        )

        analytics = build_finance_follow_up_analytics(
            follow_ups=FinanceFollowUp.objects.filter(source_surface='finance_queue')
        )

        self.assertEqual(analytics['turn_recommendation_learning']['smart_divergence']['realized_count'], 1)
        self.assertEqual(analytics['turn_recommendation_learning']['smart_divergence']['success_rate'], 50.0)
        self.assertIn('acertou a mao', analytics['turn_recommendation_learning']['smart_divergence']['summary'])
        self.assertEqual(analytics['turn_recommendation_learning']['bad_divergence']['realized_count'], 1)
        self.assertEqual(analytics['turn_recommendation_learning']['bad_divergence']['failure_rate'], 50.0)
        self.assertIn('tirou a operacao da melhor linha', analytics['turn_recommendation_learning']['bad_divergence']['summary'])
        self.assertEqual(analytics['divergence_timing_matrix'][0]['suggestion_window_stage'], 'unknown')
        self.assertEqual(analytics['divergence_timing_matrix'][0]['smart_divergence_count'], 1)
        self.assertEqual(analytics['divergence_timing_matrix'][0]['bad_divergence_count'], 1)

    def test_finance_follow_up_analytics_measures_turn_priority_tension_outcome(self):
        aligned_student = Student.objects.create(full_name='Lia Alinhada', phone='5511910000091', status='active')
        tension_success_student = Student.objects.create(full_name='Tio Tensiona Bem', phone='5511910000092', status='active')
        tension_fail_student = Student.objects.create(full_name='Tio Tensiona Mal', phone='5511910000093', status='active')
        aligned_enrollment = Enrollment.objects.create(student=aligned_student, plan=self.plan, status=EnrollmentStatus.ACTIVE)
        tension_success_enrollment = Enrollment.objects.create(student=tension_success_student, plan=self.plan, status=EnrollmentStatus.ACTIVE)
        tension_fail_enrollment = Enrollment.objects.create(student=tension_fail_student, plan=self.plan, status=EnrollmentStatus.ACTIVE)

        FinanceFollowUp.objects.create(
            student=aligned_student,
            enrollment=aligned_enrollment,
            source_surface='finance_queue',
            suggestion_key='aligned-priority',
            signal_bucket='high_signal',
            recommended_action='send_financial_followup',
            status=FinanceFollowUpStatus.REALIZED,
            realized_action_kind='overdue',
            confidence='high',
            prediction_window='next_7_days',
            rule_version='rule-v1',
            outcome_status=FinanceFollowUpOutcomeStatus.SUCCEEDED,
            outcome_window='7d',
            payload={
                'signal_bucket': 'high_signal',
                'turn_recommendation': {'action_kind': 'overdue'},
                'turn_priority': {'alignment_status': 'aligned'},
            },
        )
        FinanceFollowUp.objects.create(
            student=tension_success_student,
            enrollment=tension_success_enrollment,
            source_surface='finance_queue',
            suggestion_key='tension-success',
            signal_bucket='watch',
            recommended_action='review_winback',
            status=FinanceFollowUpStatus.REALIZED,
            realized_action_kind='reactivation',
            confidence='medium',
            prediction_window='next_30_days',
            rule_version='rule-v1',
            outcome_status=FinanceFollowUpOutcomeStatus.SUCCEEDED,
            outcome_window='30d',
            payload={
                'signal_bucket': 'watch',
                'turn_recommendation': {'action_kind': 'overdue'},
                'turn_priority': {'alignment_status': 'tension'},
            },
        )
        FinanceFollowUp.objects.create(
            student=tension_fail_student,
            enrollment=tension_fail_enrollment,
            source_surface='finance_queue',
            suggestion_key='tension-fail',
            signal_bucket='watch',
            recommended_action='review_winback',
            status=FinanceFollowUpStatus.REALIZED,
            realized_action_kind='reactivation',
            confidence='medium',
            prediction_window='next_30_days',
            rule_version='rule-v1',
            outcome_status=FinanceFollowUpOutcomeStatus.FAILED,
            outcome_window='30d',
            payload={
                'signal_bucket': 'watch',
                'turn_recommendation': {'action_kind': 'overdue'},
                'turn_priority': {'alignment_status': 'tension'},
            },
        )

        analytics = build_finance_follow_up_analytics(
            follow_ups=FinanceFollowUp.objects.filter(source_surface='finance_queue')
        )

        self.assertEqual(analytics['turn_priority_outcome']['aligned']['success_rate'], 100.0)
        self.assertEqual(analytics['turn_priority_outcome']['tension']['realized_count'], 2)
        self.assertEqual(analytics['turn_priority_outcome']['tension']['success_rate'], 50.0)
        self.assertEqual(analytics['turn_priority_learning']['healthy_tension']['realized_count'], 1)
        self.assertEqual(analytics['turn_priority_learning']['healthy_tension']['success_rate'], 50.0)
        self.assertIn('adaptacao humana', analytics['turn_priority_learning']['healthy_tension']['summary'])
        self.assertEqual(analytics['turn_priority_learning']['dangerous_tension']['realized_count'], 1)
        self.assertEqual(analytics['turn_priority_learning']['dangerous_tension']['failure_rate'], 50.0)
        self.assertIn('dispersou a execucao', analytics['turn_priority_learning']['dangerous_tension']['summary'])
        self.assertEqual(analytics['turn_priority_tension_timing_matrix'][0]['suggestion_window_stage'], 'unknown')
        self.assertEqual(analytics['turn_priority_tension_timing_matrix'][0]['healthy_tension_rate'], 50.0)
        self.assertEqual(analytics['turn_priority_tension_timing_matrix'][0]['dangerous_tension_rate'], 50.0)
        self.assertEqual(analytics['turn_priority_tension_signal_bucket_matrix'][0]['signal_bucket'], 'watch')
        self.assertEqual(analytics['turn_priority_tension_signal_bucket_matrix'][0]['healthy_tension_rate'], 50.0)
        self.assertEqual(analytics['turn_priority_tension_signal_bucket_matrix'][0]['dangerous_tension_rate'], 50.0)
        self.assertEqual(analytics['turn_priority_tension_compound_matrix'][0]['suggestion_window_stage'], 'unknown')
        self.assertEqual(analytics['turn_priority_tension_compound_matrix'][0]['signal_bucket'], 'watch')
        self.assertEqual(analytics['turn_priority_tension_compound_matrix'][0]['healthy_tension_rate'], 50.0)
        self.assertEqual(analytics['turn_priority_tension_compound_matrix'][0]['dangerous_tension_rate'], 50.0)

    def test_finance_follow_up_analytics_crosses_divergence_with_timing(self):
        fresh_student = Student.objects.create(full_name='Nina Fresh', phone='5511910000035', status='active')
        stale_student = Student.objects.create(full_name='Otto Stale', phone='5511910000036', status='active')
        fresh_enrollment = Enrollment.objects.create(student=fresh_student, plan=self.plan, status=EnrollmentStatus.ACTIVE)
        stale_enrollment = Enrollment.objects.create(student=stale_student, plan=self.plan, status=EnrollmentStatus.ACTIVE)
        fresh_payment = Payment.objects.create(
            student=fresh_student,
            enrollment=fresh_enrollment,
            due_date=self.today - timezone.timedelta(days=4),
            amount='299.90',
            status=PaymentStatus.PAID,
            method=PaymentMethod.PIX,
            paid_at=timezone.now(),
        )
        stale_payment = Payment.objects.create(
            student=stale_student,
            enrollment=stale_enrollment,
            due_date=self.today - timezone.timedelta(days=25),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        FinanceFollowUp.objects.create(
            student=fresh_student,
            payment=fresh_payment,
            enrollment=fresh_enrollment,
            suggestion_key='fresh-smart',
            source_surface='finance_queue',
            recommended_action='send_financial_followup',
            confidence='medium',
            prediction_window='next_7_days',
            rule_version='finance_queue_v1',
            status=FinanceFollowUpStatus.REALIZED,
            realized_action_kind='reactivation',
            outcome_status=FinanceFollowUpOutcomeStatus.SUCCEEDED,
            outcome_window='7d',
            suggestion_window_stage='fresh',
            suggestion_window_label='Janela pronta para agir',
            payload={'turn_recommendation': {'action_kind': 'overdue'}},
        )
        FinanceFollowUp.objects.create(
            student=stale_student,
            payment=stale_payment,
            enrollment=stale_enrollment,
            suggestion_key='stale-bad',
            source_surface='finance_queue',
            recommended_action='send_financial_followup',
            confidence='low',
            prediction_window='next_15_days',
            rule_version='finance_queue_v1',
            status=FinanceFollowUpStatus.REALIZED,
            realized_action_kind='reactivation',
            outcome_status=FinanceFollowUpOutcomeStatus.FAILED,
            outcome_window='15d',
            suggestion_window_stage='stale',
            suggestion_window_label='Passou da janela ideal',
            payload={'turn_recommendation': {'action_kind': 'overdue'}},
        )

        analytics = build_finance_follow_up_analytics(
            follow_ups=FinanceFollowUp.objects.filter(source_surface='finance_queue')
        )

        timing_map = {
            item['suggestion_window_stage']: item
            for item in analytics['divergence_timing_matrix']
        }
        self.assertEqual(timing_map['fresh']['smart_divergence_rate'], 100.0)
        self.assertEqual(timing_map['fresh']['bad_divergence_rate'], 0.0)
        self.assertEqual(timing_map['stale']['smart_divergence_rate'], 0.0)
        self.assertEqual(timing_map['stale']['bad_divergence_rate'], 100.0)

    def test_finance_follow_up_analytics_crosses_divergence_with_recommended_action(self):
        send_student = Student.objects.create(full_name='Pia Seguiria', phone='5511910000037', status='active')
        review_student = Student.objects.create(full_name='Rui Quebrou Linha', phone='5511910000038', status='active')
        send_enrollment = Enrollment.objects.create(student=send_student, plan=self.plan, status=EnrollmentStatus.ACTIVE)
        review_enrollment = Enrollment.objects.create(student=review_student, plan=self.plan, status=EnrollmentStatus.ACTIVE)
        send_payment = Payment.objects.create(
            student=send_student,
            enrollment=send_enrollment,
            due_date=self.today - timezone.timedelta(days=5),
            amount='299.90',
            status=PaymentStatus.PAID,
            method=PaymentMethod.PIX,
            paid_at=timezone.now(),
        )
        review_payment = Payment.objects.create(
            student=review_student,
            enrollment=review_enrollment,
            due_date=self.today - timezone.timedelta(days=18),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        FinanceFollowUp.objects.create(
            student=send_student,
            payment=send_payment,
            enrollment=send_enrollment,
            suggestion_key='send-smart',
            source_surface='finance_queue',
            recommended_action='send_financial_followup',
            confidence='medium',
            prediction_window='next_7_days',
            rule_version='finance_queue_v1',
            status=FinanceFollowUpStatus.REALIZED,
            realized_action_kind='reactivation',
            outcome_status=FinanceFollowUpOutcomeStatus.SUCCEEDED,
            outcome_window='7d',
            payload={'turn_recommendation': {'action_kind': 'overdue'}},
        )
        FinanceFollowUp.objects.create(
            student=review_student,
            payment=review_payment,
            enrollment=review_enrollment,
            suggestion_key='review-bad',
            source_surface='finance_queue',
            recommended_action='review_winback',
            confidence='low',
            prediction_window='next_30_days',
            rule_version='finance_queue_v1',
            status=FinanceFollowUpStatus.REALIZED,
            realized_action_kind='overdue',
            outcome_status=FinanceFollowUpOutcomeStatus.FAILED,
            outcome_window='30d',
            payload={'turn_recommendation': {'action_kind': 'reactivation'}},
        )

        analytics = build_finance_follow_up_analytics(
            follow_ups=FinanceFollowUp.objects.filter(source_surface='finance_queue')
        )

        action_map = {
            item['recommended_action']: item
            for item in analytics['divergence_action_matrix']
        }
        self.assertEqual(action_map['send_financial_followup']['smart_divergence_rate'], 100.0)
        self.assertEqual(action_map['send_financial_followup']['bad_divergence_rate'], 0.0)
        self.assertEqual(action_map['review_winback']['smart_divergence_rate'], 0.0)
        self.assertEqual(action_map['review_winback']['bad_divergence_rate'], 100.0)

    def test_finance_follow_up_analytics_crosses_divergence_with_signal_bucket(self):
        high_signal_student = Student.objects.create(full_name='Sia Alto Risco', phone='5511910000039', status='active')
        recovered_student = Student.objects.create(full_name='Teo Recuperado', phone='5511910000040', status='active')
        high_signal_enrollment = Enrollment.objects.create(student=high_signal_student, plan=self.plan, status=EnrollmentStatus.ACTIVE)
        recovered_enrollment = Enrollment.objects.create(student=recovered_student, plan=self.plan, status=EnrollmentStatus.ACTIVE)
        high_signal_payment = Payment.objects.create(
            student=high_signal_student,
            enrollment=high_signal_enrollment,
            due_date=self.today - timezone.timedelta(days=12),
            amount='299.90',
            status=PaymentStatus.PAID,
            method=PaymentMethod.PIX,
            paid_at=timezone.now(),
        )
        recovered_payment = Payment.objects.create(
            student=recovered_student,
            enrollment=recovered_enrollment,
            due_date=self.today - timezone.timedelta(days=3),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        FinanceFollowUp.objects.create(
            student=high_signal_student,
            payment=high_signal_payment,
            enrollment=high_signal_enrollment,
            suggestion_key='high-signal-smart',
            source_surface='finance_queue',
            recommended_action='send_financial_followup',
            confidence='high',
            prediction_window='next_7_days',
            rule_version='finance_queue_v1',
            status=FinanceFollowUpStatus.REALIZED,
            realized_action_kind='reactivation',
            outcome_status=FinanceFollowUpOutcomeStatus.SUCCEEDED,
            outcome_window='7d',
            payload={
                'signal_bucket': 'high_signal',
                'turn_recommendation': {'action_kind': 'overdue'},
            },
        )
        FinanceFollowUp.objects.create(
            student=recovered_student,
            payment=recovered_payment,
            enrollment=recovered_enrollment,
            suggestion_key='recovered-bad',
            source_surface='finance_queue',
            recommended_action='monitor_recent_reactivation',
            confidence='low',
            prediction_window='next_15_days',
            rule_version='finance_queue_v1',
            status=FinanceFollowUpStatus.REALIZED,
            realized_action_kind='overdue',
            outcome_status=FinanceFollowUpOutcomeStatus.FAILED,
            outcome_window='15d',
            payload={
                'signal_bucket': 'recovered',
                'turn_recommendation': {'action_kind': 'reactivation'},
            },
        )

        analytics = build_finance_follow_up_analytics(
            follow_ups=FinanceFollowUp.objects.filter(source_surface='finance_queue')
        )

        bucket_map = {
            item['signal_bucket']: item
            for item in analytics['divergence_signal_bucket_matrix']
        }
        self.assertEqual(bucket_map['high_signal']['smart_divergence_rate'], 100.0)
        self.assertEqual(bucket_map['high_signal']['bad_divergence_rate'], 0.0)
        self.assertEqual(bucket_map['recovered']['smart_divergence_rate'], 0.0)
        self.assertEqual(bucket_map['recovered']['bad_divergence_rate'], 100.0)

    def test_finance_follow_up_analytics_builds_compound_divergence_matrix(self):
        smart_student = Student.objects.create(full_name='Uli Composto Bom', phone='5511910000041', status='active')
        bad_student = Student.objects.create(full_name='Vera Composto Ruim', phone='5511910000042', status='active')
        smart_enrollment = Enrollment.objects.create(student=smart_student, plan=self.plan, status=EnrollmentStatus.ACTIVE)
        bad_enrollment = Enrollment.objects.create(student=bad_student, plan=self.plan, status=EnrollmentStatus.ACTIVE)
        smart_payment = Payment.objects.create(
            student=smart_student,
            enrollment=smart_enrollment,
            due_date=self.today - timezone.timedelta(days=5),
            amount='299.90',
            status=PaymentStatus.PAID,
            method=PaymentMethod.PIX,
            paid_at=timezone.now(),
        )
        bad_payment = Payment.objects.create(
            student=bad_student,
            enrollment=bad_enrollment,
            due_date=self.today - timezone.timedelta(days=22),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        FinanceFollowUp.objects.create(
            student=smart_student,
            payment=smart_payment,
            enrollment=smart_enrollment,
            suggestion_key='compound-smart',
            source_surface='finance_queue',
            recommended_action='send_financial_followup',
            confidence='medium',
            prediction_window='next_7_days',
            rule_version='finance_queue_v1',
            status=FinanceFollowUpStatus.REALIZED,
            realized_action_kind='reactivation',
            outcome_status=FinanceFollowUpOutcomeStatus.SUCCEEDED,
            outcome_window='7d',
            suggestion_window_stage='fresh',
            suggestion_window_label='Janela pronta para agir',
            payload={
                'signal_bucket': 'high_signal',
                'turn_recommendation': {'action_kind': 'overdue'},
            },
        )
        FinanceFollowUp.objects.create(
            student=bad_student,
            payment=bad_payment,
            enrollment=bad_enrollment,
            suggestion_key='compound-bad',
            source_surface='finance_queue',
            recommended_action='review_winback',
            confidence='low',
            prediction_window='next_30_days',
            rule_version='finance_queue_v1',
            status=FinanceFollowUpStatus.REALIZED,
            realized_action_kind='overdue',
            outcome_status=FinanceFollowUpOutcomeStatus.FAILED,
            outcome_window='30d',
            suggestion_window_stage='stale',
            suggestion_window_label='Passou da janela ideal',
            payload={
                'signal_bucket': 'recovered',
                'turn_recommendation': {'action_kind': 'reactivation'},
            },
        )

        analytics = build_finance_follow_up_analytics(
            follow_ups=FinanceFollowUp.objects.filter(source_surface='finance_queue')
        )

        compound_map = {
            (item['recommended_action'], item['suggestion_window_stage'], item['signal_bucket']): item
            for item in analytics['divergence_compound_matrix']
        }
        self.assertEqual(
            compound_map[('send_financial_followup', 'fresh', 'high_signal')]['smart_divergence_rate'],
            100.0,
        )
        self.assertEqual(
            compound_map[('send_financial_followup', 'fresh', 'high_signal')]['bad_divergence_rate'],
            0.0,
        )
        self.assertEqual(
            compound_map[('review_winback', 'stale', 'recovered')]['smart_divergence_rate'],
            0.0,
        )
        self.assertEqual(
            compound_map[('review_winback', 'stale', 'recovered')]['bad_divergence_rate'],
            100.0,
        )

    def test_build_contextual_recommendation_map_prefers_best_compound_action(self):
        analytics = {
            'compound_divergent_action_matrix': [
                {
                    'recommended_action': 'monitor_and_nudge',
                    'suggestion_window_stage': 'fresh',
                    'signal_bucket': 'high_signal',
                    'realized_action_kind': 'overdue',
                    'realized_count': 2,
                    'success_rate': 75.0,
                },
                {
                    'recommended_action': 'monitor_and_nudge',
                    'suggestion_window_stage': 'fresh',
                    'signal_bucket': 'high_signal',
                    'realized_action_kind': 'reactivation',
                    'realized_count': 3,
                    'success_rate': 100.0,
                },
            ]
        }

        contextual_map = build_contextual_recommendation_map(analytics)

        guidance = contextual_map[('monitor_and_nudge', 'fresh', 'high_signal')]
        self.assertEqual(guidance['suggested_action_kind'], 'reactivation')
        self.assertEqual(guidance['suggested_recommended_action'], 'review_winback')
        self.assertEqual(guidance['success_rate'], 100.0)
        self.assertEqual(guidance['realized_count'], 3)

    def test_financial_churn_foundation_exposes_contextual_guidance_on_queue_row(self):
        student = Student.objects.create(full_name='Wes Contexto', phone='5511910000043', status='active')
        enrollment = Enrollment.objects.create(
            student=student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=40),
            status=EnrollmentStatus.ACTIVE,
        )
        Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=self.today - timezone.timedelta(days=4),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        foundation = build_financial_churn_foundation(
            students=Student.objects.filter(pk=student.pk),
            payments=Payment.objects.all(),
            enrollments=Enrollment.objects.all(),
            today=self.today,
            contextual_recommendation_map={
                ('monitor_and_nudge', 'fresh', 'watch'): {
                    'suggested_action_kind': 'reactivation',
                    'suggested_recommended_action': 'review_winback',
                    'success_rate': 83.0,
                    'realized_count': 2,
                    'rule_name': 'contextual_compound_guidance_v1',
                }
            },
        )

        row = foundation['rows'][0]
        self.assertTrue(row['contextual_guidance']['available'])
        self.assertTrue(row['contextual_guidance']['applied'])
        self.assertEqual(row['contextual_guidance']['suggested_recommended_action'], 'review_winback')
        self.assertEqual(row['contextual_guidance']['success_rate'], 83.0)

    def test_financial_churn_foundation_exposes_turn_priority_tension_guidance_on_queue_row(self):
        student = Student.objects.create(full_name='Tina Tensa', phone='5511910000049', status='active')
        enrollment = Enrollment.objects.create(
            student=student,
            plan=self.plan,
            start_date=self.today - timezone.timedelta(days=40),
            status=EnrollmentStatus.ACTIVE,
        )
        Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=self.today - timezone.timedelta(days=4),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        tension_success_student = Student.objects.create(full_name='Tensao Bem', phone='5511910000050', status='active')
        tension_fail_student = Student.objects.create(full_name='Tensao Mal', phone='5511910000051', status='active')
        tension_success_enrollment = Enrollment.objects.create(student=tension_success_student, plan=self.plan, status=EnrollmentStatus.ACTIVE)
        tension_fail_enrollment = Enrollment.objects.create(student=tension_fail_student, plan=self.plan, status=EnrollmentStatus.ACTIVE)
        FinanceFollowUp.objects.create(
            student=tension_success_student,
            enrollment=tension_success_enrollment,
            source_surface='finance_queue',
            suggestion_key='queue-tension-success',
            signal_bucket='watch',
            recommended_action='review_winback',
            status=FinanceFollowUpStatus.REALIZED,
            realized_action_kind='reactivation',
            confidence='medium',
            prediction_window='next_30_days',
            rule_version='rule-v1',
            outcome_status=FinanceFollowUpOutcomeStatus.SUCCEEDED,
            outcome_window='30d',
            suggestion_window_stage='fresh',
            suggestion_window_label='Janela pronta para agir',
            payload={
                'signal_bucket': 'watch',
                'turn_recommendation': {'action_kind': 'overdue'},
                'turn_priority': {'alignment_status': 'tension'},
            },
        )
        FinanceFollowUp.objects.create(
            student=tension_fail_student,
            enrollment=tension_fail_enrollment,
            source_surface='finance_queue',
            suggestion_key='queue-tension-fail',
            signal_bucket='watch',
            recommended_action='review_winback',
            status=FinanceFollowUpStatus.REALIZED,
            realized_action_kind='reactivation',
            confidence='medium',
            prediction_window='next_30_days',
            rule_version='rule-v1',
            outcome_status=FinanceFollowUpOutcomeStatus.FAILED,
            outcome_window='30d',
            suggestion_window_stage='fresh',
            suggestion_window_label='Janela pronta para agir',
            payload={
                'signal_bucket': 'watch',
                'turn_recommendation': {'action_kind': 'overdue'},
                'turn_priority': {'alignment_status': 'tension'},
            },
        )

        analytics = build_finance_follow_up_analytics(
            follow_ups=FinanceFollowUp.objects.filter(source_surface='finance_queue')
        )
        foundation = build_financial_churn_foundation(
            students=Student.objects.filter(pk=student.pk),
            payments=Payment.objects.all(),
            enrollments=Enrollment.objects.all(),
            today=self.today,
            turn_priority_tension_context_map=build_turn_priority_tension_context_map(
                analytics,
                min_realized_count=2,
                min_rate_gap=0.0,
            ),
        )

        row = foundation['rows'][0]
        self.assertTrue(row['turn_priority_tension_guidance']['available'])
        self.assertEqual(row['turn_priority_tension_guidance']['tendency'], 'mixed')
        self.assertEqual(row['turn_priority_tension_guidance']['realized_count'], 2)
        self.assertIn('ainda nao mostra lado dominante', row['turn_priority_tension_guidance']['note'])
