"""
ARQUIVO: regras de timing e janela da fundacao de churn financeiro.

POR QUE ELE EXISTE:
- isola leitura de momentum, ancora e janela de predicao operacional.

PONTOS CRITICOS:
- janela prevista e apoio operacional; nao e verdade transacional.
"""

from finance.follow_up_tracker import RECOMMENDATION_OUTCOME_WINDOWS


def _normalize_datetime_to_date(value):
    if value is None:
        return None
    if hasattr(value, 'date'):
        return value.date()
    return value


def _days_since(reference_date, value):
    normalized = _normalize_datetime_to_date(value)
    if normalized is None:
        return None
    return max((reference_date - normalized).days, 0)


def _parse_window_days(value):
    normalized = str(value or '').strip().lower()
    if normalized.endswith('d'):
        normalized = normalized[:-1]
    try:
        return max(int(normalized), 1)
    except (TypeError, ValueError):
        return 7


def _resolve_recommendation_anchor(
    *,
    recommended_action,
    first_overdue_date,
    latest_enrollment_start_date,
    latest_enrollment_end_date,
    latest_finance_touch_at,
    last_paid_at,
):
    if recommended_action == 'review_winback':
        return latest_enrollment_end_date or latest_finance_touch_at or first_overdue_date
    if recommended_action == 'monitor_recent_reactivation':
        return latest_enrollment_start_date or latest_finance_touch_at or last_paid_at
    if recommended_action in {
        'send_financial_followup',
        'escalate_manual_retention',
        'monitor_and_nudge',
        'observe_payment_resolution',
    }:
        return latest_finance_touch_at or first_overdue_date
    return latest_finance_touch_at or last_paid_at or first_overdue_date


def _build_recommendation_momentum(*, recommended_action, today, anchor_at):
    action_window = RECOMMENDATION_OUTCOME_WINDOWS.get(recommended_action, '7d')
    window_days = _parse_window_days(action_window)
    age_days = _days_since(today, anchor_at)
    if age_days is None:
        return {
            'action_window': action_window,
            'window_days': window_days,
            'window_age_days': None,
            'window_progress_ratio': 0.0,
            'decay_stage': 'fresh',
            'decay_label': 'Janela pronta para agir',
            'decay_penalty': 0.0,
        }

    progress_ratio = round(age_days / window_days, 2) if window_days else 0.0
    if progress_ratio > 1.0:
        return {
            'action_window': action_window,
            'window_days': window_days,
            'window_age_days': age_days,
            'window_progress_ratio': progress_ratio,
            'decay_stage': 'stale',
            'decay_label': 'Passou da janela ideal',
            'decay_penalty': 25.0,
        }
    if progress_ratio >= 0.5:
        return {
            'action_window': action_window,
            'window_days': window_days,
            'window_age_days': age_days,
            'window_progress_ratio': progress_ratio,
            'decay_stage': 'cooling',
            'decay_label': 'Janela esfriando',
            'decay_penalty': 12.0,
        }
    return {
        'action_window': action_window,
        'window_days': window_days,
        'window_age_days': age_days,
        'window_progress_ratio': progress_ratio,
        'decay_stage': 'fresh',
        'decay_label': 'Janela pronta para agir',
        'decay_penalty': 0.0,
    }


def _format_prediction_window_label(value):
    normalized = str(value or '').strip().lower()
    if normalized.startswith('next_') and normalized.endswith('_days'):
        days = normalized.removeprefix('next_').removesuffix('_days')
        return f'proximos {days} dias'
    return normalized or 'janela indefinida'


def _resolve_prediction_window_adjustment(
    *,
    base_prediction_window,
    recommended_action,
    prediction_window_override_map,
):
    override = (prediction_window_override_map or {}).get(recommended_action) or {}
    candidate_window = override.get('outcome_window', '')
    if not candidate_window:
        return {
            'applied': False,
            'rule_name': '',
            'reason': '',
            'from_prediction_window': base_prediction_window,
            'to_prediction_window': base_prediction_window,
            'evidence_success_rate': 0.0,
            'evidence_realized_count': 0,
        }

    candidate_prediction_window = f"next_{candidate_window.removesuffix('d')}_days"
    if candidate_prediction_window == base_prediction_window:
        return {
            'applied': False,
            'rule_name': override.get('rule_name', ''),
            'reason': 'candidate_matches_base_window',
            'from_prediction_window': base_prediction_window,
            'to_prediction_window': base_prediction_window,
            'evidence_success_rate': override.get('success_rate', 0.0) or 0.0,
            'evidence_realized_count': override.get('realized_count', 0) or 0,
        }

    return {
        'applied': True,
        'rule_name': override.get('rule_name', ''),
        'reason': 'historical_window_override',
        'from_prediction_window': base_prediction_window,
        'to_prediction_window': candidate_prediction_window,
        'from_prediction_window_label': _format_prediction_window_label(base_prediction_window),
        'to_prediction_window_label': _format_prediction_window_label(candidate_prediction_window),
        'evidence_success_rate': override.get('success_rate', 0.0) or 0.0,
        'evidence_realized_count': override.get('realized_count', 0) or 0,
    }
