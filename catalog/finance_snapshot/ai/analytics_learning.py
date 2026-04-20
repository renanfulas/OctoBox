"""
ARQUIVO: analytics historicos de divergencia e tensao da IA financeira.

POR QUE ELE EXISTE:
- tira de `analytics.py` o laboratorio de aprendizado contextual e matrizes compostas.
"""

from __future__ import annotations

from collections import defaultdict

from .common import safe_rate


def build_learning_analytics_sections(*, follow_up_rows):
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

    turn_recommendation_adherence['adherence_rate'] = safe_rate(
        turn_recommendation_adherence['aligned_count'],
        turn_recommendation_adherence['tracked_realized_count'],
    )
    for bucket in turn_recommendation_outcome.values():
        bucket['success_rate'] = safe_rate(bucket['succeeded_count'], bucket['realized_count'])
    for bucket in turn_priority_outcome.values():
        bucket['success_rate'] = safe_rate(bucket['succeeded_count'], bucket['realized_count'])

    smart_divergence = turn_recommendation_learning['smart_divergence']
    bad_divergence = turn_recommendation_learning['bad_divergence']
    smart_divergence['realized_count'] = turn_recommendation_outcome['divergent']['succeeded_count']
    smart_divergence['success_rate'] = safe_rate(
        turn_recommendation_outcome['divergent']['succeeded_count'],
        turn_recommendation_outcome['divergent']['realized_count'],
    )
    if smart_divergence['realized_count']:
        smart_divergence['summary'] = (
            f"{smart_divergence['realized_count']} divergencia(s) terminaram em sucesso, "
            "sinalizando que o time saiu da trilha e mesmo assim acertou a mao."
        )
    bad_divergence['realized_count'] = turn_recommendation_outcome['divergent']['failed_count']
    bad_divergence['failure_rate'] = safe_rate(
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
    healthy_tension['success_rate'] = safe_rate(
        turn_priority_outcome['tension']['succeeded_count'],
        turn_priority_outcome['tension']['realized_count'],
    )
    if healthy_tension['realized_count']:
        healthy_tension['summary'] = (
            f"{healthy_tension['realized_count']} caso(s) em tensao terminaram em sucesso, "
            "sinalizando adaptacao humana que leu melhor o campo."
        )
    dangerous_tension['realized_count'] = turn_priority_outcome['tension']['failed_count']
    dangerous_tension['failure_rate'] = safe_rate(
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
                'healthy_tension_rate': safe_rate(data['succeeded_count'], data['realized_count']),
                'dangerous_tension_rate': safe_rate(data['failed_count'], data['realized_count']),
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
                'healthy_tension_rate': safe_rate(data['succeeded_count'], data['realized_count']),
                'dangerous_tension_rate': safe_rate(data['failed_count'], data['realized_count']),
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
                'healthy_tension_rate': safe_rate(data['succeeded_count'], data['realized_count']),
                'dangerous_tension_rate': safe_rate(data['failed_count'], data['realized_count']),
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
                'smart_divergence_rate': safe_rate(
                    data['smart_divergence_count'],
                    data['divergent_realized_count'],
                ),
                'bad_divergence_rate': safe_rate(
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
                'smart_divergence_rate': safe_rate(
                    data['smart_divergence_count'],
                    data['divergent_realized_count'],
                ),
                'bad_divergence_rate': safe_rate(
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
                'smart_divergence_rate': safe_rate(
                    data['smart_divergence_count'],
                    data['divergent_realized_count'],
                ),
                'bad_divergence_rate': safe_rate(
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
                'smart_divergence_rate': safe_rate(
                    data['smart_divergence_count'],
                    data['divergent_realized_count'],
                ),
                'bad_divergence_rate': safe_rate(
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
                'success_rate': safe_rate(data['succeeded_count'], data['realized_count']),
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
    }


__all__ = ['build_learning_analytics_sections']
