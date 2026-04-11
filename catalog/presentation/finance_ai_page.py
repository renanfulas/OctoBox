"""
ARQUIVO: presenter da camada assistida por IA da central financeira.

POR QUE ELE EXISTE:
- separa analytics historico, leitura assistida e traducao de score da fachada principal.
"""

from ..finance_snapshot.ai import build_turn_recommendation


def build_follow_up_analytics_board(analytics):
    analytics = analytics or {}
    action_map = {
        'review_winback': 'Revisar winback',
        'monitor_recent_reactivation': 'Acompanhar reativacao',
        'escalate_manual_retention': 'Escalar retencao manual',
        'send_financial_followup': 'Enviar follow-up financeiro',
        'monitor_and_nudge': 'Monitorar e lembrar',
        'observe_payment_resolution': 'Observar regularizacao',
        'maintain_relationship': 'Manter relacionamento',
        'overdue': 'WhatsApp de cobranca',
        'reactivation': 'WhatsApp de reativacao',
    }
    signal_bucket_map = {
        'already_inactive': 'Ja inativo',
        'high_signal': 'Alto risco',
        'watch': 'Observacao',
        'recovered': 'Recuperado',
        'stable': 'Estavel',
        'unknown': 'Sem classificacao',
    }
    recommendation_performance = []
    for item in analytics.get('recommendation_performance', [])[:4]:
        recommendation_performance.append(
            {
                'label': action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' ')),
                'historical_score': item['historical_score'],
                'success_rate': item['success_rate'],
                'execution_rate': item['execution_rate'],
                'sample': item['realized_count'],
            }
        )

    realized_actions = []
    for item in analytics.get('realized_action_performance', [])[:3]:
        realized_actions.append(
            {
                'label': action_map.get(item['action_kind'], item['action_kind']),
                'executed_count': item['executed_count'],
                'succeeded_count': item['succeeded_count'],
            }
        )

    weakest = []
    for item in analytics.get('weakest_recommendations', [])[:3]:
        weakest.append(
            {
                'label': action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' ')),
                'failure_rate': item['failure_rate'],
                'failed_count': item['failed_count'],
            }
        )

    windows = list(analytics.get('window_performance', [])[:3])
    timing = list(analytics.get('window_stage_performance', [])[:3])
    recommendation_timing = []
    for item in analytics.get('recommendation_timing_matrix', [])[:4]:
        recommendation_timing.append(
            {
                'action_label': action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' ')),
                'timing_label': item['suggestion_window_label'],
                'success_rate': item['success_rate'],
                'realized_count': item['realized_count'],
                'average_queue_assist_score': item['average_queue_assist_score'],
            }
        )
    recommendation_window = []
    for item in analytics.get('recommendation_window_matrix', [])[:4]:
        recommendation_window.append(
            {
                'action_label': action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' ')),
                'outcome_window': item['outcome_window'],
                'success_rate': item['success_rate'],
                'realized_count': item['realized_count'],
            }
        )
    divergence_timing = []
    for item in analytics.get('divergence_timing_matrix', [])[:4]:
        divergence_timing.append(
            {
                'timing_label': item['suggestion_window_label'],
                'divergent_realized_count': item['divergent_realized_count'],
                'smart_divergence_count': item['smart_divergence_count'],
                'bad_divergence_count': item['bad_divergence_count'],
                'smart_divergence_rate': item['smart_divergence_rate'],
                'bad_divergence_rate': item['bad_divergence_rate'],
            }
        )
    divergence_action = []
    for item in analytics.get('divergence_action_matrix', [])[:4]:
        divergence_action.append(
            {
                'action_label': action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' ')),
                'divergent_realized_count': item['divergent_realized_count'],
                'smart_divergence_count': item['smart_divergence_count'],
                'bad_divergence_count': item['bad_divergence_count'],
                'smart_divergence_rate': item['smart_divergence_rate'],
                'bad_divergence_rate': item['bad_divergence_rate'],
            }
        )
    divergence_signal_bucket = []
    for item in analytics.get('divergence_signal_bucket_matrix', [])[:4]:
        divergence_signal_bucket.append(
            {
                'signal_bucket_label': signal_bucket_map.get(item['signal_bucket'], item['signal_bucket']),
                'divergent_realized_count': item['divergent_realized_count'],
                'smart_divergence_count': item['smart_divergence_count'],
                'bad_divergence_count': item['bad_divergence_count'],
                'smart_divergence_rate': item['smart_divergence_rate'],
                'bad_divergence_rate': item['bad_divergence_rate'],
            }
        )
    turn_priority_tension_timing = []
    for item in analytics.get('turn_priority_tension_timing_matrix', [])[:4]:
        turn_priority_tension_timing.append(
            {
                'timing_label': item['suggestion_window_label'],
                'realized_count': item['realized_count'],
                'healthy_tension_count': item['healthy_tension_count'],
                'dangerous_tension_count': item['dangerous_tension_count'],
                'healthy_tension_rate': item['healthy_tension_rate'],
                'dangerous_tension_rate': item['dangerous_tension_rate'],
            }
        )
    turn_priority_tension_signal_bucket = []
    for item in analytics.get('turn_priority_tension_signal_bucket_matrix', [])[:4]:
        turn_priority_tension_signal_bucket.append(
            {
                'signal_bucket_label': signal_bucket_map.get(item['signal_bucket'], item['signal_bucket']),
                'realized_count': item['realized_count'],
                'healthy_tension_count': item['healthy_tension_count'],
                'dangerous_tension_count': item['dangerous_tension_count'],
                'healthy_tension_rate': item['healthy_tension_rate'],
                'dangerous_tension_rate': item['dangerous_tension_rate'],
            }
        )
    turn_priority_tension_compound = []
    for item in analytics.get('turn_priority_tension_compound_matrix', [])[:4]:
        turn_priority_tension_compound.append(
            {
                'timing_label': item['suggestion_window_label'],
                'signal_bucket_label': signal_bucket_map.get(item['signal_bucket'], item['signal_bucket']),
                'realized_count': item['realized_count'],
                'healthy_tension_rate': item['healthy_tension_rate'],
                'dangerous_tension_rate': item['dangerous_tension_rate'],
            }
        )
    divergence_compound = []
    for item in analytics.get('divergence_compound_matrix', [])[:4]:
        divergence_compound.append(
            {
                'action_label': action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' ')),
                'timing_label': item['suggestion_window_label'],
                'signal_bucket_label': signal_bucket_map.get(item['signal_bucket'], item['signal_bucket']),
                'divergent_realized_count': item['divergent_realized_count'],
                'smart_divergence_rate': item['smart_divergence_rate'],
                'bad_divergence_rate': item['bad_divergence_rate'],
            }
        )
    best_play = build_turn_recommendation(analytics)
    if best_play.get('recommended_action'):
        action_label = action_map.get(best_play['recommended_action'], best_play['recommended_action'].replace('_', ' '))
        best_play['action_label'] = action_label
        best_play['summary'] = (
            f"{action_label} esta liderando no historico ativo dentro da janela {best_play.get('outcome_window', '')}, "
            f"com {best_play.get('success_rate', 0.0)}% de sucesso em {best_play.get('realized_count', 0)} realizado(s)."
        )
    adherence = analytics.get('turn_recommendation_adherence', {}) or {}
    turn_outcome = analytics.get('turn_recommendation_outcome', {}) or {}
    turn_learning = analytics.get('turn_recommendation_learning', {}) or {}
    turn_priority_outcome = analytics.get('turn_priority_outcome', {}) or {}
    turn_priority_learning = analytics.get('turn_priority_learning', {}) or {}

    return {
        'summary': analytics.get('summary', {}),
        'best_play': best_play,
        'turn_recommendation_adherence': adherence,
        'turn_recommendation_outcome': {
            'aligned': {
                'label': 'Seguiu o turno',
                'realized_count': (turn_outcome.get('aligned') or {}).get('realized_count', 0),
                'succeeded_count': (turn_outcome.get('aligned') or {}).get('succeeded_count', 0),
                'failed_count': (turn_outcome.get('aligned') or {}).get('failed_count', 0),
                'success_rate': (turn_outcome.get('aligned') or {}).get('success_rate', 0.0),
            },
            'divergent': {
                'label': 'Divergiu do turno',
                'realized_count': (turn_outcome.get('divergent') or {}).get('realized_count', 0),
                'succeeded_count': (turn_outcome.get('divergent') or {}).get('succeeded_count', 0),
                'failed_count': (turn_outcome.get('divergent') or {}).get('failed_count', 0),
                'success_rate': (turn_outcome.get('divergent') or {}).get('success_rate', 0.0),
            },
        },
        'turn_recommendation_learning': {
            'smart_divergence': {
                'headline': (turn_learning.get('smart_divergence') or {}).get('headline', 'Quando divergir valeu a pena'),
                'realized_count': (turn_learning.get('smart_divergence') or {}).get('realized_count', 0),
                'success_rate': (turn_learning.get('smart_divergence') or {}).get('success_rate', 0.0),
                'summary': (turn_learning.get('smart_divergence') or {}).get(
                    'summary',
                    'Ainda sem casos suficientes para provar divergencia inteligente.',
                ),
            },
            'bad_divergence': {
                'headline': (turn_learning.get('bad_divergence') or {}).get(
                    'headline',
                    'Quando divergir piorou o resultado',
                ),
                'realized_count': (turn_learning.get('bad_divergence') or {}).get('realized_count', 0),
                'failure_rate': (turn_learning.get('bad_divergence') or {}).get('failure_rate', 0.0),
                'summary': (turn_learning.get('bad_divergence') or {}).get(
                    'summary',
                    'Ainda sem casos suficientes para provar desvio ruim.',
                ),
            },
        },
        'turn_priority_outcome': {
            'aligned': {
                'label': 'Turno alinhado',
                'realized_count': (turn_priority_outcome.get('aligned') or {}).get('realized_count', 0),
                'succeeded_count': (turn_priority_outcome.get('aligned') or {}).get('succeeded_count', 0),
                'failed_count': (turn_priority_outcome.get('aligned') or {}).get('failed_count', 0),
                'success_rate': (turn_priority_outcome.get('aligned') or {}).get('success_rate', 0.0),
            },
            'tension': {
                'label': 'Turno em tensao',
                'realized_count': (turn_priority_outcome.get('tension') or {}).get('realized_count', 0),
                'succeeded_count': (turn_priority_outcome.get('tension') or {}).get('succeeded_count', 0),
                'failed_count': (turn_priority_outcome.get('tension') or {}).get('failed_count', 0),
                'success_rate': (turn_priority_outcome.get('tension') or {}).get('success_rate', 0.0),
            },
        },
        'turn_priority_learning': {
            'healthy_tension': {
                'headline': (turn_priority_learning.get('healthy_tension') or {}).get(
                    'headline',
                    'Quando a tensao valeu a pena',
                ),
                'realized_count': (turn_priority_learning.get('healthy_tension') or {}).get('realized_count', 0),
                'success_rate': (turn_priority_learning.get('healthy_tension') or {}).get('success_rate', 0.0),
                'summary': (turn_priority_learning.get('healthy_tension') or {}).get(
                    'summary',
                    'Ainda sem casos suficientes para provar tensao saudavel.',
                ),
            },
            'dangerous_tension': {
                'headline': (turn_priority_learning.get('dangerous_tension') or {}).get(
                    'headline',
                    'Quando a tensao virou dispersao',
                ),
                'realized_count': (turn_priority_learning.get('dangerous_tension') or {}).get('realized_count', 0),
                'failure_rate': (turn_priority_learning.get('dangerous_tension') or {}).get('failure_rate', 0.0),
                'summary': (turn_priority_learning.get('dangerous_tension') or {}).get(
                    'summary',
                    'Ainda sem casos suficientes para provar tensao perigosa.',
                ),
            },
        },
        'turn_priority_tension_timing': turn_priority_tension_timing,
        'turn_priority_tension_signal_bucket': turn_priority_tension_signal_bucket,
        'turn_priority_tension_compound': turn_priority_tension_compound,
        'recommendations': recommendation_performance,
        'realized_actions': realized_actions,
        'weakest': weakest,
        'windows': windows,
        'timing': timing,
        'recommendation_timing': recommendation_timing,
        'recommendation_window': recommendation_window,
        'divergence_timing': divergence_timing,
        'divergence_action': divergence_action,
        'divergence_signal_bucket': divergence_signal_bucket,
        'divergence_compound': divergence_compound,
        'score_guide': analytics.get('score_guide', {}),
    }


__all__ = ['build_follow_up_analytics_board']
