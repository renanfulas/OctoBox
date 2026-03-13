"""
ARQUIVO: adapters Django do motor financeiro do aluno.

POR QUE ELE EXISTE:
- Isola a persistencia concreta de agenda e regeneracao de cobrança abaixo da camada de aplicacao.

O QUE ESTE ARQUIVO FAZ:
1. Cria cobranças unicas, parceladas e recorrentes.
2. Regenera cobrança preservando grupo comercial.
3. Mantém o contrato de payments.py fino e compatível.

PONTOS CRITICOS:
- Aqui fica o ORM; regra de datas e contrato do caso de uso ficam acima desta camada.
"""

from decimal import Decimal
from uuid import uuid4

from django.db import transaction

from finance.models import Payment, PaymentStatus
from students.models import Student
from students.application.commands import StudentPaymentRegenerationCommand, StudentPaymentScheduleCommand
from students.application.ports import ClockPort, StudentPaymentRegenerationPort, StudentPaymentSchedulePort
from students.application.results import StudentPaymentRegenerationResult, StudentPaymentScheduleResult
from students.application.use_cases import (
    execute_student_payment_regeneration_use_case,
    execute_student_payment_schedule_use_case,
)
from students.domain import build_payment_regeneration_decision, build_payment_schedule_plan
from students.infrastructure.django_clock import DjangoClockPort


class DjangoStudentPaymentSchedulePort(StudentPaymentSchedulePort):
    def __init__(self, *, clock: ClockPort):
        self.clock = clock

    @transaction.atomic
    def execute(self, command: StudentPaymentScheduleCommand) -> StudentPaymentScheduleResult:
        student = Student.objects.get(pk=command.student_id)
        enrollment = None
        if command.enrollment_id is not None:
            enrollment = student.enrollments.select_related('plan').get(pk=command.enrollment_id)

        billing_group = str(uuid4())
        billing_cycle = getattr(getattr(enrollment, 'plan', None), 'billing_cycle', 'monthly')
        payment_plan = build_payment_schedule_plan(
            due_date=command.due_date,
            amount=Decimal(command.amount),
            billing_strategy=command.billing_strategy,
            installment_total=command.installment_total,
            recurrence_cycles=command.recurrence_cycles,
            billing_cycle=billing_cycle,
            confirm_payment_now=command.confirm_payment_now,
        )
        created_payment = None
        for planned_payment in payment_plan:
            payment = Payment.objects.create(
                student=student,
                enrollment=enrollment,
                due_date=planned_payment.due_date,
                amount=planned_payment.amount,
                status=PaymentStatus.PAID if planned_payment.charge_now else PaymentStatus.PENDING,
                method=command.payment_method,
                paid_at=self.clock.now() if planned_payment.charge_now else None,
                reference=command.reference,
                notes=command.note,
                billing_group=billing_group,
                installment_number=planned_payment.installment_number,
                installment_total=planned_payment.installment_total,
            )
            created_payment = created_payment or payment

        return StudentPaymentScheduleResult(
            student_id=student.id,
            payment_id=getattr(created_payment, 'id', None),
            billing_group=billing_group,
            created_count=len(payment_plan),
        )


class DjangoStudentPaymentRegenerationPort(StudentPaymentRegenerationPort):
    @transaction.atomic
    def execute(self, command: StudentPaymentRegenerationCommand) -> StudentPaymentRegenerationResult:
        student = Student.objects.select_for_update().get(pk=command.student_id)
        payment = Payment.objects.select_related('enrollment__plan').select_for_update().get(pk=command.payment_id)

        target_enrollment = None
        if command.enrollment_id is not None:
            target_enrollment = student.enrollments.select_related('plan').select_for_update().get(pk=command.enrollment_id)
        else:
            target_enrollment = student.enrollments.select_related('plan').select_for_update().order_by('-start_date', '-created_at').first()

        if target_enrollment is None:
            return StudentPaymentRegenerationResult(
                student_id=student.id,
                payment_id=None,
                enrollment_id=None,
            )

        regeneration = build_payment_regeneration_decision(
            current_due_date=payment.due_date,
            current_installment_number=payment.installment_number,
            current_installment_total=payment.installment_total,
            billing_cycle=target_enrollment.plan.billing_cycle,
        )

        new_payment = Payment.objects.create(
            student=student,
            enrollment=target_enrollment,
            due_date=regeneration.due_date,
            amount=payment.amount,
            status=PaymentStatus.PENDING,
            method=payment.method,
            reference=payment.reference,
            notes=regeneration.note,
            billing_group=payment.billing_group or str(uuid4()),
            installment_number=regeneration.installment_number,
            installment_total=regeneration.installment_total,
        )
        return StudentPaymentRegenerationResult(
            student_id=student.id,
            payment_id=new_payment.id,
            enrollment_id=target_enrollment.id,
        )


def execute_student_payment_schedule_command(command: StudentPaymentScheduleCommand):
    return execute_student_payment_schedule_use_case(
        command,
        payment_schedule_port=DjangoStudentPaymentSchedulePort(clock=DjangoClockPort()),
    )


def execute_student_payment_regeneration_command(command: StudentPaymentRegenerationCommand):
    return execute_student_payment_regeneration_use_case(
        command,
        payment_regeneration_port=DjangoStudentPaymentRegenerationPort(),
    )


__all__ = [
    'execute_student_payment_regeneration_command',
    'execute_student_payment_schedule_command',
]