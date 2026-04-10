"""
ARQUIVO: regras base de sinal e recomendacao da fundacao de churn financeiro.

POR QUE ELE EXISTE:
- separa decisao pura de sinal, recomendacao e prioridade do data product principal.

PONTOS CRITICOS:
- atraso financeiro continua sendo sinal; churn real inicial continua sendo status inativo do aluno.
"""

from decimal import Decimal

from finance.model_definitions import EnrollmentStatus


ZERO_MONEY = Decimal('0.00')


def _resolve_signal_bucket(*, actual_status, open_amount, overdue_30d, overdue_60d, latest_enrollment_status, reactivated_after_inactive):
    if actual_status == 'inactive':
        return 'already_inactive'
    if reactivated_after_inactive:
        return 'recovered'
    if open_amount > ZERO_MONEY and (overdue_60d >= 2 or latest_enrollment_status in {EnrollmentStatus.CANCELED, EnrollmentStatus.EXPIRED}):
        return 'high_signal'
    if overdue_30d >= 1 or latest_enrollment_status in {EnrollmentStatus.CANCELED, EnrollmentStatus.EXPIRED}:
        return 'watch'
    return 'stable'


def _build_recommendation_contract(
    *,
    actual_status,
    signal_bucket,
    overdue_60d,
    open_amount,
    finance_touches_30d,
    reactivated_after_inactive,
):
    prediction_window = 'next_30_days'

    if actual_status == 'inactive':
        return {
            'recommended_action': 'review_winback',
            'confidence': 'high',
            'prediction_window': prediction_window,
            'rule_version': 'finance_queue_v1',
            'is_recommendation': True,
        }

    if reactivated_after_inactive:
        return {
            'recommended_action': 'monitor_recent_reactivation',
            'confidence': 'medium',
            'prediction_window': prediction_window,
            'rule_version': 'finance_queue_v1',
            'is_recommendation': True,
        }

    if signal_bucket == 'high_signal':
        if finance_touches_30d > 0:
            return {
                'recommended_action': 'escalate_manual_retention',
                'confidence': 'high',
                'prediction_window': prediction_window,
                'rule_version': 'finance_queue_v1',
                'is_recommendation': True,
            }
        return {
            'recommended_action': 'send_financial_followup',
            'confidence': 'high',
            'prediction_window': prediction_window,
            'rule_version': 'finance_queue_v1',
            'is_recommendation': True,
        }

    if signal_bucket == 'watch':
        return {
            'recommended_action': 'monitor_and_nudge',
            'confidence': 'medium',
            'prediction_window': prediction_window,
            'rule_version': 'finance_queue_v1',
            'is_recommendation': True,
        }

    if open_amount > ZERO_MONEY or overdue_60d > 0:
        return {
            'recommended_action': 'observe_payment_resolution',
            'confidence': 'medium',
            'prediction_window': prediction_window,
            'rule_version': 'finance_queue_v1',
            'is_recommendation': True,
        }

    return {
        'recommended_action': 'maintain_relationship',
        'confidence': 'low',
        'prediction_window': prediction_window,
        'rule_version': 'finance_queue_v1',
        'is_recommendation': True,
    }


def _resolve_priority_contract(*, actual_status, signal_bucket, confidence, finance_touches_30d):
    if actual_status == 'inactive':
        return {'priority_rank': 0, 'priority_label': 'Winback imediato'}
    if signal_bucket == 'high_signal':
        if finance_touches_30d > 0:
            return {'priority_rank': 1, 'priority_label': 'Escalada manual'}
        return {'priority_rank': 2, 'priority_label': 'Ataque imediato'}
    if signal_bucket == 'watch':
        return {'priority_rank': 3, 'priority_label': 'Observacao ativa'}
    if signal_bucket == 'recovered':
        return {'priority_rank': 4, 'priority_label': 'Pos-recuperacao'}
    return {
        'priority_rank': 5 if confidence == 'low' else 4,
        'priority_label': 'Base estavel',
    }


def _build_reason_codes(*, actual_status, overdue_60d, open_amount, latest_enrollment_status, finance_touches_30d, reactivated_after_inactive):
    reason_codes = []
    if actual_status == 'inactive':
        reason_codes.append('student_inactive')
    if overdue_60d >= 2:
        reason_codes.append('recurring_overdue_60d')
    elif overdue_60d == 1:
        reason_codes.append('overdue_60d')
    if open_amount > ZERO_MONEY:
        reason_codes.append('open_amount_active')
    if latest_enrollment_status in {EnrollmentStatus.CANCELED, EnrollmentStatus.EXPIRED}:
        reason_codes.append(f'enrollment_{latest_enrollment_status}')
    if finance_touches_30d > 0:
        reason_codes.append('recent_finance_touch')
    if reactivated_after_inactive:
        reason_codes.append('reactivated_after_inactive')
    return reason_codes or ['stable_base']
