"""
ARQUIVO: trilha persistida de follow-up financeiro sugerido e realizado.

POR QUE ELE EXISTE:
- fecha o ciclo entre sugestao da fila e acao real do time para analytics e ML futuros.

O QUE ESTE ARQUIVO FAZ:
1. sincroniza sugestoes visiveis da fila em registros persistidos.
2. marca sugestoes realizadas quando a operacao executa o toque correspondente.
3. supersede sugestoes antigas quando a fila muda de leitura.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from finance.models import FinanceFollowUp, FinanceFollowUpOutcomeStatus, FinanceFollowUpStatus, PaymentStatus


ACTION_KIND_TO_RECOMMENDATIONS = {
    'overdue': {
        'send_financial_followup',
        'escalate_manual_retention',
        'monitor_and_nudge',
        'observe_payment_resolution',
    },
    'reactivation': {
        'review_winback',
        'monitor_recent_reactivation',
    },
}

RECOMMENDATION_OUTCOME_WINDOWS = {
    'review_winback': '30d',
    'monitor_recent_reactivation': '15d',
    'escalate_manual_retention': '7d',
    'send_financial_followup': '7d',
    'monitor_and_nudge': '15d',
    'observe_payment_resolution': '7d',
    'maintain_relationship': '30d',
}

RECOMMENDATION_TO_ACTION_KIND = {
    'review_winback': 'reactivation',
    'monitor_recent_reactivation': 'reactivation',
    'escalate_manual_retention': 'overdue',
    'send_financial_followup': 'overdue',
    'monitor_and_nudge': 'overdue',
    'observe_payment_resolution': 'overdue',
}


def build_finance_follow_up_suggestion_key(item):
    return ':'.join(
        [
            'finance-queue',
            str(item.get('student_id') or ''),
            str(item.get('payment_id') or ''),
            str(item.get('enrollment_id') or ''),
            str(item.get('recommended_action') or ''),
            str(item.get('rule_version') or ''),
        ]
    )


def _parse_outcome_window_days(value):
    normalized = (value or '').strip().lower()
    if normalized.endswith('d'):
        normalized = normalized[:-1]
    try:
        return max(int(normalized), 1)
    except (TypeError, ValueError):
        return 7


def _build_turn_priority_payload(*, items, turn_recommendation):
    queue_items = list(items or [])
    if not queue_items:
        return {}

    band_order = {'act_now': 0, 'act_with_caution': 1, 'observe_first': 2}
    sorted_items = sorted(
        queue_items,
        key=lambda item: (
            band_order.get((item.get('operational_band') or {}).get('level', 'observe_first'), 99),
            item.get('priority_rank', 999),
        ),
    )
    lead_level = (sorted_items[0].get('operational_band') or {}).get('level', 'observe_first')
    lead_items = [
        item for item in sorted_items if (item.get('operational_band') or {}).get('level', 'observe_first') == lead_level
    ]
    action_counts = {}
    for item in lead_items:
        recommended_action = item.get('recommended_action') or ''
        if not recommended_action:
            continue
        action_counts[recommended_action] = action_counts.get(recommended_action, 0) + 1
    dominant_action = ''
    if action_counts:
        dominant_action = max(action_counts.items(), key=lambda entry: (entry[1], entry[0]))[0]
    dominant_action_kind = RECOMMENDATION_TO_ACTION_KIND.get(dominant_action, '')
    global_action_kind = (turn_recommendation or {}).get('action_kind', '')
    alignment_status = 'unknown'
    if global_action_kind and dominant_action_kind:
        alignment_status = 'aligned' if global_action_kind == dominant_action_kind else 'tension'
    return {
        'lead_operational_band_level': lead_level,
        'dominant_action': dominant_action,
        'dominant_action_kind': dominant_action_kind,
        'global_action_kind': global_action_kind,
        'alignment_status': alignment_status,
    }


def sync_finance_follow_up_suggestions(*, items, source_surface='finance_queue', turn_recommendation=None):
    queue_items = list(items or [])
    if not queue_items:
        return 0

    now = timezone.now()
    suggestion_keys = set()
    student_ids = {item['student_id'] for item in queue_items}
    created_count = 0

    existing = FinanceFollowUp.objects.filter(
        student_id__in=student_ids,
        source_surface=source_surface,
        status=FinanceFollowUpStatus.SUGGESTED,
    )
    existing_by_key = {record.suggestion_key: record for record in existing}
    turn_priority_payload = _build_turn_priority_payload(items=queue_items, turn_recommendation=turn_recommendation)

    for item in queue_items:
        suggestion_key = build_finance_follow_up_suggestion_key(item)
        suggestion_keys.add(suggestion_key)
        if suggestion_key in existing_by_key:
            continue
        FinanceFollowUp.objects.create(
            student_id=item['student_id'],
            payment_id=item.get('payment_id'),
            enrollment_id=item.get('enrollment_id'),
            suggestion_key=suggestion_key,
            source_surface=source_surface,
            signal_bucket=item.get('signal_bucket', ''),
            recommended_action=item.get('recommended_action', ''),
            priority_rank=item.get('priority_rank', 0) or 0,
            confidence=item.get('confidence', ''),
            prediction_window=item.get('prediction_window', ''),
            rule_version=item.get('rule_version', ''),
            suggestion_window_stage=(item.get('recommendation_momentum') or {}).get('decay_stage', ''),
            suggestion_window_label=(item.get('recommendation_momentum') or {}).get('decay_label', ''),
            suggestion_window_age_days=(item.get('recommendation_momentum') or {}).get('window_age_days'),
            suggestion_queue_assist_score=Decimal(str(item.get('queue_assist_score', 0.0) or 0.0)),
            suggested_at=now,
            outcome_window=RECOMMENDATION_OUTCOME_WINDOWS.get(item.get('recommended_action', ''), '7d'),
            payload={
                'student_name': item.get('student_name', ''),
                'priority_label': item.get('priority_label', ''),
                'reason_codes': list(item.get('reason_codes') or []),
                'recommended_action': item.get('recommended_action', ''),
                'recommended_action_base': item.get('recommended_action_base', ''),
                'confidence': item.get('confidence', ''),
                'confidence_base': item.get('confidence_base', ''),
                'prediction_window': item.get('prediction_window', ''),
                'prediction_window_base': item.get('prediction_window_base', ''),
                'signal_bucket': item.get('signal_bucket', ''),
                'historical_score': item.get('historical_score', 0.0),
                'base_historical_score': item.get('base_historical_score', 0.0),
                'queue_assist_score': item.get('queue_assist_score', 0.0),
                'contextual_priority_score': item.get('contextual_priority_score', 0.0),
                'contextual_conviction': item.get('contextual_conviction', {}),
                'operational_band': item.get('operational_band', {}),
                'recommendation_momentum': item.get('recommendation_momentum', {}),
                'recommendation_adjustment': item.get('recommendation_adjustment', {}),
                'contextual_guidance': item.get('contextual_guidance', {}),
                'turn_priority_tension_guidance': item.get('turn_priority_tension_guidance', {}),
                'confidence_adjustment': item.get('confidence_adjustment', {}),
                'prediction_window_adjustment': item.get('prediction_window_adjustment', {}),
                'turn_recommendation': dict(turn_recommendation or {}),
                'turn_priority': dict(turn_priority_payload or {}),
            },
        )
        created_count += 1

    stale = existing.exclude(suggestion_key__in=suggestion_keys)
    stale.update(status=FinanceFollowUpStatus.SUPERSEDED, resolved_at=now)
    return created_count


def mark_finance_follow_up_realized(
    *,
    student_id,
    action_kind,
    actor_id=None,
    payment_id=None,
    enrollment_id=None,
    source_surface='finance_queue',
):
    recommended_actions = ACTION_KIND_TO_RECOMMENDATIONS.get(action_kind, set())
    if not recommended_actions:
        return 0

    queryset = FinanceFollowUp.objects.filter(
        student_id=student_id,
        source_surface=source_surface,
        status=FinanceFollowUpStatus.SUGGESTED,
        recommended_action__in=recommended_actions,
    )
    if payment_id is not None:
        queryset = queryset.filter(payment_id=payment_id)
    if enrollment_id is not None:
        queryset = queryset.filter(enrollment_id=enrollment_id)

    actor = None
    if actor_id is not None:
        actor = get_user_model().objects.filter(pk=actor_id).first()

    updated = 0
    now = timezone.now()
    for follow_up in queryset:
        follow_up.status = FinanceFollowUpStatus.REALIZED
        follow_up.resolved_at = now
        follow_up.resolved_by = actor
        follow_up.realized_action_kind = action_kind
        follow_up.outcome_status = FinanceFollowUpOutcomeStatus.PENDING
        follow_up.outcome_checked_at = now
        follow_up.outcome_reason = ''
        follow_up.save(
            update_fields=[
                'status',
                'resolved_at',
                'resolved_by',
                'realized_action_kind',
                'outcome_status',
                'outcome_checked_at',
                'outcome_reason',
                'updated_at',
            ]
        )
        updated += 1
    return updated


def evaluate_finance_follow_up_outcome(*, follow_up_id):
    follow_up = (
        FinanceFollowUp.objects.select_related('student', 'payment', 'enrollment')
        .get(pk=follow_up_id)
    )
    now = timezone.now()

    outcome_status = FinanceFollowUpOutcomeStatus.PENDING
    outcome_reason = 'awaiting_window'

    if follow_up.recommended_action == 'review_winback' and follow_up.student.status == 'active':
        outcome_status = FinanceFollowUpOutcomeStatus.SUCCEEDED
        outcome_reason = 'student_reactivated'
    elif follow_up.recommended_action == 'review_winback' and follow_up.student.status == 'inactive':
        outcome_status = FinanceFollowUpOutcomeStatus.FAILED
        outcome_reason = 'student_still_inactive'
    elif follow_up.payment_id and follow_up.payment and follow_up.payment.status == PaymentStatus.PAID:
        outcome_status = FinanceFollowUpOutcomeStatus.SUCCEEDED
        outcome_reason = 'payment_recovered'
    elif follow_up.payment_id and follow_up.payment and follow_up.payment.status in {PaymentStatus.PENDING, PaymentStatus.OVERDUE}:
        outcome_status = FinanceFollowUpOutcomeStatus.FAILED
        outcome_reason = 'still_overdue'

    follow_up.outcome_status = outcome_status
    follow_up.outcome_checked_at = now
    follow_up.outcome_reason = outcome_reason
    follow_up.save(update_fields=['outcome_status', 'outcome_checked_at', 'outcome_reason', 'updated_at'])
    return follow_up


def evaluate_pending_finance_follow_ups(*, window=None, limit=None, now=None):
    reference_now = now or timezone.now()
    queryset = FinanceFollowUp.objects.select_related('student', 'payment', 'enrollment').filter(
        status=FinanceFollowUpStatus.REALIZED,
        outcome_status=FinanceFollowUpOutcomeStatus.PENDING,
    )
    if window:
        queryset = queryset.filter(outcome_window=window)

    evaluated = 0
    for follow_up in queryset.order_by('resolved_at', 'id'):
        days_required = _parse_outcome_window_days(follow_up.outcome_window)
        resolved_at = follow_up.resolved_at or follow_up.suggested_at
        if resolved_at is None:
            continue
        if reference_now < resolved_at + timezone.timedelta(days=days_required):
            continue
        evaluate_finance_follow_up_outcome(follow_up_id=follow_up.id)
        evaluated += 1
        if limit is not None and evaluated >= limit:
            break
    return evaluated


__all__ = [
    'ACTION_KIND_TO_RECOMMENDATIONS',
    'RECOMMENDATION_OUTCOME_WINDOWS',
    'RECOMMENDATION_TO_ACTION_KIND',
    'build_finance_follow_up_suggestion_key',
    'evaluate_finance_follow_up_outcome',
    'evaluate_pending_finance_follow_ups',
    'mark_finance_follow_up_realized',
    'sync_finance_follow_up_suggestions',
]
