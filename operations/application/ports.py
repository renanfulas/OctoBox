"""
ARQUIVO: portas da grade de aulas.

POR QUE ELE EXISTE:
- separa a orquestracao operacional da implementacao concreta em Django.

O QUE ESTE ARQUIVO FAZ:
1. define a unidade de trabalho da grade.
2. define escrita operacional e auditoria como contratos.

PONTOS CRITICOS:
- os contratos precisam continuar pequenos para facilitar futuros adapters fora do Django.
"""

from typing import Callable, Protocol, TypeVar

from .commands import ClassScheduleCreateCommand, ClassSessionDeleteCommand, ClassSessionUpdateCommand
from .results import ClassScheduleCreateResult, DeletedClassSessionRecord, UpdatedClassSessionRecord


ResultType = TypeVar('ResultType')


class UnitOfWorkPort(Protocol):
    def run(self, operation: Callable[[], ResultType]) -> ResultType:
        ...


class ClassGridClockPort(Protocol):
    def get_current_timezone(self):
        ...

    def make_aware(self, value, current_timezone):
        ...


class ClassGridWriterPort(Protocol):
    def create_schedule(self, command: ClassScheduleCreateCommand) -> ClassScheduleCreateResult:
        ...

    def update_session(self, command: ClassSessionUpdateCommand) -> UpdatedClassSessionRecord:
        ...

    def delete_session(self, command: ClassSessionDeleteCommand) -> DeletedClassSessionRecord:
        ...


class ClassGridAuditPort(Protocol):
    def record_schedule_created(self, *, command: ClassScheduleCreateCommand, result: ClassScheduleCreateResult) -> None:
        ...

    def record_session_updated(self, *, command: ClassSessionUpdateCommand, result: UpdatedClassSessionRecord) -> None:
        ...

    def record_session_deleted(self, *, command: ClassSessionDeleteCommand, result: DeletedClassSessionRecord) -> None:
        ...


__all__ = ['ClassGridAuditPort', 'ClassGridClockPort', 'ClassGridWriterPort', 'UnitOfWorkPort']