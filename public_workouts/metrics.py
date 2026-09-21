"""Cockpit deterministico do Curva: crescimento so avanca com operacao saudavel."""

from __future__ import annotations

import logging
import time
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Count, Min, Subquery, Sum
from django.utils import timezone

from .capacity import get_capacity_projection, get_tier_capacity
from .funnel_analytics import build_acquisition_report
from .models import (
    PublicWorkoutFunnelEvent,
    PublicWorkoutAcquisitionSession,
    PublicWorkoutCampaignSpend,
    PublicWorkoutLoadLog,
    PublicWorkoutMetricSnapshot,
    PublicWorkoutPayment,
    PublicWorkoutPaymentStatus,
    PublicWorkoutSubscription,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTier,
    PublicWorkoutWorkItem,
    PublicWorkoutWorkItemStatus,
)


FUNNEL_STEPS = (
    'landing_viewed', 'tier_selected', 'checkout_started',
    'checkout_authorized', 'invoice_paid', 'training_intake_completed',
    'program_published', 'program_opened',
)
logger = logging.getLogger(__name__)


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _percentile(values: list[int], percentile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * percentile)))
    return ordered[index]


def build_metrics_snapshot(*, at=None, window_days: int = 30) -> dict:
    at = at or timezone.now()
    since = at - timedelta(days=window_days)
    funnel_rows = PublicWorkoutFunnelEvent.objects.filter(
        occurred_at__gte=since, event_type__in=FUNNEL_STEPS,
    ).values('event_type').annotate(total=Count('id'))
    funnel = {step: 0 for step in FUNNEL_STEPS}
    funnel.update({row['event_type']: row['total'] for row in funnel_rows})
    acquisition = build_acquisition_report(at=at, window_days=window_days)
    acquisition_steps = acquisition['steps']
    funnel_rates = {
        'landing_to_tier': _ratio(acquisition_steps[1]['visitors'], acquisition['visitors']),
        'checkout_to_paid': _ratio(acquisition['paid'], acquisition_steps[2]['visitors']),
        'visitor_to_paid': _ratio(acquisition['paid'], acquisition['visitors']),
    }

    active = PublicWorkoutSubscription.objects.filter(status=PublicWorkoutSubscriptionStatus.ACTIVE)
    active_by_tier = {
        row['tier']: row['total'] for row in active.values('tier').annotate(total=Count('id'))
    }
    revenue = PublicWorkoutPayment.objects.filter(
        status=PublicWorkoutPaymentStatus.PAID, paid_at__gte=since,
    ).aggregate(gross=Sum('gross_amount'), net=Sum('net_amount'))
    tier_economics = {}
    for tier in PublicWorkoutTier.values:
        tier_payments = PublicWorkoutPayment.objects.filter(
            status=PublicWorkoutPaymentStatus.PAID,
            paid_at__gte=since,
            subscription__tier=tier,
        ).aggregate(gross=Sum('gross_amount'), net=Sum('net_amount'))
        effort_minutes = 0
        labor_cost = Decimal('0')
        completed_items = PublicWorkoutWorkItem.objects.filter(
            subscription__tier=tier,
            status=PublicWorkoutWorkItemStatus.DONE,
            completed_at__gte=since,
        ).select_related('assigned_to')
        for item in completed_items:
            minutes = item.actual_effort_minutes or item.estimated_effort_minutes
            effort_minutes += minutes
            if item.assigned_to_id:
                labor_cost += (Decimal(minutes) / Decimal('60')) * item.assigned_to.internal_hourly_cost
        net_revenue = tier_payments['net'] or Decimal('0')
        tier_economics[tier] = {
            'gross_revenue': str(tier_payments['gross'] or Decimal('0')),
            'net_revenue': str(net_revenue),
            'effort_minutes': effort_minutes,
            'labor_cost': str(labor_cost.quantize(Decimal('0.01'))),
            'contribution_after_labor': str((net_revenue - labor_cost).quantize(Decimal('0.01'))),
        }

    done = PublicWorkoutWorkItem.objects.filter(
        status=PublicWorkoutWorkItemStatus.DONE,
        completed_at__gte=since,
        started_at__isnull=False,
    ).values_list('started_at', 'completed_at', 'due_at')
    done_rows = list(done)
    lead_minutes = [
        max(0, int((completed - started).total_seconds() / 60))
        for started, completed, _due in done_rows
    ]
    on_time = sum(1 for _started, completed, due in done_rows if completed <= due)
    open_work = PublicWorkoutWorkItem.objects.filter(status__in=(
        PublicWorkoutWorkItemStatus.OPEN,
        PublicWorkoutWorkItemStatus.IN_PROGRESS,
        PublicWorkoutWorkItemStatus.BLOCKED,
    ))
    operations = {
        'open': open_work.count(),
        'overdue': open_work.filter(due_at__lt=at).count(),
        'blocked': open_work.filter(status=PublicWorkoutWorkItemStatus.BLOCKED).count(),
        'completion_minutes_p50': _percentile(lead_minutes, 0.50),
        'completion_minutes_p80': _percentile(lead_minutes, 0.80),
        'completed_on_time_rate': _ratio(on_time, len(done_rows)),
    }

    inactive_since = at - timedelta(days=14)
    recent_load_accounts = set(PublicWorkoutLoadLog.objects.filter(
        created_at__gte=inactive_since,
    ).values_list('account_id', flat=True))
    recent_open_accounts = set(PublicWorkoutFunnelEvent.objects.filter(
        event_type='program_opened', occurred_at__gte=inactive_since,
    ).values_list('account_id', flat=True))
    retention_buckets = {'healthy': 0, 'attention': 0, 'high_risk': 0}
    for subscription in active.only('account_id'):
        score = int(subscription.account_id not in recent_load_accounts) + int(
            subscription.account_id not in recent_open_accounts
        )
        retention_buckets[('healthy', 'attention', 'high_risk')[score]] += 1

    paid_events = PublicWorkoutFunnelEvent.objects.filter(
        occurred_at__gte=since, event_type='invoice_paid',
    )
    paid_event_count = paid_events.count()
    attributed_paid_event_count = paid_events.exclude(source='').count()
    first_payers = PublicWorkoutPayment.objects.filter(
        status__in=(PublicWorkoutPaymentStatus.PAID, PublicWorkoutPaymentStatus.REFUNDED),
        paid_at__lte=at, gross_amount__gt=0,
    ).values('subscription__account_id').annotate(first_paid=Min('paid_at')).filter(first_paid__gte=since)
    acquired = PublicWorkoutAcquisitionSession.objects.filter(
        account_id__in=Subquery(first_payers.values('subscription__account_id')),
    )
    sources = [
        {'source': row['first_source'], 'paid': row['paid']}
        for row in acquired.values('first_source').annotate(paid=Count('account_id', distinct=True)).order_by('-paid')[:10]
    ]
    paid_campaigns = {
        (row['first_source'], row['first_campaign']): row['paid']
        for row in acquired.values('first_source', 'first_campaign').annotate(paid=Count('account_id', distinct=True))
    }
    campaign_spend = {}
    for spend in PublicWorkoutCampaignSpend.objects.filter(
        starts_on__lte=at.date(), ends_on__gte=since.date(), currency='brl',
    ):
        item = campaign_spend.setdefault((spend.source, spend.campaign), {
            'amount': Decimal('0'), 'window_complete': True,
        })
        item['amount'] += spend.amount
        item['window_complete'] &= spend.starts_on >= since.date() and spend.ends_on <= at.date()
    campaign_economics = []
    for (source, campaign), spend in campaign_spend.items():
        paid = paid_campaigns.get((source, campaign), 0)
        campaign_economics.append({
            'source': source, 'campaign': campaign,
            'spend': str(spend['amount']), 'paid_customers': paid,
            'spend_window_complete': spend['window_complete'],
            'cac': str((spend['amount'] / paid).quantize(Decimal('0.01'))) if paid and spend['window_complete'] else None,
        })
    latest_paid_by_subscription = {}
    for payment in PublicWorkoutPayment.objects.filter(
        status=PublicWorkoutPaymentStatus.PAID,
    ).order_by('subscription_id', '-paid_at'):
        latest_paid_by_subscription.setdefault(payment.subscription_id, payment.gross_amount)
    mrr = sum(
        (latest_paid_by_subscription.get(subscription.pk, Decimal('0')) for subscription in active),
        Decimal('0'),
    )
    canceled = PublicWorkoutSubscription.objects.filter(canceled_at__gte=since)
    lost_mrr = sum(
        (latest_paid_by_subscription.get(subscription.pk, Decimal('0')) for subscription in canceled),
        Decimal('0'),
    )
    refunds = PublicWorkoutPayment.objects.filter(
        status=PublicWorkoutPaymentStatus.REFUNDED, updated_at__gte=since,
    ).aggregate(total=Sum('gross_amount'))['total'] or Decimal('0')
    capacity = {tier: get_tier_capacity(tier) for tier in PublicWorkoutTier.values}
    growth_blockers = []
    growth_warnings = []
    if operations['overdue']:
        growth_blockers.append('work_items_overdue')
    if any(item['configured'] and not item['raw_available'] for item in capacity.values()):
        growth_blockers.append('capacity_threshold_exceeded')
    if not all(item['configured'] for item in capacity.values()):
        growth_warnings.append('capacity_not_fully_configured')
    if funnel['landing_viewed'] < 30:
        growth_warnings.append('insufficient_funnel_sample')
    growth_status = 'red' if growth_blockers else ('yellow' if growth_warnings else 'green')
    return {
        'schema_version': 2,
        'generated_at': at.isoformat(),
        'window_days': window_days,
        'funnel': {'counts': funnel, 'counts_unit': 'raw_events', 'rates': funnel_rates,
                   'rates_unit': 'unique_visitors_7_day_cohort'},
        'acquisition': acquisition,
        'commercial': {
            'active_by_tier': active_by_tier,
            'gross_revenue': str(revenue['gross'] or Decimal('0')),
            'net_revenue': str(revenue['net'] or Decimal('0')),
            'paid_by_source': sources,
            'mrr_observed': str(mrr),
            'lost_mrr': str(lost_mrr),
            'canceled_customers': canceled.count(),
            'refunds': str(refunds),
            'attribution': {
                'paid_events': paid_event_count,
                'known_paid_events': attributed_paid_event_count,
                'known_paid_rate': _ratio(attributed_paid_event_count, paid_event_count),
            },
            'campaign_economics': campaign_economics,
            'tier_economics': tier_economics,
        },
        'operations': operations,
        'capacity': capacity,
        'capacity_projection': {
            '14_days': get_capacity_projection(days=14),
            '28_days': get_capacity_projection(days=28),
        },
        'retention': {'signal_window_days': 14, 'buckets': retention_buckets},
        'growth_gate': {
            'status': growth_status,
            'blockers': growth_blockers,
            'warnings': growth_warnings,
        },
    }


def capture_daily_metrics(*, at=None) -> PublicWorkoutMetricSnapshot:
    at = at or timezone.now()
    started_at = time.monotonic()
    payload = build_metrics_snapshot(at=at)
    snapshot, _created = PublicWorkoutMetricSnapshot.objects.update_or_create(
        metric_date=at.date(), schema_version=payload['schema_version'],
        defaults={'payload': payload},
    )
    duration_ms = round((time.monotonic() - started_at) * 1000)
    gate = payload['growth_gate']
    slow_threshold_ms = int(getattr(settings, 'PUBLIC_WORKOUT_METRICS_SLOW_MS', 5000))
    if duration_ms >= slow_threshold_ms:
        logger.warning(
            'curva_metrics_snapshot_slow snapshot_id=%s duration_ms=%s threshold_ms=%s',
            snapshot.pk, duration_ms, slow_threshold_ms,
        )
    log = logger.warning if gate['status'] == 'red' else logger.info
    log(
        'curva_metrics_snapshot snapshot_id=%s metric_date=%s gate=%s blockers=%s warnings=%s duration_ms=%s',
        snapshot.pk, snapshot.metric_date, gate['status'], gate['blockers'], gate['warnings'], duration_ms,
    )
    return snapshot


__all__ = ['build_metrics_snapshot', 'capture_daily_metrics']
