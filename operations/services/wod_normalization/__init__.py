"""
ARQUIVO: pacote de servicos do SmartPlan — normalizacao de WOD via BYOLLM.

POR QUE ELE EXISTE:
- isola a logica de validacao do paste do GPT customizado e de hidratacao para os modelos
  relacionais de WOD (SessionWorkoutBlock, SessionWorkoutMovement).

O QUE ESTE ARQUIVO FAZ:
1. expoe `detect_smartplan_format` para validar texto colado.
2. expoe `hydrate_session_workout_from_payload` para popular blocos a partir do JSON.

PONTOS CRITICOS:
- nao deve ter dependencia de API externa em runtime.
- contrato com o GPT vive em prompts/smartplan_v1.md; mudou o formato, bumpe a versao.
"""

from operations.services.wod_normalization.response_parser import (
    detect_smartplan_format,
    detect_smartplan_text_format,
)

__all__ = [
    'detect_smartplan_format',
    'detect_smartplan_text_format',
]
