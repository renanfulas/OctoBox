"""
ARQUIVO: analytics historicos de performance e timing das recomendacoes financeiras.

POR QUE ELE EXISTE:
- tira de `analytics.py` a leitura de performance basica, janelas e matrizes de recomendacao.
"""

from .common import historical_score, safe_rate


def build_recommendation_analytics_sections(
    *,
    by_recommendation,
    by_realized_action,
    by_window,
    by_window_stage,
    by_recommendation_and_stage,
    by_recommendation_and_window,
):
    recommendations = []
    for recommended_action, rows in by_recommendation.items():
        suggested_count = len(rows)
        realized_count = sum(1 for row in rows if row.status == 'realized')
        succeeded_count = sum(1 for row in rows if row.outcome_status == 'succeeded')
        failed_count = sum(1 for row in rows if row.outcome_status == 'failed')
        recommendations.append(
            {
                'recommended_action': recommended_action,
                'suggested_count': suggested_count,
                'realized_count': realized_count,
                'succeeded_count': succeeded_count,
                'failed_count': failed_count,
                'execution_rate': safe_rate(realized_count, suggested_count),
                'success_rate': safe_rate(succeeded_count, realized_count),
                'failure_rate': safe_rate(failed_count, realized_count),
                'historical_score': historical_score(
                    execution_rate=safe_rate(realized_count, suggested_count),
                    success_rate=safe_rate(succeeded_count, realized_count),
                ),
            }
        )

    recommendations.sort(key=lambda item: (-item['success_rate'], -item['realized_count'], item['recommended_action']))

    realized_actions = []
    for action_kind, rows in by_realized_action.items():
        realized_actions.append(
            {
                'action_kind': action_kind,
                'executed_count': len(rows),
                'succeeded_count': sum(1 for row in rows if row.outcome_status == 'succeeded'),
                'failed_count': sum(1 for row in rows if row.outcome_status == 'failed'),
            }
        )
    realized_actions.sort(key=lambda item: (-item['executed_count'], item['action_kind']))

    weakest_recommendations = sorted(
        [item for item in recommendations if item['realized_count'] > 0],
        key=lambda item: (-item['failure_rate'], -item['failed_count'], item['recommended_action']),
    )

    window_performance = []
    for outcome_window, rows in by_window.items():
        realized_count = sum(1 for row in rows if row.status == 'realized')
        succeeded_count = sum(1 for row in rows if row.outcome_status == 'succeeded')
        failed_count = sum(1 for row in rows if row.outcome_status == 'failed')
        pending_count = sum(1 for row in rows if row.outcome_status == 'pending')
        window_performance.append(
            {
                'outcome_window': outcome_window,
                'realized_count': realized_count,
                'succeeded_count': succeeded_count,
                'failed_count': failed_count,
                'pending_count': pending_count,
                'success_rate': safe_rate(succeeded_count, realized_count),
            }
        )
    window_performance.sort(key=lambda item: (item['outcome_window'],))

    window_stage_performance = []
    for suggestion_window_stage, rows in by_window_stage.items():
        realized_count = sum(1 for row in rows if row.status == 'realized')
        succeeded_count = sum(1 for row in rows if row.outcome_status == 'succeeded')
        failed_count = sum(1 for row in rows if row.outcome_status == 'failed')
        labels = [row.suggestion_window_label for row in rows if row.suggestion_window_label]
        label = labels[0] if labels else 'Janela sem etiqueta'
        average_queue_assist_score = round(
            sum(float(row.suggestion_queue_assist_score or 0) for row in rows) / len(rows),
            1,
        ) if rows else 0.0
        window_stage_performance.append(
            {
                'suggestion_window_stage': suggestion_window_stage,
                'suggestion_window_label': label,
                'suggested_count': len(rows),
                'realized_count': realized_count,
                'succeeded_count': succeeded_count,
                'failed_count': failed_count,
                'success_rate': safe_rate(succeeded_count, realized_count),
                'average_queue_assist_score': average_queue_assist_score,
            }
        )
    window_stage_performance.sort(
        key=lambda item: (-item['success_rate'], -item['realized_count'], item['suggestion_window_stage'])
    )

    recommendation_timing_matrix = []
    for (recommended_action, suggestion_window_stage), rows in by_recommendation_and_stage.items():
        realized_count = sum(1 for row in rows if row.status == 'realized')
        if not realized_count:
            continue
        succeeded_count = sum(1 for row in rows if row.outcome_status == 'succeeded')
        failed_count = sum(1 for row in rows if row.outcome_status == 'failed')
        labels = [row.suggestion_window_label for row in rows if row.suggestion_window_label]
        label = labels[0] if labels else 'Janela sem etiqueta'
        recommendation_timing_matrix.append(
            {
                'recommended_action': recommended_action,
                'suggestion_window_stage': suggestion_window_stage,
                'suggestion_window_label': label,
                'realized_count': realized_count,
                'succeeded_count': succeeded_count,
                'failed_count': failed_count,
                'success_rate': safe_rate(succeeded_count, realized_count),
                'average_queue_assist_score': round(
                    sum(float(row.suggestion_queue_assist_score or 0) for row in rows) / len(rows),
                    1,
                ) if rows else 0.0,
            }
        )
    recommendation_timing_matrix.sort(
        key=lambda item: (-item['success_rate'], -item['realized_count'], item['recommended_action'], item['suggestion_window_stage'])
    )

    recommendation_window_matrix = []
    for (recommended_action, outcome_window), rows in by_recommendation_and_window.items():
        realized_count = sum(1 for row in rows if row.status == 'realized')
        if not realized_count:
            continue
        succeeded_count = sum(1 for row in rows if row.outcome_status == 'succeeded')
        failed_count = sum(1 for row in rows if row.outcome_status == 'failed')
        recommendation_window_matrix.append(
            {
                'recommended_action': recommended_action,
                'outcome_window': outcome_window,
                'realized_count': realized_count,
                'succeeded_count': succeeded_count,
                'failed_count': failed_count,
                'success_rate': safe_rate(succeeded_count, realized_count),
            }
        )
    recommendation_window_matrix.sort(
        key=lambda item: (-item['success_rate'], -item['realized_count'], item['recommended_action'], item['outcome_window'])
    )

    return {
        'recommendation_performance': recommendations,
        'realized_action_performance': realized_actions,
        'weakest_recommendations': weakest_recommendations[:5],
        'window_performance': window_performance,
        'window_stage_performance': window_stage_performance,
        'recommendation_timing_matrix': recommendation_timing_matrix,
        'recommendation_window_matrix': recommendation_window_matrix,
    }


__all__ = ['build_recommendation_analytics_sections']
