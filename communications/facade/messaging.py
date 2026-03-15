"""
ARQUIVO: facade publica de messaging e operacao de communications.

POR QUE ELE EXISTE:
- cria um ponto de entrada estavel para webhook inbound, toque operacional, fila financeira e contato WhatsApp sem expor commands e adapters concretos.

O QUE ESTE ARQUIVO FAZ:
1. monta commands pequenos para os fluxos de communications.
2. chama os entrypoints concretos da aplicacao.
3. devolve resultados pequenos e previsiveis para as bordas externas.

PONTOS CRITICOS:
- esta camada organiza entrada e saida; nao deve duplicar regra de negocio.
"""

from dataclasses import dataclass

from communications.application.commands import (
    BuildOperationalQueueSnapshotCommand,
    FinanceCommunicationActionCommand,
    RegisterOperationalMessageCommand,
    build_register_inbound_whatsapp_message_command,
)
from communications.infrastructure import (
    ensure_whatsapp_contact_for_student,
    execute_build_operational_queue_snapshot_command,
    execute_finance_communication_action_command,
    execute_register_inbound_whatsapp_message_command,
    execute_register_operational_message_command,
)


@dataclass(frozen=True, slots=True)
class InboundWhatsAppFacadeResult:
    accepted: bool
    reason: str = ''
    contact_id: int | None = None
    message_log_id: int | None = None


@dataclass(frozen=True, slots=True)
class CommunicationsEnsureContactResult:
    contact_id: int
    contact_created: bool


@dataclass(frozen=True, slots=True)
class OperationalMessageFacadeResult:
    student_id: int
    contact_id: int
    message_log_id: int
    action_kind: str
    payment_id: int | None = None
    enrollment_id: int | None = None
    contact_created: bool = False
    blocked: bool = False


@dataclass(frozen=True, slots=True)
class FinanceCommunicationFacadeResult:
    student_id: int
    message_log_id: int
    blocked: bool = False


@dataclass(frozen=True, slots=True)
class OperationalQueueItemFacadeResult:
    kind: str
    title: str
    student_id: int
    payment_id: int | None
    enrollment_id: int | None
    pill: str
    pill_class: str
    summary: str
    suggested_message: str


@dataclass(frozen=True, slots=True)
class OperationalQueueSnapshotFacadeResult:
    items: tuple[OperationalQueueItemFacadeResult, ...]


def run_register_inbound_whatsapp_message(*, inbound_message) -> InboundWhatsAppFacadeResult:
    command = build_register_inbound_whatsapp_message_command(inbound_message=inbound_message)
    result = execute_register_inbound_whatsapp_message_command(command)
    return InboundWhatsAppFacadeResult(
        accepted=result.accepted,
        reason=result.reason,
        contact_id=result.contact_id,
        message_log_id=result.message_log_id,
    )


def ensure_student_whatsapp_contact(*, student_id: int) -> CommunicationsEnsureContactResult:
    contact, created = ensure_whatsapp_contact_for_student(student_id=student_id)
    return CommunicationsEnsureContactResult(contact_id=contact.id, contact_created=created)


def run_register_operational_message(
    *,
    actor_id: int | None,
    action_kind: str,
    student_id: int,
    payment_id: int | None = None,
    enrollment_id: int | None = None,
) -> OperationalMessageFacadeResult:
    result = execute_register_operational_message_command(
        RegisterOperationalMessageCommand(
            actor_id=actor_id,
            action_kind=action_kind,
            student_id=student_id,
            payment_id=payment_id,
            enrollment_id=enrollment_id,
        )
    )
    return OperationalMessageFacadeResult(
        student_id=result.student_id,
        contact_id=result.contact_id,
        message_log_id=result.message_log_id,
        action_kind=result.action_kind,
        payment_id=result.payment_id,
        enrollment_id=result.enrollment_id,
        contact_created=result.contact_created,
        blocked=result.blocked,
    )


def run_finance_communication_action(
    *,
    actor_id: int | None,
    action_kind: str,
    student_id: int,
    payment_id: int | None = None,
    enrollment_id: int | None = None,
) -> FinanceCommunicationFacadeResult:
    result = execute_finance_communication_action_command(
        FinanceCommunicationActionCommand(
            actor_id=actor_id,
            action_kind=action_kind,
            student_id=student_id,
            payment_id=payment_id,
            enrollment_id=enrollment_id,
        )
    )
    return FinanceCommunicationFacadeResult(
        student_id=result.student_id,
        message_log_id=result.message_log_id,
        blocked=result.blocked,
    )


def run_build_operational_queue_snapshot(*, limit: int = 9) -> OperationalQueueSnapshotFacadeResult:
    result = execute_build_operational_queue_snapshot_command(BuildOperationalQueueSnapshotCommand(limit=limit))
    return OperationalQueueSnapshotFacadeResult(
        items=tuple(
            OperationalQueueItemFacadeResult(
                kind=item.kind,
                title=item.title,
                student_id=item.student_id,
                payment_id=item.payment_id,
                enrollment_id=item.enrollment_id,
                pill=item.pill,
                pill_class=item.pill_class,
                summary=item.summary,
                suggested_message=item.suggested_message,
            )
            for item in result.items
        )
    )


__all__ = [
    'CommunicationsEnsureContactResult',
    'FinanceCommunicationFacadeResult',
    'InboundWhatsAppFacadeResult',
    'OperationalMessageFacadeResult',
    'OperationalQueueItemFacadeResult',
    'OperationalQueueSnapshotFacadeResult',
    'ensure_student_whatsapp_contact',
    'run_build_operational_queue_snapshot',
    'run_finance_communication_action',
    'run_register_inbound_whatsapp_message',
    'run_register_operational_message',
]