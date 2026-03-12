"""
ARQUIVO: portas do fluxo rapido de aluno.

POR QUE ELE EXISTE:
- Separa o caso de uso das implementacoes concretas em ORM, auditoria e transacao.

O QUE ESTE ARQUIVO FAZ:
1. Define escrita do aluno.
2. Define sincronizacao comercial e intake.
3. Define auditoria e unidade de trabalho.

PONTOS CRITICOS:
- As portas devem continuar pequenas e focadas no caso de uso atual.
"""

from collections.abc import Callable
from typing import Protocol, TypeVar

from .commands import StudentQuickCommand
from .commands import (
    StudentEnrollmentActionCommand,
    StudentEnrollmentSyncCommand,
    StudentIntakeSyncCommand,
    StudentPaymentActionCommand,
    StudentPaymentRegenerationCommand,
    StudentPaymentScheduleCommand,
)
from .results import (
    EnrollmentSyncRecord,
    StudentEnrollmentActionResult,
    StudentPaymentActionResult,
    StudentPaymentRegenerationResult,
    StudentPaymentScheduleResult,
    StudentQuickResult,
    StudentRecord,
)

ReturnType = TypeVar('ReturnType')


class StudentWriterPort(Protocol):
    def create(self, command: StudentQuickCommand) -> StudentRecord:
        ...

    def update(self, command: StudentQuickCommand) -> StudentRecord:
        ...


class StudentEnrollmentSyncPort(Protocol):
    def sync(self, *, student_id: int, command: StudentQuickCommand) -> EnrollmentSyncRecord:
        ...


class StudentEnrollmentWorkflowPort(Protocol):
    def sync(self, command: StudentEnrollmentSyncCommand) -> EnrollmentSyncRecord:
        ...


class StudentIntakeSyncPort(Protocol):
    def sync(self, *, student_id: int, intake_record_id: int | None) -> int | None:
        ...


class StudentIntakeWorkflowPort(Protocol):
    def sync(self, command: StudentIntakeSyncCommand) -> int | None:
        ...


class StudentQuickAuditPort(Protocol):
    def record_created(self, *, command: StudentQuickCommand, result: StudentQuickResult) -> None:
        ...

    def record_updated(self, *, command: StudentQuickCommand, result: StudentQuickResult) -> None:
        ...


class UnitOfWorkPort(Protocol):
    def run(self, operation: Callable[[], ReturnType]) -> ReturnType:
        ...


class StudentPaymentActionPort(Protocol):
    def execute(self, command: StudentPaymentActionCommand) -> StudentPaymentActionResult:
        ...


class StudentEnrollmentActionPort(Protocol):
    def execute(self, command: StudentEnrollmentActionCommand) -> StudentEnrollmentActionResult:
        ...


class StudentPaymentSchedulePort(Protocol):
    def execute(self, command: StudentPaymentScheduleCommand) -> StudentPaymentScheduleResult:
        ...


class StudentPaymentRegenerationPort(Protocol):
    def execute(self, command: StudentPaymentRegenerationCommand) -> StudentPaymentRegenerationResult:
        ...


__all__ = [
    'StudentEnrollmentSyncPort',
    'StudentEnrollmentActionPort',
    'StudentIntakeWorkflowPort',
    'StudentPaymentRegenerationPort',
    'StudentIntakeSyncPort',
    'StudentPaymentActionPort',
    'StudentPaymentSchedulePort',
    'StudentQuickAuditPort',
    'StudentWriterPort',
    'UnitOfWorkPort',
]
