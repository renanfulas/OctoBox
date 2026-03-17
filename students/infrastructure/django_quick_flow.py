"""
ARQUIVO: adapters Django principais do fluxo rapido de aluno.

POR QUE ELE EXISTE:
- Implementa portas do caso de uso usando ORM e transacao concretos da base atual.

O QUE ESTE ARQUIVO FAZ:
1. Persiste aluno via ORM.
2. Reusa sincronizacao comercial e de intake existentes.
3. Monta as dependencias concretas do quick flow.

PONTOS CRITICOS:
- Auditoria concreta deste fluxo agora mora em adapter proprio para reduzir acoplamento dentro deste modulo.
"""

from django.db import transaction

from students.models import Student
from students.application.commands import StudentEnrollmentSyncCommand, StudentIntakeSyncCommand, StudentQuickCommand
from students.application.ports import (
    StudentEnrollmentSyncPort,
    StudentIntakeSyncPort,
    StudentWriterPort,
    UnitOfWorkPort,
)
from students.application.results import EnrollmentSyncRecord, StudentQuickResult, StudentRecord
from students.application.use_cases import (
    execute_create_student_quick_use_case,
    execute_update_student_quick_use_case,
)
from students.infrastructure.django_audit import DjangoStudentQuickAudit
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
