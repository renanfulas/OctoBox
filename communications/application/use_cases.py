"""
ARQUIVO: casos de uso do dominio de communications.

POR QUE ELE EXISTE:
- Centraliza a entrada do domínio de communications em use cases reutilizáveis.

O QUE ESTE ARQUIVO FAZ:
1. Orquestra o registro inbound de WhatsApp.
2. Orquestra o toque operacional outbound.

PONTOS CRITICOS:
- A camada de aplicacao continua sem depender de Django ou ORM concretos.
"""

from .commands import (
    BuildOperationalQueueSnapshotCommand,
    FinanceCommunicationActionCommand,
    RegisterInboundWhatsAppMessageCommand,
    RegisterOperationalMessageCommand,
)
from .ports import (
    FinanceCommunicationActionPort,
    InboundWhatsAppMessagePort,
    OperationalMessagePort,
    OperationalQueueSnapshotPort,
)
from .results import (
    FinanceCommunicationActionResult,
    InboundWhatsAppMessageResult,
    OperationalMessageResult,
    OperationalQueueSnapshotResult,
)


def execute_register_inbound_whatsapp_message_use_case(
    command: RegisterInboundWhatsAppMessageCommand,
    *,
    inbound_port: InboundWhatsAppMessagePort,
) -> InboundWhatsAppMessageResult:
    return inbound_port.register(command)


def execute_register_operational_message_use_case(
    command: RegisterOperationalMessageCommand,
    *,
    operational_port: OperationalMessagePort,
) -> OperationalMessageResult:
    return operational_port.register(command)


def execute_finance_communication_action_use_case(
    command: FinanceCommunicationActionCommand,
    *,
    finance_action_port: FinanceCommunicationActionPort,
) -> FinanceCommunicationActionResult:
    return finance_action_port.execute(command)


def execute_build_operational_queue_snapshot_use_case(
    command: BuildOperationalQueueSnapshotCommand,
    *,
    snapshot_port: OperationalQueueSnapshotPort,
) -> OperationalQueueSnapshotResult:
    return snapshot_port.build_snapshot(command)


__all__ = [
    'execute_build_operational_queue_snapshot_use_case',
    'execute_finance_communication_action_use_case',
    'execute_register_inbound_whatsapp_message_use_case',
    'execute_register_operational_message_use_case',
]
