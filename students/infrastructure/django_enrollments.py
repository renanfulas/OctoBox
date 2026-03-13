"""
ARQUIVO: adapters Django do motor de matrícula do aluno.

POR QUE ELE EXISTE:
- Isola a orquestração concreta de matrícula, troca de plano e cobrança inicial abaixo da camada de aplicação.

O QUE ESTE ARQUIVO FAZ:
1. Sincroniza matrícula com plano e status comercial.
2. Cancela e reativa matrícula preservando histórico.
3. Reusa o motor financeiro desacoplado para gerar cobrança.

PONTOS CRITICOS:
- Este arquivo concentra ORM e transação do domínio comercial de matrícula.
"""

from django.db import transaction

from students.application.commands import StudentEnrollmentActionCommand, StudentEnrollmentSyncCommand
from students.application.ports import ClockPort, StudentEnrollmentWorkflowPort
from students.application.results import EnrollmentSyncRecord, StudentEnrollmentActionResult
from students.application.use_cases import execute_student_enrollment_sync_use_case
from students.domain import (
    append_enrollment_note,
    build_enrollment_cancellation_decision,
    build_enrollment_reactivation_decision,
    build_enrollment_sync_decision,
    resolve_enrollment_sync_defaults,
)
from students.infrastructure.django_clock import DjangoClockPort
from students.application.commands import StudentPaymentScheduleCommand
from students.infrastructure.django_payments import execute_student_payment_schedule_command
from finance.models import Enrollment, EnrollmentStatus, MembershipPlan, PaymentStatus
from students.models import Student


class DjangoStudentEnrollmentWorkflowPort(StudentEnrollmentWorkflowPort):
    def __init__(self, *, clock: ClockPort):
        self.clock = clock

    @transaction.atomic
    def sync(self, command: StudentEnrollmentSyncCommand) -> EnrollmentSyncRecord:
        student = Student.objects.select_for_update().get(pk=command.student_id)
        latest_enrollment = student.enrollments.select_related('plan').select_for_update().order_by('-start_date', '-created_at').first()
        selected_plan = MembershipPlan.objects.get(pk=command.selected_plan_id) if command.selected_plan_id is not None else None
        sync_defaults = resolve_enrollment_sync_defaults(
            enrollment_status=command.enrollment_status,
            due_date=command.due_date,
            payment_method=command.payment_method,
            billing_strategy=command.billing_strategy,
            installment_total=command.installment_total,
            recurrence_cycles=command.recurrence_cycles,
            initial_payment_amount=command.initial_payment_amount,
            selected_plan_price=getattr(selected_plan, 'price', None),
            today=self.clock.today(),
        )

        if selected_plan is None:
            return EnrollmentSyncRecord(enrollment_id=None, payment_id=None, movement='none')

        decision = build_enrollment_sync_decision(
            has_current_enrollment=latest_enrollment is not None,
            same_plan=latest_enrollment is not None and latest_enrollment.plan_id == selected_plan.id,
            previous_price=getattr(getattr(latest_enrollment, 'plan', None), 'price', None),
            selected_price=selected_plan.price,
        )

        if latest_enrollment is None:
            enrollment = Enrollment.objects.create(
                student=student,
                plan=selected_plan,
                status=sync_defaults.enrollment_status,
                start_date=self.clock.today(),
                notes=decision.new_enrollment_note,
            )
            payment_result = execute_student_payment_schedule_command(
                StudentPaymentScheduleCommand(
                    student_id=student.id,
                    enrollment_id=enrollment.id,
                    due_date=sync_defaults.due_date,
                    payment_method=sync_defaults.payment_method,
                    confirm_payment_now=command.confirm_payment_now,
                    note=decision.payment_note or '',
                    amount=sync_defaults.base_amount,
                    reference=command.payment_reference,
                    billing_strategy=sync_defaults.billing_strategy,
                    installment_total=sync_defaults.installment_total,
                    recurrence_cycles=sync_defaults.recurrence_cycles,
                )
            )
            return EnrollmentSyncRecord(
                enrollment_id=enrollment.id,
                payment_id=payment_result.payment_id,
                movement=decision.movement,
            )

        if latest_enrollment.plan_id == selected_plan.id:
            latest_enrollment.plan = selected_plan
            latest_enrollment.status = sync_defaults.enrollment_status
            if latest_enrollment.start_date is None:
                latest_enrollment.start_date = self.clock.today()
            latest_enrollment.save(update_fields=['plan', 'status', 'start_date', 'updated_at'])

            payment_id = None
            if not latest_enrollment.payments.exists():
                payment_result = execute_student_payment_schedule_command(
                    StudentPaymentScheduleCommand(
                        student_id=student.id,
                        enrollment_id=latest_enrollment.id,
                        due_date=sync_defaults.due_date,
                        payment_method=sync_defaults.payment_method,
                        confirm_payment_now=command.confirm_payment_now,
                        note=decision.payment_note or '',
                        amount=sync_defaults.base_amount,
                        reference=command.payment_reference,
                        billing_strategy=sync_defaults.billing_strategy,
                        installment_total=sync_defaults.installment_total,
                        recurrence_cycles=sync_defaults.recurrence_cycles,
                    )
                )
                payment_id = payment_result.payment_id

            return EnrollmentSyncRecord(
                enrollment_id=latest_enrollment.id,
                payment_id=payment_id,
                movement=decision.movement,
            )

        latest_enrollment.status = EnrollmentStatus.EXPIRED
        latest_enrollment.end_date = self.clock.today()
        latest_enrollment.notes = append_enrollment_note(
            latest_enrollment.notes,
            decision.current_enrollment_closing_note or '',
        )
        latest_enrollment.save(update_fields=['status', 'end_date', 'notes', 'updated_at'])

        enrollment = Enrollment.objects.create(
            student=student,
            plan=selected_plan,
            status=sync_defaults.enrollment_status,
            start_date=self.clock.today(),
            notes=decision.new_enrollment_note,
        )
        payment_result = execute_student_payment_schedule_command(
            StudentPaymentScheduleCommand(
                student_id=student.id,
                enrollment_id=enrollment.id,
                due_date=sync_defaults.due_date,
                payment_method=sync_defaults.payment_method,
                confirm_payment_now=command.confirm_payment_now,
                note=decision.payment_note or '',
                amount=sync_defaults.base_amount,
                reference=command.payment_reference,
                billing_strategy=sync_defaults.billing_strategy,
                installment_total=sync_defaults.installment_total,
                recurrence_cycles=sync_defaults.recurrence_cycles,
            )
        )
        return EnrollmentSyncRecord(
            enrollment_id=enrollment.id,
            payment_id=payment_result.payment_id,
            movement=decision.movement,
        )


@transaction.atomic
def cancel_student_enrollment_command(command: StudentEnrollmentActionCommand) -> StudentEnrollmentActionResult:
    enrollment = Enrollment.objects.select_for_update().get(pk=command.enrollment_id)
    decision = build_enrollment_cancellation_decision(action_date=command.action_date, reason=command.reason)
    enrollment.status = decision.status
    enrollment.end_date = decision.end_date
    enrollment.notes = append_enrollment_note(enrollment.notes, decision.note)
    enrollment.save(update_fields=['status', 'end_date', 'notes', 'updated_at'])
    enrollment.payments.filter(
        status=PaymentStatus.PENDING,
        due_date__gte=decision.cancel_pending_from_date,
    ).update(status=decision.cancel_payment_status)
    return StudentEnrollmentActionResult(student_id=command.student_id, enrollment_id=enrollment.id, action=command.action)


@transaction.atomic
def reactivate_student_enrollment_command(command: StudentEnrollmentActionCommand) -> StudentEnrollmentActionResult:
    student = Student.objects.select_for_update().get(pk=command.student_id)
    enrollment = Enrollment.objects.select_related('plan').select_for_update().get(pk=command.enrollment_id)
    decision = build_enrollment_reactivation_decision(action_date=command.action_date, reason=command.reason)
    student.enrollments.filter(status=EnrollmentStatus.ACTIVE).exclude(pk=enrollment.pk).update(
        status=decision.expire_current_active_status,
        end_date=decision.expire_current_active_end_date,
    )
    enrollment.payments.filter(status__in=decision.cancel_payment_statuses).update(status=decision.cancel_payment_target_status)
    new_enrollment = Enrollment.objects.create(
        student=student,
        plan=enrollment.plan,
        status=decision.new_enrollment_status,
        start_date=decision.new_enrollment_start_date,
        notes=decision.new_enrollment_note,
    )
    execute_student_payment_schedule_command(
        StudentPaymentScheduleCommand(
            student_id=student.id,
            enrollment_id=new_enrollment.id,
            due_date=decision.payment_due_date,
            payment_method=decision.payment_method,
            confirm_payment_now=decision.confirm_payment_now,
            note=decision.payment_note,
            amount=new_enrollment.plan.price,
            reference=decision.payment_reference,
            billing_strategy=decision.billing_strategy,
            installment_total=decision.installment_total,
            recurrence_cycles=decision.recurrence_cycles,
        )
    )
    return StudentEnrollmentActionResult(student_id=student.id, enrollment_id=new_enrollment.id, action=command.action)


def execute_student_enrollment_sync_command(command: StudentEnrollmentSyncCommand):
    return execute_student_enrollment_sync_use_case(
        command,
        enrollment_workflow_port=DjangoStudentEnrollmentWorkflowPort(clock=DjangoClockPort()),
    )


__all__ = [
    'cancel_student_enrollment_command',
    'execute_student_enrollment_sync_command',
    'reactivate_student_enrollment_command',
]