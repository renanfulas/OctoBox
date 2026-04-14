"""
ARQUIVO: fachada de compatibilidade para carteira da camada tradicional.

ALVO CANONICO:
- `catalog.finance_snapshot.traditional.portfolio`

REGRA:
- novos imports internos devem apontar para o modulo canonico
- esta fachada existe apenas para compatibilidade transitória
"""

from .traditional.portfolio import build_plan_mix, build_plan_portfolio

__all__ = ['build_plan_mix', 'build_plan_portfolio']
