"""
ARQUIVO: fachada de compatibilidade para analytics de follow-up financeiro.

POR QUE ELE EXISTE:
- preserva os imports publicos enquanto a Onda 1 move o motor historico para `finance_snapshot.ai`.

ALVO CANONICO:
- `catalog.finance_snapshot.ai`

REGRA:
- novos imports internos devem apontar para `catalog.finance_snapshot.ai`
- esta fachada existe apenas para compatibilidade transitória
"""

from .ai.analytics import build_finance_follow_up_analytics
from .ai.learning import build_contextual_recommendation_map, build_turn_priority_tension_context_map
from .ai.scoring import build_recommendation_historical_score_map
from .ai.timing import (
    build_best_action_by_timing_map,
    build_best_prediction_window_by_action_map,
    build_recommendation_timing_lookup_map,
    build_timing_recommendation_override_map,
    build_turn_recommendation,
)

__all__ = [
    'build_best_action_by_timing_map',
    'build_best_prediction_window_by_action_map',
    'build_contextual_recommendation_map',
    'build_finance_follow_up_analytics',
    'build_recommendation_historical_score_map',
    'build_recommendation_timing_lookup_map',
    'build_turn_priority_tension_context_map',
    'build_turn_recommendation',
    'build_timing_recommendation_override_map',
]
