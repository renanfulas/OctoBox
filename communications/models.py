"""
ARQUIVO: superficie publica transitoria dos modelos de communications.

POR QUE ELE EXISTE:
- Permite que services, queries e integracoes passem a importar do app real de communications sem trocar ainda o app label historico dos modelos.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta os modelos de WhatsApp ligados ao dominio de comunicacao.
2. Reaproveita a superficie estavel de onboarding para intake durante a transicao.

PONTOS CRITICOS:
- Os modelos reais ainda pertencem ao estado historico de boxcore nesta fase.
"""

from onboarding.models import IntakeSource, IntakeStatus, StudentIntake

from .model_definitions.whatsapp import (
    MessageDirection,
    MessageKind,
    WhatsAppContact,
    WhatsAppContactStatus,
    WhatsAppMessageLog,
)

__all__ = [
    'IntakeSource',
    'IntakeStatus',
    'MessageDirection',
    'MessageKind',
    'StudentIntake',
    'WhatsAppContact',
    'WhatsAppContactStatus',
    'WhatsAppMessageLog',
]
