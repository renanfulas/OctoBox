"""
ARQUIVO: superficie publica transitoria dos modelos de communications.

POR QUE ELE EXISTE:
- Permite que services, queries e integracoes passem a importar do app real de communications sem trocar ainda o app label historico dos modelos.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta intake e modelos de WhatsApp ligados ao dominio de comunicacao.
2. Mantem enums e classes em um ponto previsivel para a transicao.

PONTOS CRITICOS:
- Os modelos reais ainda pertencem a boxcore nesta fase.
"""

from boxcore.models.onboarding import IntakeSource, IntakeStatus, StudentIntake

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
