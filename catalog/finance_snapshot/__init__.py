"""
ARQUIVO: indice do snapshot financeiro canonico do catalogo.

POR QUE ELE EXISTE:
- reune a montagem do snapshot financeiro no app real catalog, sem passar pelo namespace legado.

O QUE ESTE ARQUIVO FAZ:
1. exporta o construtor principal do snapshot financeiro.

PONTOS CRITICOS:
- a assinatura publica precisa continuar estavel para views e exportacoes.
"""

from .churn_foundation import build_financial_churn_foundation
from .snapshot import build_finance_flow_bridge, build_finance_snapshot

__all__ = ['build_financial_churn_foundation', 'build_finance_flow_bridge', 'build_finance_snapshot']
