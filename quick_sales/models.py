"""
ARQUIVO: superficie estavel de modelos do dominio quick_sales.

POR QUE ELE EXISTE:
- reduz imports diretos de model_definitions ao expor o contrato estavel de quick_sales.

O QUE ESTE ARQUIVO FAZ:
1. reexporta models e enums publicos do dominio quick_sales.

PONTOS CRITICOS:
- esta superficie deve permanecer pequena e previsivel para queries, forms e adapters.
"""

from quick_sales.model_definitions import (
    QuickProductAlias,
    QuickProductTemplate,
    QuickSale,
    QuickSaleResolutionMode,
    QuickSaleStatus,
)

__all__ = [
    'QuickProductAlias',
    'QuickProductTemplate',
    'QuickSale',
    'QuickSaleResolutionMode',
    'QuickSaleStatus',
]
