"""
ARQUIVO: orquestrador da fundacao de churn financeiro.

POR QUE ELE EXISTE:
- monta a fila assistida a partir de fatos brutos e heuristicas separadas.
- preserva a assinatura publica enquanto reduz concentracao em um unico arquivo.
"""

from __future__ import annotations

from collections import defaultdict

from communications.model_definitions.whatsapp import MessageDirection
from communications.models import WhatsAppMessageLog

from .facts import ZERO_MONEY, build_student_churn_facts, days_since
from .recommendation import build_recommendation_state


def _load_payments_by_student(*, payments, student_ids):
    payments_by_student = defaultdict(list)
    if not student_ids:
        return payments_by_student
    for payment in payments.filter(student_id__in=student_ids).order_by('due_date', 'id'):
        payments_by_student[payment.student_id].append(payment)
    return payments_by_student


def _load_enrollments_by_student(*, enrollments, student_ids):
    enrollments_by_student = defaultdict(list)
    if not student_ids:
        return enrollments_by_student
    for enrollment in enrollments.filter(student_id__in=student_ids).order_by('start_date', 'updated_at', 'id'):
        enrollments_by_student[enrollment.student_id].append(enrollment)
    return enrollments_by_student


def _load_finance_messages_by_student(*, student_ids):
    finance_messages_by_student = defaultdict(list)
    if not student_ids:
        return finance_messages_by_student
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
    return finance_messages_by_student


def _update_summary(summary, *, actual_status, signal_bucket, finance_touches_30d):
    if actual_status == 'inactive':
        summary['actual_churn_count'] += 1
    if signal_bucket == 'high_signal':
        summary['high_signal_count'] += 1
    elif signal_bucket == 'watch':
        summary['watch_count'] += 1
    elif signal_bucket == 'recovered':
        summary['recovered_count'] += 1
    if finance_touches_30d > 0:
        summary['recent_finance_touch_count'] += 1


def _build_queue_row(*, student, facts, recommendation_state, today):
    latest_enrollment = facts['latest_enrollment']
    recommendation = recommendation_state['recommendation']
    base_recommendation = recommendation_state['base_recommendation']
    timing_guidance = recommendation_state['timing_guidance']

    return {
        'student_id': student.id,
        'student_name': student.full_name,
        'student_phone': student.phone,
        'payment_id': facts['first_overdue_payment_id'],
        'enrollment_id': getattr(latest_enrollment, 'id', None),
        'actual_student_status': student.status,
        'actual_churn_event': student.status == 'inactive',
        'signal_bucket': recommendation_state['signal_bucket'],
        'reason_codes': recommendation_state['reason_codes'],
        'recommended_action': recommendation['recommended_action'],
        'recommended_action_base': base_recommendation['recommended_action'],
        'confidence': recommendation['confidence'],
        'confidence_base': base_recommendation['confidence'],
        'prediction_window': recommendation['prediction_window'],
        'prediction_window_base': base_recommendation['prediction_window'],
        'rule_version': recommendation['rule_version'],
        'is_recommendation': recommendation['is_recommendation'],
        'priority_rank': recommendation_state['priority']['priority_rank'],
        'priority_label': recommendation_state['priority']['priority_label'],
        'historical_score': recommendation_state['historical_score'],
        'base_historical_score': recommendation_state['base_historical_score'],
        'queue_assist_score': recommendation_state['queue_assist_score'],
        'contextual_priority_score': recommendation_state['contextual_priority_score'],
        'contextual_conviction': recommendation_state['contextual_conviction'],
        'operational_band': recommendation_state['operational_band'],
        'priority_order_reason': 'missao_operacional_then_historical_score_then_contextual_score',
        'recommendation_momentum': recommendation_state['recommendation_momentum'],
        'recommendation_adjustment': recommendation_state['recommendation_adjustment'],
        'confidence_adjustment': recommendation_state['confidence_adjustment'],
        'prediction_window_adjustment': recommendation_state['prediction_window_adjustment'],
        'contextual_guidance': recommendation_state['contextual_guidance'],
        'turn_priority_tension_guidance': recommendation_state['turn_priority_tension_guidance'],
        'timing_guidance': {
            'best_action_for_stage': timing_guidance.get('recommended_action', ''),
            'best_action_success_rate': timing_guidance.get('success_rate', 0.0) or 0.0,
            'best_action_realized_count': timing_guidance.get('realized_count', 0) or 0,
            'best_action_label': timing_guidance.get('suggestion_window_label', recommendation_state['recommendation_momentum']['decay_label']),
            'is_aligned_with_best_action': recommendation['recommended_action'] == timing_guidance.get('recommended_action', ''),
        },
        'financial_signal': {
            'days_since_last_payment': days_since(today, facts['last_paid_at']),
            'overdue_payment_count_30d': facts['overdue_30d'],
            'overdue_payment_count_60d': facts['overdue_60d'],
            'overdue_payment_count_90d': facts['overdue_90d'],
            'oldest_open_due_date': facts['first_overdue_date'],
            'total_open_amount': facts['open_amount'],
            'average_overdue_days': round(facts['overdue_days_sum'] / facts['overdue_counter'], 1) if facts['overdue_counter'] else 0,
            'time_to_first_overdue_days': days_since(facts['first_overdue_date'], getattr(facts['latest_enrollment'], 'start_date', None))
            if facts['first_overdue_date'] and facts['latest_enrollment'] else None,
            'paid_payment_count': facts['paid_payment_count'],
        },
        'operational_state': {
            'latest_enrollment_status': facts['latest_enrollment_status'],
            'latest_enrollment_start_date': facts['latest_enrollment_start_date'],
            'latest_enrollment_end_date': facts['latest_enrollment_end_date'],
            'latest_plan_name': getattr(getattr(latest_enrollment, 'plan', None), 'name', ''),
            'enrollment_status_change_count': len(facts['student_enrollments']),
            'reactivated_after_inactive': facts['reactivated_after_inactive'],
        },
        'communication_state': {
            'finance_touches_30d': facts['finance_touches_30d'],
            'last_finance_touch_at': facts['latest_finance_touch_at'],
            'last_finance_touch_action_kind': facts['latest_finance_touch_payload'].get('action_kind', ''),
        },
    }


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

    payments_by_student = _load_payments_by_student(payments=payments, student_ids=student_ids)
    enrollments_by_student = _load_enrollments_by_student(enrollments=enrollments, student_ids=student_ids)
    finance_messages_by_student = _load_finance_messages_by_student(student_ids=student_ids)

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

        facts = build_student_churn_facts(
            student=student,
            student_payments=student_payments,
            student_enrollments=student_enrollments,
            student_messages=student_messages,
            today=today,
        )
        facts['student_enrollments'] = student_enrollments

        recommendation_state = build_recommendation_state(
            actual_status=student.status,
            facts=facts,
            today=today,
            historical_score_map=historical_score_map,
            recommendation_timing_map=recommendation_timing_map,
            recommendation_timing_lookup_map=recommendation_timing_lookup_map,
            recommendation_override_map=recommendation_override_map,
            prediction_window_override_map=prediction_window_override_map,
            contextual_recommendation_map=contextual_recommendation_map,
            turn_priority_tension_context_map=turn_priority_tension_context_map,
        )

        _update_summary(
            summary,
            actual_status=student.status,
            signal_bucket=recommendation_state['signal_bucket'],
            finance_touches_30d=facts['finance_touches_30d'],
        )
        rows.append(
            _build_queue_row(
                student=student,
                facts=facts,
                recommendation_state=recommendation_state,
                today=today,
            )
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
