"""
ARQUIVO: indice da camada de IA do snapshot financeiro.

POR QUE ELE EXISTE:
- organiza a frente assistida do financeiro em modulos menores.
- preserva um ponto unico de import para analytics, timing, score e aprendizado.
"""

from .analytics import build_finance_follow_up_analytics
from .foundation import build_financial_churn_foundation
from .learning import build_contextual_recommendation_map, build_turn_priority_tension_context_map
from .recommendation import build_recommendation_state
from .scoring import build_recommendation_historical_score_map
from .timing import (
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
    'build_financial_churn_foundation',
    'build_finance_follow_up_analytics',
    'build_recommendation_state',
    'build_recommendation_historical_score_map',
    'build_recommendation_timing_lookup_map',
    'build_timing_recommendation_override_map',
    'build_turn_priority_tension_context_map',
    'build_turn_recommendation',
]
