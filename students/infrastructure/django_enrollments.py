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

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from boxcore.models import Enrollment, EnrollmentStatus, MembershipPlan, PaymentStatus, Student
from students.application.commands import StudentEnrollmentActionCommand, StudentEnrollmentSyncCommand
from students.application.enrollment_terms import describe_plan_change
from students.application.ports import StudentEnrollmentWorkflowPort
from students.application.results import EnrollmentSyncRecord, StudentEnrollmentActionResult
from students.application.use_cases import execute_student_enrollment_sync_use_case
from students.infrastructure.django_payments import execute_student_payment_schedule_command
from students.application.commands import StudentPaymentScheduleCommand


class DjangoStudentEnrollmentWorkflowPort(StudentEnrollmentWorkflowPort):
    @transaction.atomic
    def sync(self, command: StudentEnrollmentSyncCommand) -> EnrollmentSyncRecord:
        enrollment_status = command.enrollment_status or EnrollmentStatus.PENDING
        due_date = command.due_date or timezone.localdate()
        payment_method = command.payment_method or 'pix'
        installment_total = command.installment_total or 1
        recurrence_cycles = command.recurrence_cycles or 1

        student = Student.objects.select_for_update().get(pk=command.student_id)
        latest_enrollment = student.enrollments.select_related('plan').select_for_update().order_by('-start_date', '-created_at').first()
        selected_plan = MembershipPlan.objects.get(pk=command.selected_plan_id) if command.selected_plan_id is not None else None
        base_amount = command.initial_payment_amount or (selected_plan.price if selected_plan is not None else Decimal('0.00'))

        if selected_plan is None:
            return EnrollmentSyncRecord(enrollment_id=None, payment_id=None, movement='none')

        if latest_enrollment is None:
            enrollment = Enrollment.objects.create(
                student=student,
                plan=selected_plan,
                status=enrollment_status,
                start_date=timezone.localdate(),
                notes='Plano conectado pela tela leve do aluno.',
            )
            payment_result = execute_student_payment_schedule_command(
                StudentPaymentScheduleCommand(
                    student_id=student.id,
                    enrollment_id=enrollment.id,
                    due_date=due_date,
                    payment_method=payment_method,
                    confirm_payment_now=command.confirm_payment_now,
                    note='Primeira cobranca criada no fluxo leve do aluno.',
                    amount=base_amount,
                    reference=command.payment_reference,
                    billing_strategy=command.billing_strategy,
                    installment_total=installment_total,
                    recurrence_cycles=recurrence_cycles,
                )
            )
            return EnrollmentSyncRecord(enrollment_id=enrollment.id, payment_id=payment_result.payment_id, movement='created')

        if latest_enrollment.plan_id == selected_plan.id:
            latest_enrollment.plan = selected_plan
            latest_enrollment.status = enrollment_status
            if latest_enrollment.start_date is None:
                latest_enrollment.start_date = timezone.localdate()
            latest_enrollment.save(update_fields=['plan', 'status', 'start_date', 'updated_at'])

            payment_id = None
            if not latest_enrollment.payments.exists():
                payment_result = execute_student_payment_schedule_command(
                    StudentPaymentScheduleCommand(
                        student_id=student.id,
                        enrollment_id=latest_enrollment.id,
                        due_date=due_date,
                        payment_method=payment_method,
                        confirm_payment_now=command.confirm_payment_now,
                        note='Primeira cobranca criada no fluxo leve do aluno.',
                        amount=base_amount,
                        reference=command.payment_reference,
                        billing_strategy=command.billing_strategy,
                        installment_total=installment_total,
                        recurrence_cycles=recurrence_cycles,
                    )
                )
                payment_id = payment_result.payment_id

            return EnrollmentSyncRecord(
                enrollment_id=latest_enrollment.id,
                payment_id=payment_id,
                movement='status_adjusted',
            )

        movement = describe_plan_change(
            previous_price=latest_enrollment.plan.price,
            selected_price=selected_plan.price,
        )
        latest_enrollment.status = EnrollmentStatus.EXPIRED
        latest_enrollment.end_date = timezone.localdate()
        latest_enrollment.notes = '\n'.join(
            filter(None, [latest_enrollment.notes.strip(), f'Encerrada por {movement} na tela leve do aluno.'])
        )
        latest_enrollment.save(update_fields=['status', 'end_date', 'notes', 'updated_at'])

        enrollment = Enrollment.objects.create(
            student=student,
            plan=selected_plan,
            status=enrollment_status,
            start_date=timezone.localdate(),
            notes=f'{movement.capitalize()} aplicada pela tela leve do aluno.',
        )
        payment_result = execute_student_payment_schedule_command(
            StudentPaymentScheduleCommand(
                student_id=student.id,
                enrollment_id=enrollment.id,
                due_date=due_date,
                payment_method=payment_method,
                confirm_payment_now=command.confirm_payment_now,
                note=f'Cobranca criada apos {movement} de plano.',
                amount=base_amount,
                reference=command.payment_reference,
                billing_strategy=command.billing_strategy,
                installment_total=installment_total,
                recurrence_cycles=recurrence_cycles,
            )
        )
        return EnrollmentSyncRecord(
            enrollment_id=enrollment.id,
            payment_id=payment_result.payment_id,
            movement=movement,
        )


@transaction.atomic
def cancel_student_enrollment_command(command: StudentEnrollmentActionCommand) -> StudentEnrollmentActionResult:
    enrollment = Enrollment.objects.select_for_update().get(pk=command.enrollment_id)
    enrollment.status = EnrollmentStatus.CANCELED
    enrollment.end_date = command.action_date
    enrollment.notes = '\n'.join(
        filter(None, [enrollment.notes.strip(), f'Cancelada pela tela do aluno. Motivo: {command.reason or "nao informado"}.'])
    )
    enrollment.save(update_fields=['status', 'end_date', 'notes', 'updated_at'])
    enrollment.payments.filter(status=PaymentStatus.PENDING, due_date__gte=command.action_date).update(status=PaymentStatus.CANCELED)
    return StudentEnrollmentActionResult(student_id=command.student_id, enrollment_id=enrollment.id, action=command.action)


@transaction.atomic
def reactivate_student_enrollment_command(command: StudentEnrollmentActionCommand) -> StudentEnrollmentActionResult:
    student = Student.objects.select_for_update().get(pk=command.student_id)
    enrollment = Enrollment.objects.select_related('plan').select_for_update().get(pk=command.enrollment_id)
    student.enrollments.filter(status=EnrollmentStatus.ACTIVE).exclude(pk=enrollment.pk).update(
        status=EnrollmentStatus.EXPIRED,
        end_date=command.action_date,
    )
    enrollment.payments.filter(status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE]).update(status=PaymentStatus.CANCELED)
    new_enrollment = Enrollment.objects.create(
        student=student,
        plan=enrollment.plan,
        status=EnrollmentStatus.ACTIVE,
        start_date=command.action_date,
        notes=f'Reativada pela tela do aluno. Motivo: {command.reason or "nao informado"}.',
    )
    execute_student_payment_schedule_command(
        StudentPaymentScheduleCommand(
            student_id=student.id,
            enrollment_id=new_enrollment.id,
            due_date=command.action_date,
            payment_method='pix',
            confirm_payment_now=False,
            note='Cobranca criada na reativacao da matricula.',
            amount=new_enrollment.plan.price,
            reference='',
            billing_strategy='single',
            installment_total=1,
            recurrence_cycles=1,
        )
    )
    return StudentEnrollmentActionResult(student_id=student.id, enrollment_id=new_enrollment.id, action=command.action)


def execute_student_enrollment_sync_command(command: StudentEnrollmentSyncCommand):
    return execute_student_enrollment_sync_use_case(
        command,
        enrollment_workflow_port=DjangoStudentEnrollmentWorkflowPort(),
    )


__all__ = [
    'cancel_student_enrollment_command',
    'execute_student_enrollment_sync_command',
    'reactivate_student_enrollment_command',
]