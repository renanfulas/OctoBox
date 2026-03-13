"""
ARQUIVO: portas das acoes do workspace operacional.

POR QUE ELE EXISTE:
- separa os casos de uso operacionais da implementacao Django concreta.

O QUE ESTE ARQUIVO FAZ:
1. define unidade de trabalho para mutacoes do workspace.
2. define contratos de escrita e auditoria.

PONTOS CRITICOS:
- os contratos precisam seguir pequenos para futuros adapters.
"""

from typing import Callable, Protocol, TypeVar

from .workspace_commands import (
    ApplyAttendanceActionCommand,
    CreateTechnicalBehaviorNoteCommand,
    LinkPaymentEnrollmentCommand,
)
from .workspace_results import AttendanceActionResult, LinkedPaymentEnrollmentResult, TechnicalBehaviorNoteResult


ResultType = TypeVar('ResultType')


class WorkspaceClockPort(Protocol):
    def now(self):
        ...


class WorkspaceUnitOfWorkPort(Protocol):
    def run(self, operation: Callable[[], ResultType]) -> ResultType:
        ...


class WorkspaceActionWriterPort(Protocol):
    def link_payment_enrollment(self, command: LinkPaymentEnrollmentCommand) -> LinkedPaymentEnrollmentResult | None:
        ...

    def create_technical_behavior_note(
        self,
        command: CreateTechnicalBehaviorNoteCommand,
    ) -> TechnicalBehaviorNoteResult | None:
        ...

    def apply_attendance_action(self, command: ApplyAttendanceActionCommand) -> AttendanceActionResult | None:
        ...


class WorkspaceActionAuditPort(Protocol):
    def record_payment_enrollment_linked(
        self,
        *,
        command: LinkPaymentEnrollmentCommand,
        result: LinkedPaymentEnrollmentResult | None,
    ) -> None:
        ...

    def record_technical_behavior_note_created(
        self,
        *,
        command: CreateTechnicalBehaviorNoteCommand,
        result: TechnicalBehaviorNoteResult | None,
    ) -> None:
        ...

    def record_attendance_action_applied(
        self,
        *,
        command: ApplyAttendanceActionCommand,
        result: AttendanceActionResult | None,
    ) -> None:
        ...


__all__ = ['WorkspaceActionAuditPort', 'WorkspaceActionWriterPort', 'WorkspaceClockPort', 'WorkspaceUnitOfWorkPort']