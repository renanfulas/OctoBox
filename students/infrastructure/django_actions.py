"""
ARQUIVO: adapters Django das actions comerciais do aluno.

POR QUE ELE EXISTE:
- Isola pagamento e matrícula em use cases com adapters concretos sem reescrever a UI atual.

O QUE ESTE ARQUIVO FAZ:
1. Executa actions de pagamento com auditoria.
2. Executa actions de matrícula com auditoria.
3. Mantém o uso de ORM e transação abaixo da camada de aplicação.

PONTOS CRITICOS:
- Esta camada continua usando Django concretamente; acima dela o contrato deve permanecer estável.
"""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from boxcore.auditing import log_audit_event
from boxcore.models import Enrollment, Payment, PaymentStatus, Student
from students.application.commands import StudentEnrollmentActionCommand, StudentPaymentActionCommand
from students.application.ports import StudentEnrollmentActionPort, StudentPaymentActionPort
from students.application.results import StudentEnrollmentActionResult, StudentPaymentActionResult
from students.application.use_cases import execute_student_enrollment_action_use_case, execute_student_payment_action_use_case
from students.infrastructure.django_enrollments import (
    cancel_student_enrollment_command,
    reactivate_student_enrollment_command,
)
from students.infrastructure.django_payments import execute_student_payment_regeneration_command
from students.application.commands import StudentPaymentRegenerationCommand


class DjangoStudentPaymentActionPort(StudentPaymentActionPort):
    def __init__(self):
        self.user_model = get_user_model()

    def _get_actor(self, actor_id: int | None):
        if actor_id is None:
            return None
        return self.user_model.objects.filter(pk=actor_id).first()

    @transaction.atomic
    def execute(self, command: StudentPaymentActionCommand) -> StudentPaymentActionResult:
        actor = self._get_actor(command.actor_id)
        student = Student.objects.get(pk=command.student_id)
        payment = Payment.objects.select_for_update().get(pk=command.payment_id)

        if command.action == 'update-payment':
            payment.amount = command.amount
            payment.due_date = command.due_date
            payment.method = command.method
            payment.reference = command.reference
            payment.notes = command.notes
            payment.save(update_fields=['amount', 'due_date', 'method', 'reference', 'notes', 'updated_at'])
            log_audit_event(
                actor=actor,
                action='student_payment_updated',
                target=payment,
                description='Cobranca atualizada pela tela do aluno.',
                metadata={'status': payment.status},
            )
            return StudentPaymentActionResult(student_id=student.id, payment_id=payment.id, action=command.action)

        if command.action == 'mark-paid':
            payment.status = PaymentStatus.PAID
            payment.paid_at = timezone.now()
            payment.save(update_fields=['status', 'paid_at', 'updated_at'])
            log_audit_event(
                actor=actor,
                action='student_payment_marked_paid',
                target=payment,
                description='Cobranca confirmada como paga pela tela do aluno.',
                metadata={'method': payment.method},
            )
            return StudentPaymentActionResult(student_id=student.id, payment_id=payment.id, action=command.action)

        if command.action == 'refund-payment':
            payment.status = PaymentStatus.REFUNDED
            payment.save(update_fields=['status', 'updated_at'])
            log_audit_event(
                actor=actor,
                action='student_payment_refunded',
                target=payment,
                description='Pagamento estornado pela tela do aluno.',
                metadata={},
            )
            return StudentPaymentActionResult(student_id=student.id, payment_id=payment.id, action=command.action)

        if command.action == 'cancel-payment':
            payment.status = PaymentStatus.CANCELED
            payment.save(update_fields=['status', 'updated_at'])
            log_audit_event(
                actor=actor,
                action='student_payment_canceled',
                target=payment,
                description='Cobranca cancelada pela tela do aluno.',
                metadata={},
            )
            return StudentPaymentActionResult(student_id=student.id, payment_id=payment.id, action=command.action)

        if command.action == 'regenerate-payment':
            enrollment = payment.enrollment or student.enrollments.order_by('-start_date', '-created_at').first()
            regeneration_result = execute_student_payment_regeneration_command(
                StudentPaymentRegenerationCommand(
                    student_id=student.id,
                    payment_id=payment.id,
                    enrollment_id=getattr(enrollment, 'id', None),
                )
            )
            if regeneration_result.payment_id is not None:
                new_payment = Payment.objects.get(pk=regeneration_result.payment_id)
                log_audit_event(
                    actor=actor,
                    action='student_payment_regenerated',
                    target=new_payment,
                    description='Nova cobranca gerada pela tela do aluno.',
                    metadata={'previous_payment_id': payment.id},
                )
                return StudentPaymentActionResult(student_id=student.id, payment_id=new_payment.id, action=command.action)

        return StudentPaymentActionResult(student_id=student.id, payment_id=None, action=command.action)


class DjangoStudentEnrollmentActionPort(StudentEnrollmentActionPort):
    def __init__(self):
        self.user_model = get_user_model()

    def _get_actor(self, actor_id: int | None):
        if actor_id is None:
            return None
        return self.user_model.objects.filter(pk=actor_id).first()

    @transaction.atomic
    def execute(self, command: StudentEnrollmentActionCommand) -> StudentEnrollmentActionResult:
        actor = self._get_actor(command.actor_id)
        student = Student.objects.get(pk=command.student_id)
        enrollment = Enrollment.objects.get(pk=command.enrollment_id)

        if command.action == 'cancel-enrollment':
            cancel_student_enrollment_command(command)
            log_audit_event(
                actor=actor,
                action='student_enrollment_canceled',
                target=enrollment,
                description='Matricula cancelada pela tela do aluno.',
                metadata={'reason': command.reason},
            )
            return StudentEnrollmentActionResult(student_id=student.id, enrollment_id=enrollment.id, action=command.action)

        if command.action == 'reactivate-enrollment':
            action_result = reactivate_student_enrollment_command(command)
            new_enrollment = Enrollment.objects.get(pk=action_result.enrollment_id)
            log_audit_event(
                actor=actor,
                action='student_enrollment_reactivated',
                target=new_enrollment,
                description='Matricula reativada pela tela do aluno.',
                metadata={'reason': command.reason},
            )
            return StudentEnrollmentActionResult(student_id=student.id, enrollment_id=new_enrollment.id, action=command.action)

        return StudentEnrollmentActionResult(student_id=student.id, enrollment_id=None, action=command.action)


def execute_student_payment_action_command(command: StudentPaymentActionCommand):
    return execute_student_payment_action_use_case(
        command,
        payment_action_port=DjangoStudentPaymentActionPort(),
    )


def execute_student_enrollment_action_command(command: StudentEnrollmentActionCommand):
    return execute_student_enrollment_action_use_case(
        command,
        enrollment_action_port=DjangoStudentEnrollmentActionPort(),
    )


__all__ = ['execute_student_enrollment_action_command', 'execute_student_payment_action_command']