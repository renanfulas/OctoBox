"""
ARQUIVO: adapters Django do fluxo rapido de aluno.

POR QUE ELE EXISTE:
- Implementa portas do caso de uso usando ORM, transacao e auditoria concretos da base atual.

O QUE ESTE ARQUIVO FAZ:
1. Persiste aluno via ORM.
2. Reusa sincronizacao comercial e de intake existentes.
3. Registra auditoria concreta com o modelo historico atual.

PONTOS CRITICOS:
- Esta camada pode usar Django livremente, mas o contrato para cima precisa continuar estavel.
"""

from django.contrib.auth import get_user_model
from django.db import transaction

from boxcore.auditing import log_audit_event
from boxcore.models import Enrollment, MembershipPlan, Payment, Student, StudentIntake
from students.application.commands import StudentEnrollmentSyncCommand, StudentIntakeSyncCommand, StudentQuickCommand
from students.application.ports import (
    StudentEnrollmentSyncPort,
    StudentIntakeSyncPort,
    StudentQuickAuditPort,
    StudentWriterPort,
    UnitOfWorkPort,
)
from students.application.results import EnrollmentSyncRecord, StudentQuickResult, StudentRecord
from students.application.use_cases import (
    execute_create_student_quick_use_case,
    execute_update_student_quick_use_case,
)
from students.infrastructure.django_enrollments import execute_student_enrollment_sync_command
from students.infrastructure.django_intakes import execute_student_intake_sync_command


class DjangoAtomicUnitOfWork(UnitOfWorkPort):
    def run(self, operation):
        with transaction.atomic():
            return operation()


class DjangoStudentWriter(StudentWriterPort):
    writable_fields = (
        'full_name',
        'phone',
        'status',
        'email',
        'gender',
        'birth_date',
        'health_issue_status',
        'cpf',
        'notes',
    )

    def _build_student_values(self, command: StudentQuickCommand):
        return {field_name: getattr(command, field_name) for field_name in self.writable_fields}

    def create(self, command: StudentQuickCommand) -> StudentRecord:
        student = Student.objects.create(**self._build_student_values(command))
        return StudentRecord(id=student.id, full_name=student.full_name)

    def update(self, command: StudentQuickCommand) -> StudentRecord:
        if command.student_id is None:
            raise ValueError('student_id is required to update a student.')

        student = Student.objects.select_for_update().get(pk=command.student_id)
        update_fields = []
        for field_name, value in self._build_student_values(command).items():
            if getattr(student, field_name) != value:
                setattr(student, field_name, value)
                update_fields.append(field_name)

        if update_fields:
            update_fields.append('updated_at')
            student.save(update_fields=update_fields)

        return StudentRecord(id=student.id, full_name=student.full_name)


class DjangoStudentEnrollmentSync(StudentEnrollmentSyncPort):
    def sync(self, *, student_id: int, command: StudentQuickCommand) -> EnrollmentSyncRecord:
        return execute_student_enrollment_sync_command(
            StudentEnrollmentSyncCommand(
                student_id=student_id,
                selected_plan_id=command.selected_plan_id,
                enrollment_status=command.enrollment_status,
                due_date=command.payment_due_date,
                payment_method=command.payment_method,
                confirm_payment_now=command.confirm_payment_now,
                payment_reference=command.payment_reference,
                billing_strategy=command.billing_strategy,
                installment_total=command.installment_total,
                recurrence_cycles=command.recurrence_cycles,
                initial_payment_amount=command.initial_payment_amount,
            )
        )


class DjangoStudentIntakeSync(StudentIntakeSyncPort):
    def sync(self, *, student_id: int, intake_record_id: int | None) -> int | None:
        return execute_student_intake_sync_command(
            StudentIntakeSyncCommand(
                student_id=student_id,
                intake_record_id=intake_record_id,
            )
        )


class DjangoStudentQuickAudit(StudentQuickAuditPort):
    def __init__(self):
        self.user_model = get_user_model()

    def _get_actor(self, actor_id: int | None):
        if actor_id is None:
            return None
        return self.user_model.objects.filter(pk=actor_id).first()

    def _get_student(self, student_id: int):
        return Student.objects.get(pk=student_id)

    def _get_enrollment(self, enrollment_id: int | None):
        if enrollment_id is None:
            return None
        return Enrollment.objects.get(pk=enrollment_id)

    def _get_payment(self, payment_id: int | None):
        if payment_id is None:
            return None
        return Payment.objects.get(pk=payment_id)

    def _get_intake(self, intake_id: int | None):
        if intake_id is None:
            return None
        return StudentIntake.objects.get(pk=intake_id)

    def record_created(self, *, command: StudentQuickCommand, result: StudentQuickResult) -> None:
        actor = self._get_actor(command.actor_id)
        student = self._get_student(result.student.id)
        payment = self._get_payment(result.enrollment_sync.payment_id)
        intake = self._get_intake(result.intake_id)

        log_audit_event(
            actor=actor,
            action='student_quick_created',
            target=student,
            description='Aluno criado pela tela leve de cadastro.',
            metadata={
                'status': student.status,
                'enrollment_id': result.enrollment_sync.enrollment_id,
                'payment_id': result.enrollment_sync.payment_id,
                'movement': result.enrollment_sync.movement,
                'intake_id': result.intake_id,
            },
        )
        if payment is not None:
            log_audit_event(
                actor=actor,
                action='student_quick_payment_created',
                target=payment,
                description='Primeira cobranca criada pela tela leve do aluno.',
                metadata={'status': payment.status, 'method': payment.method},
            )
        if intake is not None:
            log_audit_event(
                actor=actor,
                action='student_intake_converted',
                target=intake,
                description='Lead convertido em aluno pela tela leve.',
                metadata={'student_id': student.id},
            )

    def record_updated(self, *, command: StudentQuickCommand, result: StudentQuickResult) -> None:
        actor = self._get_actor(command.actor_id)
        student = self._get_student(result.student.id)
        enrollment = self._get_enrollment(result.enrollment_sync.enrollment_id)
        payment = self._get_payment(result.enrollment_sync.payment_id)
        intake = self._get_intake(result.intake_id)

        log_audit_event(
            actor=actor,
            action='student_quick_updated',
            target=student,
            description='Aluno alterado pela tela leve de cadastro.',
            metadata={
                'changed_fields': list(result.changed_fields),
                'enrollment_id': result.enrollment_sync.enrollment_id,
                'payment_id': result.enrollment_sync.payment_id,
                'movement': result.enrollment_sync.movement,
                'intake_id': result.intake_id,
            },
        )
        if enrollment is not None and result.enrollment_sync.movement in ('upgrade', 'downgrade', 'troca de plano'):
            log_audit_event(
                actor=actor,
                action='student_plan_changed',
                target=enrollment,
                description='Troca de plano registrada pela tela leve do aluno.',
                metadata={'movement': result.enrollment_sync.movement},
            )
        if payment is not None:
            log_audit_event(
                actor=actor,
                action='student_quick_payment_created',
                target=payment,
                description='Cobranca criada ou confirmada pela tela leve do aluno.',
                metadata={'status': payment.status, 'method': payment.method},
            )
        if intake is not None:
            log_audit_event(
                actor=actor,
                action='student_intake_converted',
                target=intake,
                description='Lead vinculado ao aluno pela tela leve.',
                metadata={'student_id': student.id},
            )


def _build_dependencies():
    return {
        'unit_of_work': DjangoAtomicUnitOfWork(),
        'student_writer': DjangoStudentWriter(),
        'enrollment_sync': DjangoStudentEnrollmentSync(),
        'intake_sync': DjangoStudentIntakeSync(),
        'audit': DjangoStudentQuickAudit(),
    }


def execute_create_student_quick_command(command: StudentQuickCommand) -> StudentQuickResult:
    return execute_create_student_quick_use_case(command, **_build_dependencies())


def execute_update_student_quick_command(command: StudentQuickCommand) -> StudentQuickResult:
    return execute_update_student_quick_use_case(command, **_build_dependencies())


__all__ = ['execute_create_student_quick_command', 'execute_update_student_quick_command']
