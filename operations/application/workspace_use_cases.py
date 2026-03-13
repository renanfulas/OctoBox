"""
ARQUIVO: casos de uso das acoes do workspace operacional.

POR QUE ELE EXISTE:
- move as mutacoes reais de manager e coach para fora do modulo historico boxcore.operations.

O QUE ESTE ARQUIVO FAZ:
1. vincula pagamento a matricula ativa.
2. cria ocorrencia tecnica.
3. aplica mudanca operacional de presenca.

PONTOS CRITICOS:
- a camada de aplicacao nao depende de ORM, request ou views.
"""

from .workspace_commands import (
    ApplyAttendanceActionCommand,
    CreateTechnicalBehaviorNoteCommand,
    LinkPaymentEnrollmentCommand,
)
from .workspace_ports import WorkspaceActionAuditPort, WorkspaceActionWriterPort, WorkspaceUnitOfWorkPort


def execute_link_payment_enrollment_use_case(
    command: LinkPaymentEnrollmentCommand,
    *,
    unit_of_work: WorkspaceUnitOfWorkPort,
    writer: WorkspaceActionWriterPort,
    audit: WorkspaceActionAuditPort,
):
    def operation():
        result = writer.link_payment_enrollment(command)
        audit.record_payment_enrollment_linked(command=command, result=result)
        return result

    return unit_of_work.run(operation)


def execute_create_technical_behavior_note_use_case(
    command: CreateTechnicalBehaviorNoteCommand,
    *,
    unit_of_work: WorkspaceUnitOfWorkPort,
    writer: WorkspaceActionWriterPort,
    audit: WorkspaceActionAuditPort,
):
    def operation():
        result = writer.create_technical_behavior_note(command)
        audit.record_technical_behavior_note_created(command=command, result=result)
        return result

    return unit_of_work.run(operation)


def execute_apply_attendance_action_use_case(
    command: ApplyAttendanceActionCommand,
    *,
    unit_of_work: WorkspaceUnitOfWorkPort,
    writer: WorkspaceActionWriterPort,
    audit: WorkspaceActionAuditPort,
):
    def operation():
        result = writer.apply_attendance_action(command)
        audit.record_attendance_action_applied(command=command, result=result)
        return result

    return unit_of_work.run(operation)


__all__ = [
    'execute_apply_attendance_action_use_case',
    'execute_create_technical_behavior_note_use_case',
    'execute_link_payment_enrollment_use_case',
]