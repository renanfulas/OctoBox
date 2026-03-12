"""
ARQUIVO: indice do snapshot financeiro modularizado.

POR QUE ELE EXISTE:
- Reune a montagem do snapshot financeiro em modulos menores sem quebrar imports antigos.

O QUE ESTE ARQUIVO FAZ:
1. Exporta o construtor principal do snapshot financeiro.

PONTOS CRITICOS:
- A assinatura publica precisa continuar estavel para views e exportacoes.
"""

from .snapshot import build_finance_snapshot

__all__ = ['build_finance_snapshot']