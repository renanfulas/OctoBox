"""
ARQUIVO: casos de uso da grade de aulas.

POR QUE ELE EXISTE:
- move a orquestracao operacional principal para fora do catalogo historico.

O QUE ESTE ARQUIVO FAZ:
1. cria agendas recorrentes com auditoria.
2. atualiza aulas com auditoria.
3. exclui aulas com auditoria.

PONTOS CRITICOS:
- a aplicacao continua sem depender de form, view ou ORM.
"""

from .commands import ClassScheduleCreateCommand, ClassSessionDeleteCommand, ClassSessionUpdateCommand
from .ports import ClassGridAuditPort, ClassGridWriterPort, UnitOfWorkPort
from .results import ClassScheduleCreateResult, DeletedClassSessionRecord, UpdatedClassSessionRecord


def execute_create_class_schedule_use_case(
    command: ClassScheduleCreateCommand,
    *,
    unit_of_work: UnitOfWorkPort,
    writer: ClassGridWriterPort,
    audit: ClassGridAuditPort,
) -> ClassScheduleCreateResult:
    def operation():
        result = writer.create_schedule(command)
        audit.record_schedule_created(command=command, result=result)
        return result

    return unit_of_work.run(operation)


def execute_update_class_session_use_case(
    command: ClassSessionUpdateCommand,
    *,
    unit_of_work: UnitOfWorkPort,
    writer: ClassGridWriterPort,
    audit: ClassGridAuditPort,
) -> UpdatedClassSessionRecord:
    def operation():
        result = writer.update_session(command)
        audit.record_session_updated(command=command, result=result)
        return result

    return unit_of_work.run(operation)


def execute_delete_class_session_use_case(
    command: ClassSessionDeleteCommand,
    *,
    unit_of_work: UnitOfWorkPort,
    writer: ClassGridWriterPort,
    audit: ClassGridAuditPort,
) -> DeletedClassSessionRecord:
    def operation():
        result = writer.delete_session(command)
        audit.record_session_deleted(command=command, result=result)
        return result

    return unit_of_work.run(operation)


__all__ = [
    'execute_create_class_schedule_use_case',
    'execute_delete_class_session_use_case',
    'execute_update_class_session_use_case',
]