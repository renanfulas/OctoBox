"""
ARQUIVO: builders de timing e melhor jogada da IA financeira.

POR QUE ELE EXISTE:
- separa as leituras de janela e override temporal do motor historico bruto.
"""

from .common import RECOMMENDATION_ACTION_KIND_MAP


def build_best_action_by_timing_map(analytics):
    analytics = analytics or {}
    best_map = {}
    for item in analytics.get('recommendation_timing_matrix', []):
        stage = item.get('suggestion_window_stage') or 'unknown'
        current = best_map.get(stage)
        candidate_key = (
            item.get('success_rate', 0.0) or 0.0,
            item.get('realized_count', 0) or 0,
            -(item.get('average_queue_assist_score', 0.0) or 0.0),
        )
        if current is None:
            best_map[stage] = item
            continue
        current_key = (
            current.get('success_rate', 0.0) or 0.0,
            current.get('realized_count', 0) or 0,
            -(current.get('average_queue_assist_score', 0.0) or 0.0),
        )
        if candidate_key > current_key:
            best_map[stage] = item
    return best_map


def build_recommendation_timing_lookup_map(analytics):
    analytics = analytics or {}
    lookup = {}
    for item in analytics.get('recommendation_timing_matrix', []):
        lookup[(item.get('suggestion_window_stage') or 'unknown', item.get('recommended_action') or '')] = item
    return lookup


def build_timing_recommendation_override_map(
    analytics,
    *,
    min_realized_count=3,
    min_success_rate=70.0,
):
    analytics = analytics or {}
    prediction_window_map = build_best_prediction_window_by_action_map(
        analytics,
        min_realized_count=min_realized_count,
        min_success_rate=min_success_rate,
    )
    override_map = {}
    for item in analytics.get('recommendation_timing_matrix', []):
        stage = item.get('suggestion_window_stage') or 'unknown'
        recommended_action = item.get('recommended_action', '')
        preferred_window = prediction_window_map.get(recommended_action) or {}
        preferred_window_success_rate = preferred_window.get('success_rate', 0.0) or 0.0
        preferred_window_realized_count = preferred_window.get('realized_count', 0) or 0
        realized_count = item.get('realized_count', 0) or 0
        success_rate = item.get('success_rate', 0.0) or 0.0
        if preferred_window:
            if preferred_window_realized_count < min_realized_count or preferred_window_success_rate < min_success_rate:
                continue
        elif realized_count < min_realized_count or success_rate < min_success_rate:
            continue
        candidate = {
            'recommended_action': recommended_action,
            'success_rate': success_rate,
            'realized_count': realized_count,
            'suggestion_window_label': item.get('suggestion_window_label', ''),
            'average_queue_assist_score': item.get('average_queue_assist_score', 0.0) or 0.0,
            'preferred_outcome_window': preferred_window.get('outcome_window', ''),
            'preferred_window_success_rate': preferred_window_success_rate,
            'preferred_window_realized_count': preferred_window_realized_count,
            'min_realized_count': min_realized_count,
            'min_success_rate': min_success_rate,
            'rule_name': 'timing_override_v2',
        }
        current = override_map.get(stage)
        candidate_key = (
            candidate['preferred_window_success_rate'],
            candidate['success_rate'],
            candidate['preferred_window_realized_count'],
            candidate['realized_count'],
            -(candidate['average_queue_assist_score']),
        )
        if current is None:
            override_map[stage] = candidate
            continue
        current_key = (
            current.get('preferred_window_success_rate', 0.0) or 0.0,
            current.get('success_rate', 0.0) or 0.0,
            current.get('preferred_window_realized_count', 0) or 0,
            current.get('realized_count', 0) or 0,
            -(current.get('average_queue_assist_score', 0.0) or 0.0),
        )
        if candidate_key > current_key:
            override_map[stage] = candidate
    return override_map


def build_best_prediction_window_by_action_map(
    analytics,
    *,
    min_realized_count=3,
    min_success_rate=60.0,
):
    analytics = analytics or {}
    best_map = {}
    for item in analytics.get('recommendation_window_matrix', []):
        recommended_action = item.get('recommended_action') or ''
        if not recommended_action:
            continue
        realized_count = item.get('realized_count', 0) or 0
        success_rate = item.get('success_rate', 0.0) or 0.0
        if realized_count < min_realized_count or success_rate < min_success_rate:
            continue
        current = best_map.get(recommended_action)
        candidate_key = (
            success_rate,
            realized_count,
            item.get('outcome_window') or '',
        )
        if current is None:
            best_map[recommended_action] = {
                'outcome_window': item.get('outcome_window', ''),
                'success_rate': success_rate,
                'realized_count': realized_count,
                'min_realized_count': min_realized_count,
                'min_success_rate': min_success_rate,
                'rule_name': 'prediction_window_override_v1',
            }
            continue
        current_key = (
            current.get('success_rate', 0.0) or 0.0,
            current.get('realized_count', 0) or 0,
            current.get('outcome_window') or '',
        )
        if candidate_key > current_key:
            best_map[recommended_action] = {
                'outcome_window': item.get('outcome_window', ''),
                'success_rate': success_rate,
                'realized_count': realized_count,
                'min_realized_count': min_realized_count,
                'min_success_rate': min_success_rate,
                'rule_name': 'prediction_window_override_v1',
            }
    return best_map


def build_turn_recommendation(analytics):
    analytics = analytics or {}
    recommendation_window_matrix = analytics.get('recommendation_window_matrix', []) or []
    if not recommendation_window_matrix:
        return {
            'title': 'Melhor jogada agora',
            'recommended_action': '',
            'action_kind': '',
            'action_label': 'Sem leitura suficiente',
            'summary': 'Assim que houver historico suficiente de acao dentro da janela prevista, a jogada mais forte aparece aqui.',
            'note': 'Leitura baseada no historico acumulado atual; um recorte semanal dedicado pode entrar depois.',
        }

    item = recommendation_window_matrix[0]
    recommended_action = item.get('recommended_action', '')
    return {
        'title': 'Melhor jogada agora',
        'recommended_action': recommended_action,
        'action_kind': RECOMMENDATION_ACTION_KIND_MAP.get(recommended_action, ''),
        'action_label': recommended_action,
        'summary': '',
        'note': 'Leitura baseada no historico acumulado atual; um recorte semanal dedicado pode entrar depois.',
        'outcome_window': item.get('outcome_window', ''),
        'success_rate': item.get('success_rate', 0.0) or 0.0,
        'realized_count': item.get('realized_count', 0) or 0,
    }


__all__ = [
    'build_best_action_by_timing_map',
    'build_best_prediction_window_by_action_map',
    'build_recommendation_timing_lookup_map',
    'build_timing_recommendation_override_map',
    'build_turn_recommendation',
]
