"""Avaliação reproduzível do gate operacional para escalar aquisição Curva.

Lê somente snapshots diários; nunca muda assinatura, capacidade ou orçamento.
"""

from __future__ import annotations

from datetime import date, timedelta

from django.conf import settings
from django.utils import timezone

from .models import PublicWorkoutMetricSnapshot


def _snapshot_by_date(*, start: date, end: date) -> dict[date, PublicWorkoutMetricSnapshot]:
    snapshots = PublicWorkoutMetricSnapshot.objects.filter(
        metric_date__gte=start, metric_date__lte=end,
    ).order_by('metric_date', '-captured_at')
    latest = {}
    for snapshot in snapshots:
        latest.setdefault(snapshot.metric_date, snapshot)
    return latest


def evaluate_growth_readiness(*, as_of: date | None = None, observation_days: int = 28,
                              consecutive_green_days: int = 14) -> dict:
    """Devolve evidência e motivos, sem transformar amostra insuficiente em verde."""
    if observation_days < consecutive_green_days or consecutive_green_days < 1:
        raise ValueError('observation_days deve ser maior ou igual a consecutive_green_days >= 1')
    as_of = as_of or timezone.localdate()
    start = as_of - timedelta(days=observation_days - 1)
    expected_dates = [start + timedelta(days=offset) for offset in range(observation_days)]
    snapshots = _snapshot_by_date(start=start, end=as_of)
    missing_dates = [item.isoformat() for item in expected_dates if item not in snapshots]
    latest = snapshots.get(as_of)
    blockers = []

    if missing_dates:
        blockers.append('missing_daily_snapshots')

    green_start = as_of - timedelta(days=consecutive_green_days - 1)
    green_dates = [green_start + timedelta(days=offset) for offset in range(consecutive_green_days)]
    non_green_dates = [
        item.isoformat() for item in green_dates
        if item not in snapshots
        or (snapshots[item].payload or {}).get('growth_gate', {}).get('status') != 'green'
    ]
    if non_green_dates:
        blockers.append('growth_gate_not_green_for_required_window')

    latest_payload = latest.payload if latest else {}
    operations = latest_payload.get('operations', {})
    commercial = latest_payload.get('commercial', {})
    slo_rate = operations.get('completed_on_time_rate')
    required_slo = float(getattr(settings, 'PUBLIC_WORKOUT_GROWTH_MIN_SLO_RATE', 0.95))
    if slo_rate is None:
        blockers.append('slo_sample_unavailable')
    elif slo_rate < required_slo:
        blockers.append('slo_below_threshold')

    attribution = commercial.get('attribution', {})
    attribution_rate = attribution.get('known_paid_rate')
    required_attribution = float(getattr(settings, 'PUBLIC_WORKOUT_GROWTH_MIN_ATTRIBUTION_RATE', 0.70))
    if attribution_rate is None:
        blockers.append('attribution_sample_unavailable')
    elif attribution_rate < required_attribution:
        blockers.append('attribution_below_threshold')

    return {
        'ready_to_scale': not blockers,
        'as_of': as_of.isoformat(),
        'observation_days_required': observation_days,
        'consecutive_green_days_required': consecutive_green_days,
        'snapshot_days_found': len(snapshots),
        'missing_snapshot_dates': missing_dates,
        'non_green_dates': non_green_dates,
        'latest_growth_gate': latest_payload.get('growth_gate', {}).get('status'),
        'slo': {'actual': slo_rate, 'minimum': required_slo},
        'attribution': {'actual': attribution_rate, 'minimum': required_attribution},
        'blockers': blockers,
    }


__all__ = ['evaluate_growth_readiness']
