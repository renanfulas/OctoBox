"""
ARQUIVO: facade publica do workspace operacional.

POR QUE ELE EXISTE:
- cria um ponto de entrada estavel para snapshots e mutacoes do workspace sem expor queries, commands e wiring interno a views e fachadas legadas.

O QUE ESTE ARQUIVO FAZ:
1. expoe snapshots prontos por papel para owner, dev, manager e coach.
2. monta commands pequenos para as mutacoes do workspace.
3. chama os entrypoints concretos da aplicacao e devolve resultados previsiveis.

PONTOS CRITICOS:
- esta camada organiza entrada e saida; nao deve duplicar regra de negocio.
"""

from dataclasses import dataclass

from operations.application.workspace_commands import (
    build_apply_attendance_action_command,
    build_create_technical_behavior_note_command,
    build_link_payment_enrollment_command,
)
from operations.infrastructure import (
    execute_apply_attendance_action_command,
    execute_create_technical_behavior_note_command,
    execute_link_payment_enrollment_command,
)
from operations.queries import (
    build_coach_workspace_snapshot as _build_coach_workspace_snapshot,
    build_dev_workspace_snapshot as _build_dev_workspace_snapshot,
    build_manager_workspace_snapshot as _build_manager_workspace_snapshot,
    build_owner_workspace_snapshot as _build_owner_workspace_snapshot,
    build_reception_preview_workspace_snapshot as _build_reception_preview_workspace_snapshot,
)


@dataclass(frozen=True, slots=True)
class WorkspaceLinkPaymentResult:
    payment_id: int
    enrollment_id: int


@dataclass(frozen=True, slots=True)
class WorkspaceTechnicalBehaviorNoteResult:
    note_id: int


@dataclass(frozen=True, slots=True)
class WorkspaceAttendanceActionResult:
    attendance_id: int
    status: str


def build_owner_workspace_snapshot(*, today):
    return _build_owner_workspace_snapshot(today=today)


def build_dev_workspace_snapshot():
    return _build_dev_workspace_snapshot()


def build_manager_workspace_snapshot():
    return _build_manager_workspace_snapshot()


def build_coach_workspace_snapshot(*, today):
    return _build_coach_workspace_snapshot(today=today)


def build_reception_preview_workspace_snapshot(*, today):
    return _build_reception_preview_workspace_snapshot(today=today)


def run_link_payment_enrollment(*, actor_id: int | None, payment_id: int) -> WorkspaceLinkPaymentResult | None:
    command = build_link_payment_enrollment_command(actor_id=actor_id, payment_id=payment_id)
    result = execute_link_payment_enrollment_command(command)
    if result is None:
        return None
    return WorkspaceLinkPaymentResult(payment_id=result.payment_id, enrollment_id=result.enrollment_id)


def run_create_technical_behavior_note(
    *,
    actor_id: int | None,
    student_id: int,
    category: str,
    description: str,
) -> WorkspaceTechnicalBehaviorNoteResult | None:
    command = build_create_technical_behavior_note_command(
        actor_id=actor_id,
        student_id=student_id,
        category=category,
        description=description,
    )
    result = execute_create_technical_behavior_note_command(command)
    if result is None:
        return None
    return WorkspaceTechnicalBehaviorNoteResult(note_id=result.note_id)


def run_apply_attendance_action(
    *,
    actor_id: int | None,
    attendance_id: int,
    action: str,
) -> WorkspaceAttendanceActionResult | None:
    command = build_apply_attendance_action_command(
        actor_id=actor_id,
        attendance_id=attendance_id,
        action=action,
    )
    result = execute_apply_attendance_action_command(command)
    if result is None:
        return None
    return WorkspaceAttendanceActionResult(attendance_id=result.attendance_id, status=result.status)


__all__ = [
    'WorkspaceAttendanceActionResult',
    'WorkspaceLinkPaymentResult',
    'WorkspaceTechnicalBehaviorNoteResult',
    'build_coach_workspace_snapshot',
    'build_dev_workspace_snapshot',
    'build_manager_workspace_snapshot',
    'build_owner_workspace_snapshot',
    'build_reception_preview_workspace_snapshot',
    'run_apply_attendance_action',
    'run_create_technical_behavior_note',
    'run_link_payment_enrollment',
]