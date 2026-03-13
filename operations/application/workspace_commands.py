"""
ARQUIVO: commands das acoes do workspace operacional.

POR QUE ELE EXISTE:
- transforma inputs das telas operacionais em contratos pequenos e estaveis.

O QUE ESTE ARQUIVO FAZ:
1. define commands para vinculo financeiro, ocorrencia tecnica e presenca.
2. traduz ids e dados simples vindos da camada HTTP.

PONTOS CRITICOS:
- qualquer mutacao nova do workspace deve entrar aqui para manter o contrato explicito.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LinkPaymentEnrollmentCommand:
    actor_id: int | None
    payment_id: int


@dataclass(frozen=True, slots=True)
class CreateTechnicalBehaviorNoteCommand:
    actor_id: int | None
    student_id: int
    category: str
    description: str


@dataclass(frozen=True, slots=True)
class ApplyAttendanceActionCommand:
    actor_id: int | None
    attendance_id: int
    action: str


def build_link_payment_enrollment_command(*, actor_id: int | None, payment_id: int) -> LinkPaymentEnrollmentCommand:
    return LinkPaymentEnrollmentCommand(actor_id=actor_id, payment_id=payment_id)


def build_create_technical_behavior_note_command(
    *,
    actor_id: int | None,
    student_id: int,
    category: str,
    description: str,
) -> CreateTechnicalBehaviorNoteCommand:
    return CreateTechnicalBehaviorNoteCommand(
        actor_id=actor_id,
        student_id=student_id,
        category=category,
        description=description,
    )


def build_apply_attendance_action_command(
    *,
    actor_id: int | None,
    attendance_id: int,
    action: str,
) -> ApplyAttendanceActionCommand:
    return ApplyAttendanceActionCommand(actor_id=actor_id, attendance_id=attendance_id, action=action)


__all__ = [
    'ApplyAttendanceActionCommand',
    'CreateTechnicalBehaviorNoteCommand',
    'LinkPaymentEnrollmentCommand',
    'build_apply_attendance_action_command',
    'build_create_technical_behavior_note_command',
    'build_link_payment_enrollment_command',
]