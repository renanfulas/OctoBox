"""
ARQUIVO: fundacao reconciliada de churn financeiro para o snapshot do catalogo.

POR QUE ELE EXISTE:
- organiza em uma leitura unica os fatos que mais tarde vao alimentar fila operacional, score e ML financeiro.

O QUE ESTE ARQUIVO FAZ:
1. separa sinal financeiro, estado operacional e leitura final do aluno.
2. reconcilia pagamentos, matriculas e comunicacoes financeiras por aluno.
3. entrega um data product pequeno e estavel para a central financeira.

PONTOS CRITICOS:
- esta camada descreve fatos e sinais; ela nao inventa score nem substitui a verdade transacional.
- atraso nao pode ser confundido com churn real.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from communications.model_definitions.whatsapp import MessageDirection
from communications.models import WhatsAppMessageLog
from finance.model_definitions import EnrollmentStatus, PaymentStatus
from .rules.adjustments import (
    _resolve_confidence_adjustment,
    _resolve_contextual_conviction,
    _resolve_contextual_guidance,
    _resolve_operational_band,
    _resolve_recommendation_adjustment,
    _resolve_turn_priority_tension_guidance,
)
from .rules.base import (
    _build_reason_codes,
    _build_recommendation_contract,
    _resolve_priority_contract,
    _resolve_signal_bucket,
)
from .rules.timing import (
    _build_recommendation_momentum,
    _resolve_prediction_window_adjustment,
    _resolve_recommendation_anchor,
)


ZERO_MONEY = Decimal('0.00')


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


def _is_payment_open(payment, *, today):
    return (
        payment.status in {PaymentStatus.PENDING, PaymentStatus.OVERDUE}
        and payment.due_date < today
    ) or (
        payment.status == PaymentStatus.OVERDUE
    )


def build_financial_churn_foundation(
    *,
    students,
    payments,
    enrollments,
    today,
    limit=8,
    queue_focus='',
    historical_score_map=None,
    recommendation_timing_map=None,
    recommendation_timing_lookup_map=None,
    recommendation_override_map=None,
    prediction_window_override_map=None,
    contextual_recommendation_map=None,
    turn_priority_tension_context_map=None,
):
    scoped_students = list(students)
    student_ids = [student.id for student in scoped_students]
    historical_score_map = historical_score_map or {}
    recommendation_timing_map = recommendation_timing_map or {}
    recommendation_timing_lookup_map = recommendation_timing_lookup_map or {}
    recommendation_override_map = recommendation_override_map or {}
    prediction_window_override_map = prediction_window_override_map or {}
    contextual_recommendation_map = contextual_recommendation_map or {}
    turn_priority_tension_context_map = turn_priority_tension_context_map or {}

    payments_by_student = defaultdict(list)
    enrollments_by_student = defaultdict(list)
    if student_ids:
        for payment in payments.filter(student_id__in=student_ids).order_by('due_date', 'id'):
            payments_by_student[payment.student_id].append(payment)
        for enrollment in enrollments.filter(student_id__in=student_ids).order_by('start_date', 'updated_at', 'id'):
            enrollments_by_student[enrollment.student_id].append(enrollment)

    finance_messages_by_student = defaultdict(list)
    if student_ids:
        finance_messages = (
            WhatsAppMessageLog.objects.select_related('contact', 'contact__linked_student')
            .filter(
                contact__linked_student_id__in=student_ids,
                direction=MessageDirection.OUTBOUND,
            )
            .order_by('-delivered_at', '-created_at', '-id')
        )
        for message in finance_messages:
            raw_payload = message.raw_payload or {}
            if raw_payload.get('source') != 'operational-message':
                continue
            finance_messages_by_student[message.contact.linked_student_id].append(message)

    rows = []
    summary = {
        'students_in_scope': len(scoped_students),
        'actual_churn_count': 0,
        'high_signal_count': 0,
        'watch_count': 0,
        'recovered_count': 0,
        'recent_finance_touch_count': 0,
    }

    for student in scoped_students:
        student_payments = payments_by_student.get(student.id, [])
        student_enrollments = enrollments_by_student.get(student.id, [])
        student_messages = finance_messages_by_student.get(student.id, [])

        open_amount = ZERO_MONEY
        overdue_days_sum = 0
        overdue_counter = 0
        overdue_30d = 0
        overdue_60d = 0
        overdue_90d = 0
        first_overdue_date = None
        first_overdue_payment_id = None
        last_paid_at = None
        paid_payment_count = 0

        for payment in student_payments:
            if payment.status == PaymentStatus.PAID:
                paid_payment_count += 1
                payment_paid_at = payment.paid_at or payment.due_date
                if last_paid_at is None or payment_paid_at > last_paid_at:
                    last_paid_at = payment_paid_at

            if not _is_payment_open(payment, today=today):
                continue

            overdue_days = max((today - payment.due_date).days, 0)
            open_amount += payment.amount or ZERO_MONEY
            overdue_days_sum += overdue_days
            overdue_counter += 1
            if first_overdue_date is None or payment.due_date < first_overdue_date:
                first_overdue_date = payment.due_date
                first_overdue_payment_id = payment.id
            if overdue_days <= 30:
                overdue_30d += 1
            if overdue_days <= 60:
                overdue_60d += 1
            if overdue_days <= 90:
                overdue_90d += 1

        latest_enrollment = student_enrollments[-1] if student_enrollments else None
        latest_enrollment_start_date = getattr(latest_enrollment, 'start_date', None)
        latest_enrollment_status = getattr(latest_enrollment, 'status', '')
        latest_enrollment_end_date = getattr(latest_enrollment, 'end_date', None)
        reactivated_after_inactive = student.status != 'inactive' and any(
            enrollment.status in {EnrollmentStatus.CANCELED, EnrollmentStatus.EXPIRED}
            for enrollment in student_enrollments[:-1]
        ) and latest_enrollment_status == EnrollmentStatus.ACTIVE

        latest_finance_touch = student_messages[0] if student_messages else None
        latest_finance_touch_at = getattr(latest_finance_touch, 'delivered_at', None) or getattr(latest_finance_touch, 'created_at', None)
        latest_finance_touch_payload = getattr(latest_finance_touch, 'raw_payload', {}) or {}
        finance_touches_30d = sum(
            1
            for message in student_messages
            if _days_since(today, getattr(message, 'delivered_at', None) or getattr(message, 'created_at', None)) is not None
            and _days_since(today, getattr(message, 'delivered_at', None) or getattr(message, 'created_at', None)) <= 30
        )

        signal_bucket = _resolve_signal_bucket(
            actual_status=student.status,
            open_amount=open_amount,
            overdue_30d=overdue_30d,
            overdue_60d=overdue_60d,
            latest_enrollment_status=latest_enrollment_status,
            reactivated_after_inactive=reactivated_after_inactive,
        )

        reason_codes = _build_reason_codes(
            actual_status=student.status,
            overdue_60d=overdue_60d,
            open_amount=open_amount,
            latest_enrollment_status=latest_enrollment_status,
            finance_touches_30d=finance_touches_30d,
            reactivated_after_inactive=reactivated_after_inactive,
        )
        base_recommendation = _build_recommendation_contract(
            actual_status=student.status,
            signal_bucket=signal_bucket,
            overdue_60d=overdue_60d,
            open_amount=open_amount,
            finance_touches_30d=finance_touches_30d,
            reactivated_after_inactive=reactivated_after_inactive,
        )
        priority = _resolve_priority_contract(
            actual_status=student.status,
            signal_bucket=signal_bucket,
            confidence=base_recommendation['confidence'],
            finance_touches_30d=finance_touches_30d,
        )
        base_historical_score = historical_score_map.get(base_recommendation['recommended_action'], 0.0) or 0.0
        recommendation_anchor_at = _resolve_recommendation_anchor(
            recommended_action=base_recommendation['recommended_action'],
            first_overdue_date=first_overdue_date,
            latest_enrollment_start_date=latest_enrollment_start_date,
            latest_enrollment_end_date=latest_enrollment_end_date,
            latest_finance_touch_at=latest_finance_touch_at,
            last_paid_at=last_paid_at,
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
                first_overdue_date=first_overdue_date,
                latest_enrollment_start_date=latest_enrollment_start_date,
                latest_enrollment_end_date=latest_enrollment_end_date,
                latest_finance_touch_at=latest_finance_touch_at,
                last_paid_at=last_paid_at,
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

        if student.status == 'inactive':
            summary['actual_churn_count'] += 1
        if signal_bucket == 'high_signal':
            summary['high_signal_count'] += 1
        elif signal_bucket == 'watch':
            summary['watch_count'] += 1
        elif signal_bucket == 'recovered':
            summary['recovered_count'] += 1
        if finance_touches_30d > 0:
            summary['recent_finance_touch_count'] += 1

        rows.append(
            {
                'student_id': student.id,
                'student_name': student.full_name,
                'student_phone': student.phone,
                'payment_id': first_overdue_payment_id,
                'enrollment_id': getattr(latest_enrollment, 'id', None),
                'actual_student_status': student.status,
                'actual_churn_event': student.status == 'inactive',
                'signal_bucket': signal_bucket,
                'reason_codes': reason_codes,
                'recommended_action': recommendation['recommended_action'],
                'recommended_action_base': base_recommendation['recommended_action'],
                'confidence': recommendation['confidence'],
                'confidence_base': base_recommendation['confidence'],
                'prediction_window': recommendation['prediction_window'],
                'prediction_window_base': base_recommendation['prediction_window'],
                'rule_version': recommendation['rule_version'],
                'is_recommendation': recommendation['is_recommendation'],
                'priority_rank': priority['priority_rank'],
                'priority_label': priority['priority_label'],
                'historical_score': historical_score,
                'base_historical_score': base_historical_score,
                'queue_assist_score': queue_assist_score,
                'contextual_priority_score': contextual_priority_score,
                'contextual_conviction': contextual_conviction,
                'operational_band': operational_band,
                'priority_order_reason': 'missao_operacional_then_historical_score_then_contextual_score',
                'recommendation_momentum': recommendation_momentum,
                'recommendation_adjustment': recommendation_adjustment,
                'confidence_adjustment': confidence_adjustment,
                'prediction_window_adjustment': prediction_window_adjustment,
                'contextual_guidance': contextual_guidance,
                'turn_priority_tension_guidance': turn_priority_tension_guidance,
                'timing_guidance': {
                    'best_action_for_stage': timing_guidance.get('recommended_action', ''),
                    'best_action_success_rate': timing_guidance.get('success_rate', 0.0) or 0.0,
                    'best_action_realized_count': timing_guidance.get('realized_count', 0) or 0,
                    'best_action_label': timing_guidance.get('suggestion_window_label', recommendation_momentum['decay_label']),
                    'is_aligned_with_best_action': recommendation['recommended_action'] == timing_guidance.get('recommended_action', ''),
                },
                'financial_signal': {
                    'days_since_last_payment': _days_since(today, last_paid_at),
                    'overdue_payment_count_30d': overdue_30d,
                    'overdue_payment_count_60d': overdue_60d,
                    'overdue_payment_count_90d': overdue_90d,
                    'oldest_open_due_date': first_overdue_date,
                    'total_open_amount': open_amount,
                    'average_overdue_days': round(overdue_days_sum / overdue_counter, 1) if overdue_counter else 0,
                    'time_to_first_overdue_days': _days_since(first_overdue_date, getattr(student_enrollments[0], 'start_date', None))
                    if first_overdue_date and student_enrollments else None,
                    'paid_payment_count': paid_payment_count,
                },
                'operational_state': {
                    'latest_enrollment_status': latest_enrollment_status,
                    'latest_enrollment_start_date': latest_enrollment_start_date,
                    'latest_enrollment_end_date': latest_enrollment_end_date,
                    'latest_plan_name': getattr(getattr(latest_enrollment, 'plan', None), 'name', ''),
                    'enrollment_status_change_count': len(student_enrollments),
                    'reactivated_after_inactive': reactivated_after_inactive,
                },
                'communication_state': {
                    'finance_touches_30d': finance_touches_30d,
                    'last_finance_touch_at': latest_finance_touch_at,
                    'last_finance_touch_action_kind': latest_finance_touch_payload.get('action_kind', ''),
                },
            }
        )

    if queue_focus:
        rows = [row for row in rows if row['signal_bucket'] == queue_focus]

    rows.sort(
        key=lambda row: (
            row['priority_rank'],
            -row['queue_assist_score'],
            -row.get('contextual_priority_score', 0.0),
            -(row['financial_signal']['overdue_payment_count_60d']),
            -(float(row['financial_signal']['total_open_amount'] or ZERO_MONEY)),
            row['student_name'],
        )
    )

    return {
        'summary': summary,
        'queue_focus': queue_focus,
        'filtered_count': len(rows),
        'rows': rows,
        'queue_preview': rows[:limit],
        'contract': {
            'actual_status_field': 'actual_student_status',
            'actual_churn_rule': 'student.status == inactive',
                'queue_contract': (
                    'student_id, actual_student_status, signal_bucket, priority_rank, priority_label, historical_score, '
                    'queue_assist_score, contextual_priority_score, contextual_conviction, operational_band, confidence, confidence_base, confidence_adjustment, recommended_action, '
                    'recommended_action_base, recommendation_adjustment, contextual_guidance, turn_priority_tension_guidance, reason_codes, prediction_window, prediction_window_base, '
                    'prediction_window_adjustment, rule_version, is_recommendation'
                ),
            'future_inference_contract': (
                'student_id, actual_student_status, financial_risk_score, churn_risk_score, confidence, '
                'reason_codes, recommended_action, computed_at, rule_version_or_model_version, prediction_window'
            ),
        },
    }


__all__ = ['build_financial_churn_foundation']
