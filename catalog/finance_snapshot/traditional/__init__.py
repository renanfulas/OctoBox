"""
ARQUIVO: indice da camada tradicional do snapshot financeiro.

POR QUE ELE EXISTE:
- organiza a leitura financeira factual em um namespace proprio.
"""

from .base import build_finance_base, get_finance_filter_values, shift_month
from .comparison import build_comparison_peaks, build_monthly_comparison
from .metrics import (
    build_finance_interactive_kpis,
    build_finance_metrics,
    build_finance_priority_context,
    build_finance_pulse,
)
from .portfolio import build_plan_mix, build_plan_portfolio
from .trend_foundation import build_finance_trend_foundation

__all__ = [
    'build_comparison_peaks',
    'build_finance_base',
    'build_finance_interactive_kpis',
    'build_finance_metrics',
    'build_finance_priority_context',
    'build_finance_pulse',
    'build_finance_trend_foundation',
    'build_plan_mix',
    'build_monthly_comparison',
    'build_plan_portfolio',
    'get_finance_filter_values',
    'shift_month',
]
