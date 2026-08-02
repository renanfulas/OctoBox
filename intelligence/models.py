"""
ARQUIVO: superficie estavel de modelos do app intelligence.

POR QUE ELE EXISTE:
- reduz imports diretos de model_definitions ao expor o contrato estavel.

O QUE ESTE ARQUIVO FAZ:
1. reexporta models e enums publicos do app intelligence.
"""

from intelligence.model_definitions import (
    INTELLIGENCE_APP_LABEL,
    LeadChannelDailyFact,
    LeadChannelProvenance,
)

__all__ = [
    'INTELLIGENCE_APP_LABEL',
    'LeadChannelDailyFact',
    'LeadChannelProvenance',
]
