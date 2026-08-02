"""
ARQUIVO: superficie estavel de modelos do app intelligence_network.

POR QUE ELE EXISTE:
- reduz imports diretos de model_definitions ao expor o contrato estavel.
"""

from intelligence_network.model_definitions import (
    INTELLIGENCE_NETWORK_APP_LABEL,
    NetworkChannelAggregate,
)

__all__ = ['INTELLIGENCE_NETWORK_APP_LABEL', 'NetworkChannelAggregate']
