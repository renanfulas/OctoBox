"""
ARQUIVO: portas do dominio de communications.

POR QUE ELE EXISTE:
- Separa os use cases das implementações concretas em ORM, auditoria e integração.

O QUE ESTE ARQUIVO FAZ:
1. Define a porta do fluxo inbound de WhatsApp.
2. Define a porta do fluxo operacional outbound.

PONTOS CRITICOS:
- As portas devem ser pequenas e focadas no caso de uso atual.
"""

from typing import Protocol

from .commands import (
    BuildOperationalQueueSnapshotCommand,
    FinanceCommunicationActionCommand,
    RegisterInboundWhatsAppMessageCommand,
    RegisterOperationalMessageCommand,
)
from .results import (
    FinanceCommunicationActionResult,
    InboundWhatsAppMessageResult,
    OperationalMessageResult,
    OperationalQueueSnapshotResult,
)


class ClockPort(Protocol):
    def now(self):
        ...

    def today(self):
        ...


class InboundWhatsAppMessagePort(Protocol):
    def register(self, command: RegisterInboundWhatsAppMessageCommand) -> InboundWhatsAppMessageResult:
        ...


class OperationalMessagePort(Protocol):
    def register(self, command: RegisterOperationalMessageCommand) -> OperationalMessageResult:
        ...


class OperationalMessageAuditPort(Protocol):
    def record_registered(
        self,
        *,
        command: RegisterOperationalMessageCommand,
        result: OperationalMessageResult,
    ) -> None:
        ...


class FinanceCommunicationActionPort(Protocol):
    def execute(self, command: FinanceCommunicationActionCommand) -> FinanceCommunicationActionResult:
        ...


class OperationalQueueSnapshotPort(Protocol):
    def build_snapshot(self, command: BuildOperationalQueueSnapshotCommand) -> OperationalQueueSnapshotResult:
        ...


__all__ = [
    'ClockPort',
    'FinanceCommunicationActionPort',
    'InboundWhatsAppMessagePort',
    'OperationalMessageAuditPort',
    'OperationalMessagePort',
    'OperationalQueueSnapshotPort',
]
