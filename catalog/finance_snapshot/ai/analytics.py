"""
ARQUIVO: motor historico de analytics da IA financeira.

POR QUE ELE EXISTE:
- concentra a agregacao historica bruta dos follow-ups.
- deixa timing, score e aprendizado contextual em modulos menores.
"""

from __future__ import annotations

from collections import defaultdict

from .analytics_learning import build_learning_analytics_sections
from .analytics_recommendation import build_recommendation_analytics_sections


def build_finance_follow_up_analytics(*, follow_ups):
    follow_up_rows = list(follow_ups)

    by_recommendation = defaultdict(list)
    by_realized_action = defaultdict(list)
    by_window = defaultdict(list)
    by_window_stage = defaultdict(list)
    by_recommendation_and_stage = defaultdict(list)
    by_recommendation_and_window = defaultdict(list)

    for follow_up in follow_up_rows:
        by_recommendation[follow_up.recommended_action].append(follow_up)
        if follow_up.realized_action_kind:
            by_realized_action[follow_up.realized_action_kind].append(follow_up)
        by_window[follow_up.outcome_window].append(follow_up)
        suggestion_window_stage = follow_up.suggestion_window_stage or 'unknown'
        by_window_stage[suggestion_window_stage].append(follow_up)
        by_recommendation_and_stage[(follow_up.recommended_action, suggestion_window_stage)].append(follow_up)
        by_recommendation_and_window[(follow_up.recommended_action, follow_up.outcome_window)].append(follow_up)

    recommendation_sections = build_recommendation_analytics_sections(
        by_recommendation=by_recommendation,
        by_realized_action=by_realized_action,
        by_window=by_window,
        by_window_stage=by_window_stage,
        by_recommendation_and_stage=by_recommendation_and_stage,
        by_recommendation_and_window=by_recommendation_and_window,
    )
    learning_sections = build_learning_analytics_sections(follow_up_rows=follow_up_rows)

    return {
        'summary': {
            'total_follow_ups': len(follow_up_rows),
            'realized_count': sum(1 for row in follow_up_rows if row.status == 'realized'),
            'succeeded_count': sum(1 for row in follow_up_rows if row.outcome_status == 'succeeded'),
            'failed_count': sum(1 for row in follow_up_rows if row.outcome_status == 'failed'),
        },
        **recommendation_sections,
        **learning_sections,
        'score_guide': {
            'formula': 'historical_score = 0.4 * execution_rate + 0.6 * success_rate',
            'note': 'Score simples, transparente e nao probabilistico; serve como leitura operacional historica.',
        },
    }


__all__ = ['build_finance_follow_up_analytics']
