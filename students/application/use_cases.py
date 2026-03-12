"""
ARQUIVO: casos de uso do fluxo rapido de aluno.

POR QUE ELE EXISTE:
- Tira do Django a orquestracao do principal fluxo de aluno do produto.

O QUE ESTE ARQUIVO FAZ:
1. Cria aluno e sincroniza intake, matricula e cobranca.
2. Atualiza aluno e registra mudancas comerciais relevantes.
3. Mantem auditoria na mesma unidade de trabalho do fluxo principal.

PONTOS CRITICOS:
- A camada de aplicacao nao pode depender de ORM, request, template ou FormView.
"""

from .commands import (
    StudentEnrollmentActionCommand,
    StudentEnrollmentSyncCommand,
    StudentIntakeSyncCommand,
    StudentPaymentActionCommand,
    StudentPaymentRegenerationCommand,
    StudentPaymentScheduleCommand,
    StudentQuickCommand,
)
from .ports import (
    StudentEnrollmentActionPort,
    StudentEnrollmentSyncPort,
    StudentEnrollmentWorkflowPort,
    StudentIntakeSyncPort,
    StudentIntakeWorkflowPort,
    StudentPaymentActionPort,
    StudentPaymentRegenerationPort,
    StudentPaymentSchedulePort,
    StudentQuickAuditPort,
    StudentWriterPort,
    UnitOfWorkPort,
)
from .results import (
    StudentEnrollmentActionResult,
    StudentPaymentActionResult,
    StudentPaymentRegenerationResult,
    StudentPaymentScheduleResult,
    StudentQuickResult,
)


def execute_create_student_quick_use_case(
    command: StudentQuickCommand,
    *,
    unit_of_work: UnitOfWorkPort,
    student_writer: StudentWriterPort,
    enrollment_sync: StudentEnrollmentSyncPort,
    intake_sync: StudentIntakeSyncPort,
    audit: StudentQuickAuditPort,
) -> StudentQuickResult:
    def operation():
        student = student_writer.create(command)
        enrollment_result = enrollment_sync.sync(student_id=student.id, command=command)
        intake_id = intake_sync.sync(student_id=student.id, intake_record_id=command.intake_record_id)
        result = StudentQuickResult(
            student=student,
            enrollment_sync=enrollment_result,
            intake_id=intake_id,
            changed_fields=command.changed_fields,
        )
        audit.record_created(command=command, result=result)
        return result

    return unit_of_work.run(operation)


def execute_update_student_quick_use_case(
    command: StudentQuickCommand,
    *,
    unit_of_work: UnitOfWorkPort,
    student_writer: StudentWriterPort,
    enrollment_sync: StudentEnrollmentSyncPort,
    intake_sync: StudentIntakeSyncPort,
    audit: StudentQuickAuditPort,
) -> StudentQuickResult:
    def operation():
        student = student_writer.update(command)
        enrollment_result = enrollment_sync.sync(student_id=student.id, command=command)
        intake_id = intake_sync.sync(student_id=student.id, intake_record_id=command.intake_record_id)
        result = StudentQuickResult(
            student=student,
            enrollment_sync=enrollment_result,
            intake_id=intake_id,
            changed_fields=command.changed_fields,
        )
        audit.record_updated(command=command, result=result)
        return result

    return unit_of_work.run(operation)


def execute_student_payment_action_use_case(
    command: StudentPaymentActionCommand,
    *,
    payment_action_port: StudentPaymentActionPort,
) -> StudentPaymentActionResult:
    return payment_action_port.execute(command)


def execute_student_enrollment_action_use_case(
    command: StudentEnrollmentActionCommand,
    *,
    enrollment_action_port: StudentEnrollmentActionPort,
) -> StudentEnrollmentActionResult:
    return enrollment_action_port.execute(command)


def execute_student_enrollment_sync_use_case(
    command: StudentEnrollmentSyncCommand,
    *,
    enrollment_workflow_port: StudentEnrollmentWorkflowPort,
) -> EnrollmentSyncRecord:
    return enrollment_workflow_port.sync(command)


def execute_student_intake_sync_use_case(
    command: StudentIntakeSyncCommand,
    *,
    intake_workflow_port: StudentIntakeWorkflowPort,
) -> int | None:
    return intake_workflow_port.sync(command)


def execute_student_payment_schedule_use_case(
    command: StudentPaymentScheduleCommand,
    *,
    payment_schedule_port: StudentPaymentSchedulePort,
) -> StudentPaymentScheduleResult:
    return payment_schedule_port.execute(command)


def execute_student_payment_regeneration_use_case(
    command: StudentPaymentRegenerationCommand,
    *,
    payment_regeneration_port: StudentPaymentRegenerationPort,
) -> StudentPaymentRegenerationResult:
    return payment_regeneration_port.execute(command)


__all__ = [
    'execute_create_student_quick_use_case',
    'execute_student_enrollment_action_use_case',
    'execute_student_enrollment_sync_use_case',
    'execute_student_intake_sync_use_case',
    'execute_student_payment_action_use_case',
    'execute_student_payment_regeneration_use_case',
    'execute_student_payment_schedule_use_case',
    'execute_update_student_quick_use_case',
]
