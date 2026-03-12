"""
ARQUIVO: resultados explicitos do dominio de communications.

POR QUE ELE EXISTE:
- Evita retorno solto e estabiliza o contrato interno dos fluxos do dominio.

O QUE ESTE ARQUIVO FAZ:
1. Define resultado do registro inbound de WhatsApp.
2. Define resultado do toque operacional outbound.

PONTOS CRITICOS:
- Estes resultados precisam continuar pequenos e fáceis de adaptar para contratos públicos existentes.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InboundWhatsAppMessageResult:
    accepted: bool
    reason: str = ''
    contact_id: int | None = None
    message_log_id: int | None = None


@dataclass(frozen=True, slots=True)
class OperationalMessageResult:
    student_id: int
    contact_id: int
    message_log_id: int
    action_kind: str


@dataclass(frozen=True, slots=True)
class FinanceCommunicationActionResult:
    student_id: int
    message_log_id: int


@dataclass(frozen=True, slots=True)
class OperationalQueueItemResult:
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
class OperationalQueueSnapshotResult:
    items: tuple[OperationalQueueItemResult, ...]


__all__ = [
    'FinanceCommunicationActionResult',
    'InboundWhatsAppMessageResult',
    'OperationalMessageResult',
    'OperationalQueueItemResult',
    'OperationalQueueSnapshotResult',
]
