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

from finance.models import Enrollment, Payment
from students.models import Student
from students.application.commands import StudentEnrollmentActionCommand, StudentPaymentActionCommand
from students.application.ports import ClockPort, StudentEnrollmentActionPort, StudentPaymentActionPort
from students.application.results import StudentEnrollmentActionResult, StudentPaymentActionResult
from students.application.use_cases import execute_student_enrollment_action_use_case, execute_student_payment_action_use_case
from students.domain import (
    build_enrollment_action_decision,
    build_payment_mutation_decision,
    resolve_regeneration_enrollment_id,
)
from students.infrastructure.django_audit import DjangoStudentActionAudit
from students.infrastructure.django_clock import DjangoClockPort
from students.infrastructure.django_payments import execute_student_payment_regeneration_command
from students.application.commands import StudentPaymentRegenerationCommand


class DjangoStudentPaymentActionPort(StudentPaymentActionPort):
    def __init__(self, *, clock: ClockPort):
        self.user_model = get_user_model()
        self.clock = clock
        self.audit = DjangoStudentActionAudit()

    def _get_actor(self, actor_id: int | None):
        if actor_id is None:
            return None
        return self.user_model.objects.filter(pk=actor_id).first()

    @transaction.atomic
    def execute(self, command: StudentPaymentActionCommand) -> StudentPaymentActionResult:
        actor = self._get_actor(command.actor_id)
        student = Student.objects.get(pk=command.student_id)
        payment = Payment.objects.select_for_update().get(pk=command.payment_id)
        mutation_decision = build_payment_mutation_decision(command.action)

        if command.action == 'update-payment':
            payment.amount = command.amount
            payment.due_date = command.due_date
            payment.method = command.method
            payment.reference = command.reference
            payment.notes = command.notes
            payment.save(update_fields=['amount', 'due_date', 'method', 'reference', 'notes', 'updated_at'])
            self.audit.record_payment_updated(actor_id=getattr(actor, 'id', None), payment_id=payment.id)
            return StudentPaymentActionResult(student_id=student.id, payment_id=payment.id, action=command.action)

        if mutation_decision is not None:
            if command.action == 'mark-paid':
                if command.amount is not None:
                    payment.amount = command.amount
                if command.due_date is not None:
                    payment.due_date = command.due_date
                if command.method:
                    payment.method = command.method
                if command.reference:
                    payment.reference = command.reference
                if command.notes:
                    payment.notes = command.notes

            payment.status = mutation_decision.status
            payment.paid_at = self.clock.now() if mutation_decision.update_paid_at else payment.paid_at
            update_fields = ['status', 'updated_at']
            if command.action == 'mark-paid':
                update_fields = ['amount', 'due_date', 'method', 'reference', 'notes', *update_fields]
            if mutation_decision.update_paid_at:
                update_fields.insert(1, 'paid_at')
            payment.save(update_fields=update_fields)
            getattr(self.audit, mutation_decision.audit_method)(
                actor_id=getattr(actor, 'id', None),
                payment_id=payment.id,
            )
            return StudentPaymentActionResult(student_id=student.id, payment_id=payment.id, action=command.action)

        if command.action == 'regenerate-payment':
            latest_enrollment = student.enrollments.order_by('-start_date', '-created_at').first()
            enrollment_id = resolve_regeneration_enrollment_id(
                payment_enrollment_id=getattr(payment.enrollment, 'id', None),
                latest_enrollment_id=getattr(latest_enrollment, 'id', None),
            )
            regeneration_result = execute_student_payment_regeneration_command(
                StudentPaymentRegenerationCommand(
                    student_id=student.id,
                    payment_id=payment.id,
                    enrollment_id=enrollment_id,
                )
            )
            if regeneration_result.payment_id is not None:
                self.audit.record_payment_regenerated(
                    actor_id=getattr(actor, 'id', None),
                    new_payment_id=regeneration_result.payment_id,
                    previous_payment_id=payment.id,
                )
                return StudentPaymentActionResult(student_id=student.id, payment_id=regeneration_result.payment_id, action=command.action)

        return StudentPaymentActionResult(student_id=student.id, payment_id=None, action=command.action)


class DjangoStudentEnrollmentActionPort(StudentEnrollmentActionPort):
    def __init__(self):
        self.user_model = get_user_model()
        self.audit = DjangoStudentActionAudit()

    def _get_actor(self, actor_id: int | None):
        if actor_id is None:
            return None
        return self.user_model.objects.filter(pk=actor_id).first()

    @transaction.atomic
    def execute(self, command: StudentEnrollmentActionCommand) -> StudentEnrollmentActionResult:
        actor = self._get_actor(command.actor_id)
        student = Student.objects.get(pk=command.student_id)
        enrollment = Enrollment.objects.get(pk=command.enrollment_id)
        decision = build_enrollment_action_decision(command.action)

        if decision is not None:
            action_result = globals()[decision.handler_name](command)
            target_enrollment_id = action_result.enrollment_id if decision.use_action_result_enrollment else enrollment.id
            getattr(self.audit, decision.audit_method)(
                actor_id=getattr(actor, 'id', None),
                enrollment_id=target_enrollment_id,
                reason=command.reason,
            )
            return StudentEnrollmentActionResult(
                student_id=student.id,
                enrollment_id=target_enrollment_id,
                action=command.action,
            )

        return StudentEnrollmentActionResult(student_id=student.id, enrollment_id=None, action=command.action)


def execute_student_payment_action_command(command: StudentPaymentActionCommand):
    return execute_student_payment_action_use_case(
        command,
        payment_action_port=DjangoStudentPaymentActionPort(clock=DjangoClockPort()),
    )


def execute_student_enrollment_action_command(command: StudentEnrollmentActionCommand):
    return execute_student_enrollment_action_use_case(
        command,
        enrollment_action_port=DjangoStudentEnrollmentActionPort(),
    )


__all__ = ['execute_student_enrollment_action_command', 'execute_student_payment_action_command']