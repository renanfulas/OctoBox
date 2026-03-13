"""
ARQUIVO: entradas publicas por capacidade do app communications.

POR QUE ELE EXISTE:
- cria um ponto de entrada estavel para inbound WhatsApp, toques operacionais e fila financeira sem expor wiring interno ao runtime.

O QUE ESTE ARQUIVO FAZ:
1. expoe a facade publica de messaging e operacao.
2. estabiliza a fronteira publica de communications para consumo por integracoes, catalogo e outras cascas.

PONTOS CRITICOS:
- esta camada organiza entrada e saida; regra continua em domain/application e detalhe tecnico em infrastructure.
"""

from .messaging import (
    CommunicationsEnsureContactResult,
    FinanceCommunicationFacadeResult,
    InboundWhatsAppFacadeResult,
    OperationalMessageFacadeResult,
    OperationalQueueItemFacadeResult,
    OperationalQueueSnapshotFacadeResult,
    ensure_student_whatsapp_contact,
    run_build_operational_queue_snapshot,
    run_finance_communication_action,
    run_register_inbound_whatsapp_message,
    run_register_operational_message,
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