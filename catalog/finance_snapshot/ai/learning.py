"""
ARQUIVO: builders de aprendizado contextual da IA financeira.

POR QUE ELE EXISTE:
- separa as heuristicas de divergencia e tensao do motor historico bruto.
"""

from .common import ACTION_KIND_CONTEXTUAL_RECOMMENDATION_MAP


def build_contextual_recommendation_map(
    analytics,
    *,
    min_realized_count=2,
    min_success_rate=70.0,
):
    analytics = analytics or {}
    contextual_map = {}
    for item in analytics.get('compound_divergent_action_matrix', []):
        context_key = (
            item.get('recommended_action') or '',
            item.get('suggestion_window_stage') or 'unknown',
            item.get('signal_bucket') or 'unknown',
        )
        realized_count = item.get('realized_count', 0) or 0
        success_rate = item.get('success_rate', 0.0) or 0.0
        if realized_count < min_realized_count or success_rate < min_success_rate:
            continue
        candidate = {
            'suggested_action_kind': item.get('realized_action_kind', ''),
            'suggested_recommended_action': ACTION_KIND_CONTEXTUAL_RECOMMENDATION_MAP.get(
                item.get('realized_action_kind', ''),
                '',
            ),
            'success_rate': success_rate,
            'realized_count': realized_count,
            'rule_name': 'contextual_compound_guidance_v1',
            'min_realized_count': min_realized_count,
            'min_success_rate': min_success_rate,
        }
        current = contextual_map.get(context_key)
        candidate_key = (
            candidate['success_rate'],
            candidate['realized_count'],
            candidate['suggested_action_kind'],
        )
        if current is None:
            contextual_map[context_key] = candidate
            continue
        current_key = (
            current.get('success_rate', 0.0) or 0.0,
            current.get('realized_count', 0) or 0,
            current.get('suggested_action_kind', ''),
        )
        if candidate_key > current_key:
            contextual_map[context_key] = candidate
    return contextual_map


def build_turn_priority_tension_context_map(
    analytics,
    *,
    min_realized_count=2,
    min_rate_gap=10.0,
):
    analytics = analytics or {}
    tension_map = {}
    for item in analytics.get('turn_priority_tension_compound_matrix', []):
        context_key = (
            item.get('suggestion_window_stage') or 'unknown',
            item.get('signal_bucket') or 'unknown',
        )
        realized_count = item.get('realized_count', 0) or 0
        healthy_rate = item.get('healthy_tension_rate', 0.0) or 0.0
        dangerous_rate = item.get('dangerous_tension_rate', 0.0) or 0.0
        if realized_count < min_realized_count:
            continue
        rate_gap = round(abs(healthy_rate - dangerous_rate), 1)
        if rate_gap <= min_rate_gap:
            tendency = 'mixed'
        else:
            tendency = 'healthy' if healthy_rate > dangerous_rate else 'dangerous'
        candidate = {
            'tendency': tendency,
            'healthy_tension_rate': healthy_rate,
            'dangerous_tension_rate': dangerous_rate,
            'realized_count': realized_count,
            'rule_name': 'turn_priority_tension_context_v1',
            'min_realized_count': min_realized_count,
            'min_rate_gap': min_rate_gap,
        }
        current = tension_map.get(context_key)
        candidate_key = (rate_gap, realized_count, healthy_rate)
        if current is None:
            tension_map[context_key] = candidate
            continue
        current_gap = abs(
            (current.get('healthy_tension_rate', 0.0) or 0.0)
            - (current.get('dangerous_tension_rate', 0.0) or 0.0)
        )
        current_key = (
            current_gap,
            current.get('realized_count', 0) or 0,
            current.get('healthy_tension_rate', 0.0) or 0.0,
        )
        if candidate_key > current_key:
            tension_map[context_key] = candidate
    return tension_map


__all__ = [
    'build_contextual_recommendation_map',
    'build_turn_priority_tension_context_map',
]
