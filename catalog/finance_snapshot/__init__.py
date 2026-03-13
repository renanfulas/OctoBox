"""
ARQUIVO: indice do snapshot financeiro canonico do catalogo.

POR QUE ELE EXISTE:
- reune a montagem do snapshot financeiro no app real catalog, sem passar pelo namespace legado.

O QUE ESTE ARQUIVO FAZ:
1. exporta o construtor principal do snapshot financeiro.

PONTOS CRITICOS:
- a assinatura publica precisa continuar estavel para views e exportacoes.
"""

from .snapshot import build_finance_snapshot

__all__ = ['build_finance_snapshot']