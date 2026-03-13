"""
ARQUIVO: indice compativel do snapshot financeiro modularizado.

POR QUE ELE EXISTE:
- mantem imports historicos enquanto a implementacao canonica vive em catalog.finance_snapshot.

O QUE ESTE ARQUIVO FAZ:
1. reexporta o construtor principal do snapshot financeiro.

PONTOS CRITICOS:
- a assinatura publica precisa continuar estavel para views e exportacoes antigas.
"""

from catalog.finance_snapshot import build_finance_snapshot

__all__ = ['build_finance_snapshot']