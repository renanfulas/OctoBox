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
from django.utils import timezone

from boxcore.models import Payment, PaymentStatus, Student
from students.application.commands import StudentPaymentRegenerationCommand, StudentPaymentScheduleCommand
from students.application.payment_terms import advance_due_date
from students.application.ports import StudentPaymentRegenerationPort, StudentPaymentSchedulePort
from students.application.results import StudentPaymentRegenerationResult, StudentPaymentScheduleResult
from students.application.use_cases import (
    execute_student_payment_regeneration_use_case,
    execute_student_payment_schedule_use_case,
)


class DjangoStudentPaymentSchedulePort(StudentPaymentSchedulePort):
    @transaction.atomic
    def execute(self, command: StudentPaymentScheduleCommand) -> StudentPaymentScheduleResult:
        student = Student.objects.get(pk=command.student_id)
        enrollment = None
        if command.enrollment_id is not None:
            enrollment = student.enrollments.select_related('plan').get(pk=command.enrollment_id)

        billing_group = str(uuid4())
        normalized_amount = Decimal(command.amount)
        created_payment = None
        created_count = 0

        if command.billing_strategy == 'installments':
            total = max(command.installment_total, 1)
            installment_amount = (normalized_amount / total).quantize(Decimal('0.01'))
            running_total = Decimal('0.00')
            for index in range(1, total + 1):
                current_amount = installment_amount if index < total else normalized_amount - running_total
                running_total += current_amount
                payment = Payment.objects.create(
                    student=student,
                    enrollment=enrollment,
                    due_date=advance_due_date(
                        start_date=command.due_date,
                        step=index - 1,
                        billing_cycle=enrollment.plan.billing_cycle,
                    ),
                    amount=current_amount,
                    status=PaymentStatus.PAID if command.confirm_payment_now and index == 1 else PaymentStatus.PENDING,
                    method=command.payment_method,
                    paid_at=timezone.now() if command.confirm_payment_now and index == 1 else None,
                    reference=command.reference,
                    notes=command.note,
                    billing_group=billing_group,
                    installment_number=index,
                    installment_total=total,
                )
                created_payment = created_payment or payment
                created_count += 1
            return StudentPaymentScheduleResult(
                student_id=student.id,
                payment_id=getattr(created_payment, 'id', None),
                billing_group=billing_group,
                created_count=created_count,
            )

        if command.billing_strategy == 'recurring':
            cycles = max(command.recurrence_cycles, 1)
            for index in range(1, cycles + 1):
                payment = Payment.objects.create(
                    student=student,
                    enrollment=enrollment,
                    due_date=advance_due_date(
                        start_date=command.due_date,
                        step=index - 1,
                        billing_cycle=enrollment.plan.billing_cycle,
                    ),
                    amount=normalized_amount,
                    status=PaymentStatus.PAID if command.confirm_payment_now and index == 1 else PaymentStatus.PENDING,
                    method=command.payment_method,
                    paid_at=timezone.now() if command.confirm_payment_now and index == 1 else None,
                    reference=command.reference,
                    notes=command.note,
                    billing_group=billing_group,
                    installment_number=index,
                    installment_total=cycles,
                )
                created_payment = created_payment or payment
                created_count += 1
            return StudentPaymentScheduleResult(
                student_id=student.id,
                payment_id=getattr(created_payment, 'id', None),
                billing_group=billing_group,
                created_count=created_count,
            )

        created_payment = Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=command.due_date,
            amount=normalized_amount,
            status=PaymentStatus.PAID if command.confirm_payment_now else PaymentStatus.PENDING,
            method=command.payment_method,
            paid_at=timezone.now() if command.confirm_payment_now else None,
            reference=command.reference,
            notes=command.note,
            billing_group=billing_group,
            installment_number=1,
            installment_total=1,
        )
        return StudentPaymentScheduleResult(
            student_id=student.id,
            payment_id=created_payment.id,
            billing_group=billing_group,
            created_count=1,
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

        new_payment = Payment.objects.create(
            student=student,
            enrollment=target_enrollment,
            due_date=advance_due_date(
                start_date=payment.due_date,
                step=1,
                billing_cycle=target_enrollment.plan.billing_cycle,
            ),
            amount=payment.amount,
            status=PaymentStatus.PENDING,
            method=payment.method,
            reference=payment.reference,
            notes='Cobranca regenerada pela tela do aluno.',
            billing_group=payment.billing_group or str(uuid4()),
            installment_number=payment.installment_number + 1,
            installment_total=max(payment.installment_total, payment.installment_number + 1),
        )
        return StudentPaymentRegenerationResult(
            student_id=student.id,
            payment_id=new_payment.id,
            enrollment_id=target_enrollment.id,
        )


def execute_student_payment_schedule_command(command: StudentPaymentScheduleCommand):
    return execute_student_payment_schedule_use_case(
        command,
        payment_schedule_port=DjangoStudentPaymentSchedulePort(),
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