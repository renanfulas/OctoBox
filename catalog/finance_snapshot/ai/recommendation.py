"""
ARQUIVO: heuristicas e ajustes de recomendacao da fundacao de churn.

POR QUE ELE EXISTE:
- concentra a camada assistida sem misturar coleta de fatos ou montagem final da fila.
"""

from __future__ import annotations

from ..rules.adjustments import (
    _resolve_confidence_adjustment,
    _resolve_contextual_conviction,
    _resolve_contextual_guidance,
    _resolve_operational_band,
    _resolve_recommendation_adjustment,
    _resolve_turn_priority_tension_guidance,
)
from ..rules.base import (
    _build_reason_codes,
    _build_recommendation_contract,
    _resolve_priority_contract,
    _resolve_signal_bucket,
)
from ..rules.timing import (
    _build_recommendation_momentum,
    _resolve_prediction_window_adjustment,
    _resolve_recommendation_anchor,
)


def build_recommendation_state(
    *,
    actual_status,
    facts,
    today,
    historical_score_map,
    recommendation_timing_map,
    recommendation_timing_lookup_map,
    recommendation_override_map,
    prediction_window_override_map,
    contextual_recommendation_map,
    turn_priority_tension_context_map,
):
    signal_bucket = _resolve_signal_bucket(
        actual_status=actual_status,
        open_amount=facts['open_amount'],
        overdue_30d=facts['overdue_30d'],
        overdue_60d=facts['overdue_60d'],
        latest_enrollment_status=facts['latest_enrollment_status'],
        reactivated_after_inactive=facts['reactivated_after_inactive'],
    )

    reason_codes = _build_reason_codes(
        actual_status=actual_status,
        overdue_60d=facts['overdue_60d'],
        open_amount=facts['open_amount'],
        latest_enrollment_status=facts['latest_enrollment_status'],
        finance_touches_30d=facts['finance_touches_30d'],
        reactivated_after_inactive=facts['reactivated_after_inactive'],
    )
    base_recommendation = _build_recommendation_contract(
        actual_status=actual_status,
        signal_bucket=signal_bucket,
        overdue_60d=facts['overdue_60d'],
        open_amount=facts['open_amount'],
        finance_touches_30d=facts['finance_touches_30d'],
        reactivated_after_inactive=facts['reactivated_after_inactive'],
    )
    priority = _resolve_priority_contract(
        actual_status=actual_status,
        signal_bucket=signal_bucket,
        confidence=base_recommendation['confidence'],
        finance_touches_30d=facts['finance_touches_30d'],
    )
    base_historical_score = historical_score_map.get(base_recommendation['recommended_action'], 0.0) or 0.0
    recommendation_anchor_at = _resolve_recommendation_anchor(
        recommended_action=base_recommendation['recommended_action'],
        first_overdue_date=facts['first_overdue_date'],
        latest_enrollment_start_date=facts['latest_enrollment_start_date'],
        latest_enrollment_end_date=facts['latest_enrollment_end_date'],
        latest_finance_touch_at=facts['latest_finance_touch_at'],
        last_paid_at=facts['last_paid_at'],
    )
    recommendation_momentum = _build_recommendation_momentum(
        recommended_action=base_recommendation['recommended_action'],
        today=today,
        anchor_at=recommendation_anchor_at,
    )
    recommendation_adjustment = _resolve_recommendation_adjustment(
        base_recommendation=base_recommendation,
        recommendation_momentum=recommendation_momentum,
        recommendation_override_map=recommendation_override_map,
        recommendation_timing_lookup_map=recommendation_timing_lookup_map,
    )
    recommendation = dict(base_recommendation)
    if recommendation_adjustment.get('applied'):
        recommendation['recommended_action'] = recommendation_adjustment['candidate_recommended_action']
        recommendation['rule_version'] = f"{base_recommendation['rule_version']}+{recommendation_adjustment['rule_name']}"
    prediction_window_adjustment = _resolve_prediction_window_adjustment(
        base_prediction_window=base_recommendation['prediction_window'],
        recommended_action=recommendation['recommended_action'],
        prediction_window_override_map=prediction_window_override_map,
    )
    recommendation['prediction_window'] = prediction_window_adjustment['to_prediction_window']
    if prediction_window_adjustment.get('applied'):
        recommendation['rule_version'] = f"{recommendation['rule_version']}+{prediction_window_adjustment['rule_name']}"
    historical_score = historical_score_map.get(recommendation['recommended_action'], base_historical_score) or 0.0
    if recommendation_adjustment.get('applied'):
        recommendation_anchor_at = _resolve_recommendation_anchor(
            recommended_action=recommendation['recommended_action'],
            first_overdue_date=facts['first_overdue_date'],
            latest_enrollment_start_date=facts['latest_enrollment_start_date'],
            latest_enrollment_end_date=facts['latest_enrollment_end_date'],
            latest_finance_touch_at=facts['latest_finance_touch_at'],
            last_paid_at=facts['last_paid_at'],
        )
        recommendation_momentum = _build_recommendation_momentum(
            recommended_action=recommendation['recommended_action'],
            today=today,
            anchor_at=recommendation_anchor_at,
        )
    timing_guidance = recommendation_timing_map.get(recommendation_momentum['decay_stage']) or {}
    queue_assist_score = max(
        round(historical_score - recommendation_momentum['decay_penalty'], 1),
        0.0,
    )
    confidence_adjustment = _resolve_confidence_adjustment(
        base_confidence=base_recommendation['confidence'],
        historical_score=historical_score,
        queue_assist_score=queue_assist_score,
        recommendation_momentum=recommendation_momentum,
        recommendation_adjustment=recommendation_adjustment,
    )
    recommendation['confidence'] = confidence_adjustment['to_confidence']
    contextual_guidance = _resolve_contextual_guidance(
        recommended_action=recommendation['recommended_action'],
        recommendation_momentum=recommendation_momentum,
        signal_bucket=signal_bucket,
        contextual_recommendation_map=contextual_recommendation_map,
    )
    contextual_priority_score = 0.0
    if contextual_guidance.get('available'):
        contextual_priority_score = round(
            max(
                (contextual_guidance.get('success_rate', 0.0) or 0.0)
                - (contextual_guidance.get('min_success_rate', 0.0) or 0.0),
                0.0,
            ),
            1,
        )
    contextual_conviction = _resolve_contextual_conviction(
        contextual_priority_score=contextual_priority_score,
        contextual_guidance=contextual_guidance,
    )
    operational_band = _resolve_operational_band(
        priority_rank=priority['priority_rank'],
        recommendation_momentum=recommendation_momentum,
        contextual_conviction=contextual_conviction,
        contextual_guidance=contextual_guidance,
    )
    turn_priority_tension_guidance = _resolve_turn_priority_tension_guidance(
        recommendation_momentum=recommendation_momentum,
        signal_bucket=signal_bucket,
        turn_priority_tension_context_map=turn_priority_tension_context_map,
    )

    return {
        'signal_bucket': signal_bucket,
        'reason_codes': reason_codes,
        'base_recommendation': base_recommendation,
        'recommendation': recommendation,
        'priority': priority,
        'base_historical_score': base_historical_score,
        'historical_score': historical_score,
        'recommendation_momentum': recommendation_momentum,
        'recommendation_adjustment': recommendation_adjustment,
        'prediction_window_adjustment': prediction_window_adjustment,
        'timing_guidance': timing_guidance,
        'queue_assist_score': queue_assist_score,
        'confidence_adjustment': confidence_adjustment,
        'contextual_guidance': contextual_guidance,
        'contextual_priority_score': contextual_priority_score,
        'contextual_conviction': contextual_conviction,
        'operational_band': operational_band,
        'turn_priority_tension_guidance': turn_priority_tension_guidance,
    }


__all__ = ['build_recommendation_state']
