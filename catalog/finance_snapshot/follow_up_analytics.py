"""
ARQUIVO: leitura analitica comparativa de follow-ups financeiros.

POR QUE ELE EXISTE:
- transforma a trilha suggested -> realized -> outcome em comparativos pequenos para decisao e aprendizado.

O QUE ESTE ARQUIVO FAZ:
1. agrega recomendacoes por execucao e sucesso.
2. agrega acoes realizadas por frequencia.
3. destaca recomendacoes com pior desempenho.
4. compara janelas de outcome por taxa de sucesso.
5. compara em qual estagio da janela a recomendacao costuma funcionar melhor.
6. cruza recomendacao com estagio da janela para aprender a melhor acao em cada momento.
"""

from __future__ import annotations

from collections import defaultdict

from finance.models import FinanceFollowUp


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


def _safe_rate(numerator, denominator):
    if not denominator:
        return 0.0
    return round((numerator / denominator) * 100, 1)


def _historical_score(*, execution_rate, success_rate):
    return round((execution_rate * 0.4) + (success_rate * 0.6), 1)


def build_recommendation_historical_score_map(analytics):
    analytics = analytics or {}
    score_map = {}
    for item in analytics.get('recommendation_performance', []):
        score_map[item['recommended_action']] = item.get('historical_score', 0.0) or 0.0
    return score_map


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
        current_key = (current_gap, current.get('realized_count', 0) or 0, current.get('healthy_tension_rate', 0.0) or 0.0)
        if candidate_key > current_key:
            tension_map[context_key] = candidate
    return tension_map


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


def build_finance_follow_up_analytics(*, follow_ups):
    follow_up_rows = list(follow_ups)

    recommendations = []
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
                'execution_rate': _safe_rate(realized_count, suggested_count),
                'success_rate': _safe_rate(succeeded_count, realized_count),
                'failure_rate': _safe_rate(failed_count, realized_count),
                'historical_score': _historical_score(
                    execution_rate=_safe_rate(realized_count, suggested_count),
                    success_rate=_safe_rate(succeeded_count, realized_count),
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
                'success_rate': _safe_rate(succeeded_count, realized_count),
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
                'success_rate': _safe_rate(succeeded_count, realized_count),
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
                'success_rate': _safe_rate(succeeded_count, realized_count),
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
                'success_rate': _safe_rate(succeeded_count, realized_count),
            }
        )
    recommendation_window_matrix.sort(
        key=lambda item: (-item['success_rate'], -item['realized_count'], item['recommended_action'], item['outcome_window'])
    )

    turn_recommendation_adherence = {
        'tracked_realized_count': 0,
        'aligned_count': 0,
        'divergent_count': 0,
        'adherence_rate': 0.0,
    }
    turn_recommendation_outcome = {
        'aligned': {
            'realized_count': 0,
            'succeeded_count': 0,
            'failed_count': 0,
            'success_rate': 0.0,
        },
        'divergent': {
            'realized_count': 0,
            'succeeded_count': 0,
            'failed_count': 0,
            'success_rate': 0.0,
        },
    }
    turn_recommendation_learning = {
        'smart_divergence': {
            'realized_count': 0,
            'success_rate': 0.0,
            'headline': 'Quando divergir valeu a pena',
            'summary': 'Ainda sem casos suficientes para provar divergencia inteligente.',
        },
        'bad_divergence': {
            'realized_count': 0,
            'failure_rate': 0.0,
            'headline': 'Quando divergir piorou o resultado',
            'summary': 'Ainda sem casos suficientes para provar desvio ruim.',
        },
    }
    turn_priority_outcome = {
        'aligned': {
            'realized_count': 0,
            'succeeded_count': 0,
            'failed_count': 0,
            'success_rate': 0.0,
        },
        'tension': {
            'realized_count': 0,
            'succeeded_count': 0,
            'failed_count': 0,
            'success_rate': 0.0,
        },
    }
    turn_priority_learning = {
        'healthy_tension': {
            'headline': 'Quando a tensao valeu a pena',
            'realized_count': 0,
            'success_rate': 0.0,
            'summary': 'Ainda sem casos suficientes para provar tensao saudavel.',
        },
        'dangerous_tension': {
            'headline': 'Quando a tensao virou dispersao',
            'realized_count': 0,
            'failure_rate': 0.0,
            'summary': 'Ainda sem casos suficientes para provar tensao perigosa.',
        },
    }
    turn_priority_tension_timing_matrix = []
    turn_priority_tension_signal_bucket_matrix = []
    turn_priority_tension_compound_matrix = []
    divergence_timing_matrix = []
    divergence_action_matrix = []
    divergence_signal_bucket_matrix = []
    divergence_compound_matrix = []
    compound_divergent_action_matrix = []
    divergence_by_stage = defaultdict(
        lambda: {
            'label': 'Janela sem etiqueta',
            'divergent_realized_count': 0,
            'smart_divergence_count': 0,
            'bad_divergence_count': 0,
        }
    )
    divergence_by_recommended_action = defaultdict(
        lambda: {
            'divergent_realized_count': 0,
            'smart_divergence_count': 0,
            'bad_divergence_count': 0,
        }
    )
    divergence_by_signal_bucket = defaultdict(
        lambda: {
            'divergent_realized_count': 0,
            'smart_divergence_count': 0,
            'bad_divergence_count': 0,
        }
    )
    divergence_by_compound_context = defaultdict(
        lambda: {
            'timing_label': 'Janela sem etiqueta',
            'divergent_realized_count': 0,
            'smart_divergence_count': 0,
            'bad_divergence_count': 0,
        }
    )
    compound_divergent_actions = defaultdict(
        lambda: {
            'timing_label': 'Janela sem etiqueta',
            'realized_count': 0,
            'succeeded_count': 0,
            'failed_count': 0,
        }
    )
    tension_by_stage = defaultdict(
        lambda: {
            'label': 'Janela sem etiqueta',
            'realized_count': 0,
            'succeeded_count': 0,
            'failed_count': 0,
        }
    )
    tension_by_signal_bucket = defaultdict(
        lambda: {
            'realized_count': 0,
            'succeeded_count': 0,
            'failed_count': 0,
        }
    )
    tension_by_compound_context = defaultdict(
        lambda: {
            'timing_label': 'Janela sem etiqueta',
            'realized_count': 0,
            'succeeded_count': 0,
            'failed_count': 0,
        }
    )
    for follow_up in follow_up_rows:
        if follow_up.status != 'realized' or not follow_up.realized_action_kind:
            continue
        payload = follow_up.payload or {}
        turn_recommendation = payload.get('turn_recommendation') or {}
        turn_priority = payload.get('turn_priority') or {}
        recommended_action_kind = turn_recommendation.get('action_kind', '')
        if not recommended_action_kind:
            continue
        alignment_status = turn_priority.get('alignment_status') or 'unknown'
        signal_bucket = payload.get('signal_bucket') or 'unknown'
        suggestion_window_stage = follow_up.suggestion_window_stage or 'unknown'
        divergence_stage_bucket = divergence_by_stage[suggestion_window_stage]
        if follow_up.suggestion_window_label:
            divergence_stage_bucket['label'] = follow_up.suggestion_window_label
        recommended_action = follow_up.recommended_action or ''
        divergence_action_bucket = divergence_by_recommended_action[recommended_action]
        divergence_signal_bucket_bucket = divergence_by_signal_bucket[signal_bucket]
        compound_key = (recommended_action, suggestion_window_stage, signal_bucket)
        divergence_compound_bucket = divergence_by_compound_context[compound_key]
        if follow_up.suggestion_window_label:
            divergence_compound_bucket['timing_label'] = follow_up.suggestion_window_label
        compound_action_key = (
            recommended_action,
            suggestion_window_stage,
            signal_bucket,
            follow_up.realized_action_kind,
        )
        compound_action_bucket = compound_divergent_actions[compound_action_key]
        if follow_up.suggestion_window_label:
            compound_action_bucket['timing_label'] = follow_up.suggestion_window_label
        turn_recommendation_adherence['tracked_realized_count'] += 1
        if follow_up.realized_action_kind == recommended_action_kind:
            turn_recommendation_adherence['aligned_count'] += 1
            outcome_bucket = turn_recommendation_outcome['aligned']
        else:
            turn_recommendation_adherence['divergent_count'] += 1
            outcome_bucket = turn_recommendation_outcome['divergent']
            divergence_stage_bucket['divergent_realized_count'] += 1
            divergence_action_bucket['divergent_realized_count'] += 1
            divergence_signal_bucket_bucket['divergent_realized_count'] += 1
            divergence_compound_bucket['divergent_realized_count'] += 1
            compound_action_bucket['realized_count'] += 1
        outcome_bucket['realized_count'] += 1
        if follow_up.outcome_status == 'succeeded':
            outcome_bucket['succeeded_count'] += 1
            if follow_up.realized_action_kind != recommended_action_kind:
                divergence_stage_bucket['smart_divergence_count'] += 1
                divergence_action_bucket['smart_divergence_count'] += 1
                divergence_signal_bucket_bucket['smart_divergence_count'] += 1
                divergence_compound_bucket['smart_divergence_count'] += 1
                compound_action_bucket['succeeded_count'] += 1
        elif follow_up.outcome_status == 'failed':
            outcome_bucket['failed_count'] += 1
            if follow_up.realized_action_kind != recommended_action_kind:
                divergence_stage_bucket['bad_divergence_count'] += 1
                divergence_action_bucket['bad_divergence_count'] += 1
                divergence_signal_bucket_bucket['bad_divergence_count'] += 1
                divergence_compound_bucket['bad_divergence_count'] += 1
                compound_action_bucket['failed_count'] += 1
        if alignment_status in turn_priority_outcome:
            priority_bucket = turn_priority_outcome[alignment_status]
            priority_bucket['realized_count'] += 1
            if follow_up.outcome_status == 'succeeded':
                priority_bucket['succeeded_count'] += 1
            elif follow_up.outcome_status == 'failed':
                priority_bucket['failed_count'] += 1
        if alignment_status == 'tension':
            tension_stage_bucket = tension_by_stage[suggestion_window_stage]
            if follow_up.suggestion_window_label:
                tension_stage_bucket['label'] = follow_up.suggestion_window_label
            tension_signal_bucket = tension_by_signal_bucket[signal_bucket]
            tension_compound_bucket = tension_by_compound_context[(suggestion_window_stage, signal_bucket)]
            if follow_up.suggestion_window_label:
                tension_compound_bucket['timing_label'] = follow_up.suggestion_window_label
            tension_stage_bucket['realized_count'] += 1
            tension_signal_bucket['realized_count'] += 1
            tension_compound_bucket['realized_count'] += 1
            if follow_up.outcome_status == 'succeeded':
                tension_stage_bucket['succeeded_count'] += 1
                tension_signal_bucket['succeeded_count'] += 1
                tension_compound_bucket['succeeded_count'] += 1
            elif follow_up.outcome_status == 'failed':
                tension_stage_bucket['failed_count'] += 1
                tension_signal_bucket['failed_count'] += 1
                tension_compound_bucket['failed_count'] += 1
    turn_recommendation_adherence['adherence_rate'] = _safe_rate(
        turn_recommendation_adherence['aligned_count'],
        turn_recommendation_adherence['tracked_realized_count'],
    )
    for bucket in turn_recommendation_outcome.values():
        bucket['success_rate'] = _safe_rate(bucket['succeeded_count'], bucket['realized_count'])
    for bucket in turn_priority_outcome.values():
        bucket['success_rate'] = _safe_rate(bucket['succeeded_count'], bucket['realized_count'])
    smart_divergence = turn_recommendation_learning['smart_divergence']
    bad_divergence = turn_recommendation_learning['bad_divergence']
    smart_divergence['realized_count'] = turn_recommendation_outcome['divergent']['succeeded_count']
    smart_divergence['success_rate'] = _safe_rate(
        turn_recommendation_outcome['divergent']['succeeded_count'],
        turn_recommendation_outcome['divergent']['realized_count'],
    )
    if smart_divergence['realized_count']:
        smart_divergence['summary'] = (
            f"{smart_divergence['realized_count']} divergencia(s) terminaram em sucesso, "
            "sinalizando que o time saiu da trilha e mesmo assim acertou a mao."
        )
    bad_divergence['realized_count'] = turn_recommendation_outcome['divergent']['failed_count']
    bad_divergence['failure_rate'] = _safe_rate(
        turn_recommendation_outcome['divergent']['failed_count'],
        turn_recommendation_outcome['divergent']['realized_count'],
    )
    if bad_divergence['realized_count']:
        bad_divergence['summary'] = (
            f"{bad_divergence['realized_count']} divergencia(s) terminaram em falha, "
            "sinalizando desvio que tirou a operacao da melhor linha."
        )
    healthy_tension = turn_priority_learning['healthy_tension']
    dangerous_tension = turn_priority_learning['dangerous_tension']
    healthy_tension['realized_count'] = turn_priority_outcome['tension']['succeeded_count']
    healthy_tension['success_rate'] = _safe_rate(
        turn_priority_outcome['tension']['succeeded_count'],
        turn_priority_outcome['tension']['realized_count'],
    )
    if healthy_tension['realized_count']:
        healthy_tension['summary'] = (
            f"{healthy_tension['realized_count']} caso(s) em tensao terminaram em sucesso, "
            "sinalizando adaptacao humana que leu melhor o campo."
        )
    dangerous_tension['realized_count'] = turn_priority_outcome['tension']['failed_count']
    dangerous_tension['failure_rate'] = _safe_rate(
        turn_priority_outcome['tension']['failed_count'],
        turn_priority_outcome['tension']['realized_count'],
    )
    if dangerous_tension['realized_count']:
        dangerous_tension['summary'] = (
            f"{dangerous_tension['realized_count']} caso(s) em tensao terminaram em falha, "
            "sinalizando conflito operacional que dispersou a execucao."
        )
    for stage, data in tension_by_stage.items():
        if not data['realized_count']:
            continue
        turn_priority_tension_timing_matrix.append(
            {
                'suggestion_window_stage': stage,
                'suggestion_window_label': data['label'],
                'realized_count': data['realized_count'],
                'healthy_tension_count': data['succeeded_count'],
                'dangerous_tension_count': data['failed_count'],
                'healthy_tension_rate': _safe_rate(data['succeeded_count'], data['realized_count']),
                'dangerous_tension_rate': _safe_rate(data['failed_count'], data['realized_count']),
            }
        )
    turn_priority_tension_timing_matrix.sort(
        key=lambda item: (
            -(item['healthy_tension_rate'] or 0.0),
            item['dangerous_tension_rate'] or 0.0,
            -(item['realized_count'] or 0),
            item['suggestion_window_stage'],
        )
    )
    for signal_bucket, data in tension_by_signal_bucket.items():
        if not data['realized_count']:
            continue
        turn_priority_tension_signal_bucket_matrix.append(
            {
                'signal_bucket': signal_bucket,
                'realized_count': data['realized_count'],
                'healthy_tension_count': data['succeeded_count'],
                'dangerous_tension_count': data['failed_count'],
                'healthy_tension_rate': _safe_rate(data['succeeded_count'], data['realized_count']),
                'dangerous_tension_rate': _safe_rate(data['failed_count'], data['realized_count']),
            }
        )
    turn_priority_tension_signal_bucket_matrix.sort(
        key=lambda item: (
            -(item['healthy_tension_rate'] or 0.0),
            item['dangerous_tension_rate'] or 0.0,
            -(item['realized_count'] or 0),
            item['signal_bucket'],
        )
    )
    for (suggestion_window_stage, signal_bucket), data in tension_by_compound_context.items():
        if not data['realized_count']:
            continue
        turn_priority_tension_compound_matrix.append(
            {
                'suggestion_window_stage': suggestion_window_stage,
                'suggestion_window_label': data['timing_label'],
                'signal_bucket': signal_bucket,
                'realized_count': data['realized_count'],
                'healthy_tension_count': data['succeeded_count'],
                'dangerous_tension_count': data['failed_count'],
                'healthy_tension_rate': _safe_rate(data['succeeded_count'], data['realized_count']),
                'dangerous_tension_rate': _safe_rate(data['failed_count'], data['realized_count']),
            }
        )
    turn_priority_tension_compound_matrix.sort(
        key=lambda item: (
            -(item['healthy_tension_rate'] or 0.0),
            item['dangerous_tension_rate'] or 0.0,
            -(item['realized_count'] or 0),
            item['suggestion_window_stage'],
            item['signal_bucket'],
        )
    )
    for stage, data in divergence_by_stage.items():
        if not data['divergent_realized_count']:
            continue
        divergence_timing_matrix.append(
            {
                'suggestion_window_stage': stage,
                'suggestion_window_label': data['label'],
                'divergent_realized_count': data['divergent_realized_count'],
                'smart_divergence_count': data['smart_divergence_count'],
                'bad_divergence_count': data['bad_divergence_count'],
                'smart_divergence_rate': _safe_rate(
                    data['smart_divergence_count'],
                    data['divergent_realized_count'],
                ),
                'bad_divergence_rate': _safe_rate(
                    data['bad_divergence_count'],
                    data['divergent_realized_count'],
                ),
            }
        )
    divergence_timing_matrix.sort(
        key=lambda item: (
            -(item['smart_divergence_rate'] or 0.0),
            item['bad_divergence_rate'] or 0.0,
            -(item['divergent_realized_count'] or 0),
            item['suggestion_window_stage'],
        )
    )
    for recommended_action, data in divergence_by_recommended_action.items():
        if not data['divergent_realized_count']:
            continue
        divergence_action_matrix.append(
            {
                'recommended_action': recommended_action,
                'divergent_realized_count': data['divergent_realized_count'],
                'smart_divergence_count': data['smart_divergence_count'],
                'bad_divergence_count': data['bad_divergence_count'],
                'smart_divergence_rate': _safe_rate(
                    data['smart_divergence_count'],
                    data['divergent_realized_count'],
                ),
                'bad_divergence_rate': _safe_rate(
                    data['bad_divergence_count'],
                    data['divergent_realized_count'],
                ),
            }
        )
    divergence_action_matrix.sort(
        key=lambda item: (
            -(item['smart_divergence_rate'] or 0.0),
            item['bad_divergence_rate'] or 0.0,
            -(item['divergent_realized_count'] or 0),
            item['recommended_action'],
        )
    )
    for signal_bucket, data in divergence_by_signal_bucket.items():
        if not data['divergent_realized_count']:
            continue
        divergence_signal_bucket_matrix.append(
            {
                'signal_bucket': signal_bucket,
                'divergent_realized_count': data['divergent_realized_count'],
                'smart_divergence_count': data['smart_divergence_count'],
                'bad_divergence_count': data['bad_divergence_count'],
                'smart_divergence_rate': _safe_rate(
                    data['smart_divergence_count'],
                    data['divergent_realized_count'],
                ),
                'bad_divergence_rate': _safe_rate(
                    data['bad_divergence_count'],
                    data['divergent_realized_count'],
                ),
            }
        )
    divergence_signal_bucket_matrix.sort(
        key=lambda item: (
            -(item['smart_divergence_rate'] or 0.0),
            item['bad_divergence_rate'] or 0.0,
            -(item['divergent_realized_count'] or 0),
            item['signal_bucket'],
        )
    )
    for (recommended_action, suggestion_window_stage, signal_bucket), data in divergence_by_compound_context.items():
        if not data['divergent_realized_count']:
            continue
        divergence_compound_matrix.append(
            {
                'recommended_action': recommended_action,
                'suggestion_window_stage': suggestion_window_stage,
                'suggestion_window_label': data['timing_label'],
                'signal_bucket': signal_bucket,
                'divergent_realized_count': data['divergent_realized_count'],
                'smart_divergence_count': data['smart_divergence_count'],
                'bad_divergence_count': data['bad_divergence_count'],
                'smart_divergence_rate': _safe_rate(
                    data['smart_divergence_count'],
                    data['divergent_realized_count'],
                ),
                'bad_divergence_rate': _safe_rate(
                    data['bad_divergence_count'],
                    data['divergent_realized_count'],
                ),
            }
        )
    divergence_compound_matrix.sort(
        key=lambda item: (
            -(item['smart_divergence_rate'] or 0.0),
            item['bad_divergence_rate'] or 0.0,
            -(item['divergent_realized_count'] or 0),
            item['recommended_action'],
            item['suggestion_window_stage'],
            item['signal_bucket'],
        )
    )
    for (recommended_action, suggestion_window_stage, signal_bucket, realized_action_kind), data in compound_divergent_actions.items():
        if not data['realized_count']:
            continue
        compound_divergent_action_matrix.append(
            {
                'recommended_action': recommended_action,
                'suggestion_window_stage': suggestion_window_stage,
                'suggestion_window_label': data['timing_label'],
                'signal_bucket': signal_bucket,
                'realized_action_kind': realized_action_kind,
                'realized_count': data['realized_count'],
                'succeeded_count': data['succeeded_count'],
                'failed_count': data['failed_count'],
                'success_rate': _safe_rate(data['succeeded_count'], data['realized_count']),
            }
        )
    compound_divergent_action_matrix.sort(
        key=lambda item: (
            -(item['success_rate'] or 0.0),
            -(item['realized_count'] or 0),
            item['recommended_action'],
            item['suggestion_window_stage'],
            item['signal_bucket'],
            item['realized_action_kind'],
        )
    )

    return {
        'summary': {
            'total_follow_ups': len(follow_up_rows),
            'realized_count': sum(1 for row in follow_up_rows if row.status == 'realized'),
            'succeeded_count': sum(1 for row in follow_up_rows if row.outcome_status == 'succeeded'),
            'failed_count': sum(1 for row in follow_up_rows if row.outcome_status == 'failed'),
        },
        'recommendation_performance': recommendations,
        'realized_action_performance': realized_actions,
        'weakest_recommendations': weakest_recommendations[:5],
        'window_performance': window_performance,
        'window_stage_performance': window_stage_performance,
        'recommendation_timing_matrix': recommendation_timing_matrix,
        'recommendation_window_matrix': recommendation_window_matrix,
        'turn_recommendation_adherence': turn_recommendation_adherence,
        'turn_recommendation_outcome': turn_recommendation_outcome,
        'turn_recommendation_learning': turn_recommendation_learning,
        'turn_priority_outcome': turn_priority_outcome,
        'turn_priority_learning': turn_priority_learning,
        'turn_priority_tension_timing_matrix': turn_priority_tension_timing_matrix,
        'turn_priority_tension_signal_bucket_matrix': turn_priority_tension_signal_bucket_matrix,
        'turn_priority_tension_compound_matrix': turn_priority_tension_compound_matrix,
        'divergence_timing_matrix': divergence_timing_matrix,
        'divergence_action_matrix': divergence_action_matrix,
        'divergence_signal_bucket_matrix': divergence_signal_bucket_matrix,
        'divergence_compound_matrix': divergence_compound_matrix,
        'compound_divergent_action_matrix': compound_divergent_action_matrix,
        'score_guide': {
            'formula': 'historical_score = 0.4 * execution_rate + 0.6 * success_rate',
            'note': 'Score simples, transparente e nao probabilistico; serve como leitura operacional historica.',
        },
    }


__all__ = [
    'build_best_prediction_window_by_action_map',
    'build_best_action_by_timing_map',
    'build_contextual_recommendation_map',
    'build_finance_follow_up_analytics',
    'build_recommendation_timing_lookup_map',
    'build_recommendation_historical_score_map',
    'build_turn_priority_tension_context_map',
    'build_turn_recommendation',
    'build_timing_recommendation_override_map',
]
