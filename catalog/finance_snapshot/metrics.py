"""
ARQUIVO: fachada de compatibilidade para metricas da camada tradicional.

ALVO CANONICO:
- `catalog.finance_snapshot.traditional.metrics`

REGRA:
- novos imports internos devem apontar para o modulo canonico
- esta fachada existe apenas para compatibilidade transitória
"""

from .traditional.metrics import (
    build_finance_interactive_kpis,
    build_finance_metrics,
    build_finance_priority_context,
    build_finance_pulse,
)

__all__ = [
    'build_finance_interactive_kpis',
    'build_finance_metrics',
    'build_finance_priority_context',
    'build_finance_pulse',
]
