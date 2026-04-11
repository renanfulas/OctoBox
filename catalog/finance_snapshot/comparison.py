"""
ARQUIVO: fachada de compatibilidade para comparativos da camada tradicional.

ALVO CANONICO:
- `catalog.finance_snapshot.traditional.comparison`

REGRA:
- novos imports internos devem apontar para o modulo canonico
- esta fachada existe apenas para compatibilidade transitória
"""

from .traditional.comparison import build_comparison_peaks, build_monthly_comparison

__all__ = ['build_comparison_peaks', 'build_monthly_comparison']
