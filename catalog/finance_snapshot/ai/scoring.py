"""
ARQUIVO: builders de score historico da IA financeira.

POR QUE ELE EXISTE:
- concentra leituras de score derivadas dos analytics historicos.
"""


def build_recommendation_historical_score_map(analytics):
    analytics = analytics or {}
    score_map = {}
    for item in analytics.get('recommendation_performance', []):
        score_map[item['recommended_action']] = item.get('historical_score', 0.0) or 0.0
    return score_map


__all__ = ['build_recommendation_historical_score_map']
