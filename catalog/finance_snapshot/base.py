"""
ARQUIVO: fachada de compatibilidade para a base tradicional do snapshot financeiro.

ALVO CANONICO:
- `catalog.finance_snapshot.traditional.base`

REGRA:
- novos imports internos devem apontar para o modulo canonico
- esta fachada existe apenas para compatibilidade transitória
"""

from .traditional.base import build_finance_base, get_finance_filter_values, shift_month

__all__ = ['build_finance_base', 'get_finance_filter_values', 'shift_month']
