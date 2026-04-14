"""
ARQUIVO: regras de ajuste assistido da fundacao de churn financeiro.

POR QUE ELE EXISTE:
- separa ajustes por historico, confianca, contexto e tensao do data product principal.

PONTOS CRITICOS:
- ajustes continuam recomendacoes auditaveis, nunca mutacoes de estado real.
"""


CONFIDENCE_STEPS = ('low', 'medium', 'high')


def _resolve_recommendation_adjustment(
    *,
    base_recommendation,
    recommendation_momentum,
    recommendation_override_map,
    recommendation_timing_lookup_map,
):
    stage = recommendation_momentum.get('decay_stage') or 'unknown'
    override = (recommendation_override_map or {}).get(stage) or {}
    if not override:
        return {
            'applied': False,
            'rule_name': '',
            'reason': '',
            'base_success_rate': 0.0,
            'candidate_success_rate': 0.0,
            'success_rate_lift': 0.0,
            'candidate_realized_count': 0,
            'stage': stage,
            'stage_label': recommendation_momentum.get('decay_label', ''),
        }

    base_action = base_recommendation.get('recommended_action', '')
    candidate_action = override.get('recommended_action', '')
    base_timing = (recommendation_timing_lookup_map or {}).get((stage, base_action)) or {}
    base_success_rate = base_timing.get('success_rate', 0.0) or 0.0
    candidate_success_rate = override.get('success_rate', 0.0) or 0.0
    candidate_window_success_rate = override.get('preferred_window_success_rate', 0.0) or candidate_success_rate
    success_rate_lift = round(candidate_success_rate - base_success_rate, 1)
    windowed_success_rate_lift = round(candidate_window_success_rate - base_success_rate, 1)

    if not candidate_action or candidate_action == base_action:
        return {
            'applied': False,
            'rule_name': override.get('rule_name', ''),
            'reason': 'candidate_matches_base_action',
            'base_success_rate': base_success_rate,
            'candidate_success_rate': candidate_success_rate,
            'candidate_window_success_rate': candidate_window_success_rate,
            'success_rate_lift': success_rate_lift,
            'windowed_success_rate_lift': windowed_success_rate_lift,
            'candidate_realized_count': override.get('realized_count', 0) or 0,
            'candidate_window_realized_count': override.get('preferred_window_realized_count', 0) or 0,
            'candidate_preferred_outcome_window': override.get('preferred_outcome_window', ''),
            'stage': stage,
            'stage_label': override.get('suggestion_window_label', recommendation_momentum.get('decay_label', '')),
        }

    if base_timing and candidate_success_rate <= base_success_rate:
        return {
            'applied': False,
            'rule_name': override.get('rule_name', ''),
            'reason': 'candidate_not_better_than_base',
            'base_success_rate': base_success_rate,
            'candidate_success_rate': candidate_success_rate,
            'candidate_window_success_rate': candidate_window_success_rate,
            'success_rate_lift': success_rate_lift,
            'windowed_success_rate_lift': windowed_success_rate_lift,
            'candidate_realized_count': override.get('realized_count', 0) or 0,
            'candidate_window_realized_count': override.get('preferred_window_realized_count', 0) or 0,
            'candidate_preferred_outcome_window': override.get('preferred_outcome_window', ''),
            'stage': stage,
            'stage_label': override.get('suggestion_window_label', recommendation_momentum.get('decay_label', '')),
        }

    min_success_rate = override.get('min_success_rate', 0.0) or 0.0
    min_lift = 10.0
    if candidate_window_success_rate < min_success_rate or windowed_success_rate_lift < min_lift:
        return {
            'applied': False,
            'rule_name': override.get('rule_name', ''),
            'reason': 'candidate_without_enough_lift',
            'base_success_rate': base_success_rate,
            'candidate_success_rate': candidate_success_rate,
            'candidate_window_success_rate': candidate_window_success_rate,
            'success_rate_lift': success_rate_lift,
            'windowed_success_rate_lift': windowed_success_rate_lift,
            'candidate_realized_count': override.get('realized_count', 0) or 0,
            'candidate_window_realized_count': override.get('preferred_window_realized_count', 0) or 0,
            'candidate_preferred_outcome_window': override.get('preferred_outcome_window', ''),
            'stage': stage,
            'stage_label': override.get('suggestion_window_label', recommendation_momentum.get('decay_label', '')),
        }

    return {
        'applied': True,
        'rule_name': override.get('rule_name', ''),
        'reason': 'timing_history_override',
        'base_success_rate': base_success_rate,
        'candidate_success_rate': candidate_success_rate,
        'candidate_window_success_rate': candidate_window_success_rate,
        'success_rate_lift': success_rate_lift,
        'windowed_success_rate_lift': windowed_success_rate_lift,
        'candidate_realized_count': override.get('realized_count', 0) or 0,
        'candidate_window_realized_count': override.get('preferred_window_realized_count', 0) or 0,
        'candidate_preferred_outcome_window': override.get('preferred_outcome_window', ''),
        'candidate_recommended_action': candidate_action,
        'stage': stage,
        'stage_label': override.get('suggestion_window_label', recommendation_momentum.get('decay_label', '')),
    }


def _move_confidence(base_confidence, delta):
    try:
        current_index = CONFIDENCE_STEPS.index(base_confidence)
    except ValueError:
        current_index = 1
    next_index = min(max(current_index + delta, 0), len(CONFIDENCE_STEPS) - 1)
    return CONFIDENCE_STEPS[next_index]


def _resolve_confidence_adjustment(
    *,
    base_confidence,
    historical_score,
    queue_assist_score,
    recommendation_momentum,
    recommendation_adjustment,
):
    adjustment = {
        'applied': False,
        'rule_name': '',
        'reason': '',
        'from_confidence': base_confidence,
        'to_confidence': base_confidence,
        'evidence_historical_score': historical_score,
        'evidence_queue_assist_score': queue_assist_score,
        'evidence_success_rate': recommendation_adjustment.get('candidate_success_rate', 0.0) or 0.0,
        'evidence_realized_count': recommendation_adjustment.get('candidate_realized_count', 0) or 0,
    }
    if recommendation_adjustment.get('applied') and (
        (recommendation_adjustment.get('candidate_success_rate', 0.0) or 0.0) >= 80.0
        and (recommendation_adjustment.get('candidate_realized_count', 0) or 0) >= 5
    ):
        promoted = _move_confidence(base_confidence, 1)
        adjustment.update(
            {
                'applied': promoted != base_confidence,
                'rule_name': 'confidence_history_lift_v1',
                'reason': 'timing_override_with_strong_history',
                'to_confidence': promoted,
            }
        )
        return adjustment

    if historical_score >= 75.0 and queue_assist_score >= 65.0:
        promoted = _move_confidence(base_confidence, 1)
        adjustment.update(
            {
                'applied': promoted != base_confidence,
                'rule_name': 'confidence_history_lift_v1',
                'reason': 'historical_score_promotes_confidence',
                'to_confidence': promoted,
            }
        )
        return adjustment

    if historical_score <= 25.0 and recommendation_momentum.get('decay_stage') == 'stale':
        demoted = _move_confidence(base_confidence, -1)
        adjustment.update(
            {
                'applied': demoted != base_confidence,
                'rule_name': 'confidence_history_decay_v1',
                'reason': 'stale_window_with_low_history',
                'to_confidence': demoted,
            }
        )
        return adjustment

    return adjustment


def _resolve_contextual_guidance(
    *,
    recommended_action,
    recommendation_momentum,
    signal_bucket,
    contextual_recommendation_map,
):
    stage = recommendation_momentum.get('decay_stage') or 'unknown'
    guidance = (contextual_recommendation_map or {}).get((recommended_action, stage, signal_bucket)) or {}
    if not guidance:
        return {
            'available': False,
            'applied': False,
            'rule_name': '',
            'reason': '',
            'suggested_action_kind': '',
            'suggested_recommended_action': '',
            'success_rate': 0.0,
            'realized_count': 0,
            'stage': stage,
            'signal_bucket': signal_bucket,
        }

    suggested_recommended_action = guidance.get('suggested_recommended_action', '')
    return {
        'available': True,
        'applied': bool(suggested_recommended_action and suggested_recommended_action != recommended_action),
        'rule_name': guidance.get('rule_name', ''),
        'reason': 'compound_context_guidance_available',
        'suggested_action_kind': guidance.get('suggested_action_kind', ''),
        'suggested_recommended_action': suggested_recommended_action,
        'success_rate': guidance.get('success_rate', 0.0) or 0.0,
        'realized_count': guidance.get('realized_count', 0) or 0,
        'min_success_rate': guidance.get('min_success_rate', 0.0) or 0.0,
        'stage': stage,
        'signal_bucket': signal_bucket,
    }


def _resolve_contextual_conviction(*, contextual_priority_score, contextual_guidance):
    if not contextual_guidance.get('available'):
        return {
            'label': 'Sem leitura contextual',
            'level': 'none',
            'score': 0.0,
        }
    if contextual_priority_score >= 20.0:
        return {
            'label': 'Conviccao contextual alta',
            'level': 'high',
            'score': contextual_priority_score,
        }
    if contextual_priority_score >= 10.0:
        return {
            'label': 'Conviccao contextual media',
            'level': 'medium',
            'score': contextual_priority_score,
        }
    return {
        'label': 'Conviccao contextual baixa',
        'level': 'low',
        'score': contextual_priority_score,
    }


def _resolve_operational_band(
    *,
    priority_rank,
    recommendation_momentum,
    contextual_conviction,
    contextual_guidance,
):
    decay_stage = recommendation_momentum.get('decay_stage') or 'unknown'
    conviction_level = contextual_conviction.get('level') or 'none'

    if priority_rank <= 2 and decay_stage != 'stale' and conviction_level == 'high':
        return {
            'label': 'Agir agora',
            'level': 'act_now',
        }
    if contextual_guidance.get('available') and conviction_level in {'medium', 'high'}:
        return {
            'label': 'Agir com cautela',
            'level': 'act_with_caution',
        }
    return {
        'label': 'Observar primeiro',
        'level': 'observe_first',
    }


def _resolve_turn_priority_tension_guidance(
    *,
    recommendation_momentum,
    signal_bucket,
    turn_priority_tension_context_map,
):
    stage = recommendation_momentum.get('decay_stage') or 'unknown'
    guidance = (turn_priority_tension_context_map or {}).get((stage, signal_bucket)) or {}
    if not guidance:
        return {
            'available': False,
            'tendency': 'unknown',
            'label': 'Sem leitura de tensao',
            'note': 'Ainda sem amostra suficiente para dizer se a tensao neste contexto costuma ajudar ou dispersar.',
            'healthy_tension_rate': 0.0,
            'dangerous_tension_rate': 0.0,
            'realized_count': 0,
            'stage': stage,
            'signal_bucket': signal_bucket,
        }

    tendency = guidance.get('tendency') or 'mixed'
    if tendency == 'healthy':
        label = 'Tensao costuma ser saudavel'
        note = (
            f"Neste timing e gravidade, a tensao historicamente ajudou mais do que atrapalhou "
            f"({guidance.get('healthy_tension_rate', 0.0)}% vs {guidance.get('dangerous_tension_rate', 0.0)}%)."
        )
    elif tendency == 'dangerous':
        label = 'Tensao costuma virar ruido'
        note = (
            f"Neste timing e gravidade, a tensao historicamente dispersou mais do que ajudou "
            f"({guidance.get('dangerous_tension_rate', 0.0)}% vs {guidance.get('healthy_tension_rate', 0.0)}%)."
        )
    else:
        label = 'Tensao ainda mista'
        note = (
            f"Neste timing e gravidade, a tensao ainda nao mostra lado dominante "
            f"({guidance.get('healthy_tension_rate', 0.0)}% vs {guidance.get('dangerous_tension_rate', 0.0)}%)."
        )
    return {
        'available': True,
        'tendency': tendency,
        'label': label,
        'note': note,
        'healthy_tension_rate': guidance.get('healthy_tension_rate', 0.0) or 0.0,
        'dangerous_tension_rate': guidance.get('dangerous_tension_rate', 0.0) or 0.0,
        'realized_count': guidance.get('realized_count', 0) or 0,
        'stage': stage,
        'signal_bucket': signal_bucket,
        'rule_name': guidance.get('rule_name', ''),
    }
