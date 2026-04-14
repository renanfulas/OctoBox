"""
ARQUIVO: fachada de compatibilidade da fundacao de churn financeiro.

POR QUE ELE EXISTE:
- preserva o ponto de import publico enquanto a Onda 2 move a fundacao para `finance_snapshot.ai`.

ALVO CANONICO:
- `catalog.finance_snapshot.ai.foundation`

REGRA:
- novos imports internos devem apontar para `catalog.finance_snapshot.ai`
- esta fachada existe apenas para compatibilidade transitória
"""

from .ai.foundation import build_financial_churn_foundation

__all__ = ['build_financial_churn_foundation']
