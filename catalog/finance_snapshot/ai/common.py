"""
ARQUIVO: helpers e constantes compartilhadas da IA financeira.

POR QUE ELE EXISTE:
- evita duplicar mapas e funcoes pequenas entre analytics, timing e score.
"""

RECOMMENDATION_ACTION_KIND_MAP = {
    'review_winback': 'reactivation',
    'monitor_recent_reactivation': 'reactivation',
    'escalate_manual_retention': 'overdue',
    'send_financial_followup': 'overdue',
    'monitor_and_nudge': 'overdue',
    'observe_payment_resolution': 'overdue',
}

ACTION_KIND_CONTEXTUAL_RECOMMENDATION_MAP = {
    'overdue': 'send_financial_followup',
    'reactivation': 'review_winback',
}


def safe_rate(numerator, denominator):
    if not denominator:
        return 0.0
    return round((numerator / denominator) * 100, 1)


def historical_score(*, execution_rate, success_rate):
    return round((execution_rate * 0.4) + (success_rate * 0.6), 1)


__all__ = [
    'ACTION_KIND_CONTEXTUAL_RECOMMENDATION_MAP',
    'RECOMMENDATION_ACTION_KIND_MAP',
    'historical_score',
    'safe_rate',
]
