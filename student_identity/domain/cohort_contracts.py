"""Pure contract and calculation for student activation cohorts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone as datetime_timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class StudentCohortDefinition:
    contract_version: int
    journey: str
    cohort_kind: str
    start_milestone: str
    activation_milestone: str = 'app_entry_completed'
    activation_days: int = 7
    retention_start_day: int = 7
    retention_days: int = 7
    data_lateness_hours: int = 48
    lookback_days: int = 90


COHORT_DEFINITIONS = (
    StudentCohortDefinition(1, 'mass_box_invite', 'invite_link', 'link_created'),
    StudentCohortDefinition(1, 'imported_lead_invite', 'invitation', 'invite_created'),
    StudentCohortDefinition(1, 'registered_student_invite', 'invitation', 'invite_created'),
)

RETURN_ACTIVITY_KINDS = frozenset({'wod_viewed', 'rm_created', 'rm_updated'})


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, TypeError):
        return ZoneInfo('UTC')


def _as_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=datetime_timezone.utc)
    return value


def _start_day(row) -> date:
    return _as_aware(row.occurred_at).astimezone(_zone(row.timezone_name)).date()


def calculate_student_cohort_report(
    *,
    definition: StudentCohortDefinition,
    starts,
    activations,
    returns,
    now: datetime,
    coverage_start: datetime | None,
) -> dict:
    """Aggregate deduped cohort facts without ORM or framework dependencies.

    `returns` is an iterable of `(identity_id, occurred_at)` pairs from real
    authenticated app activity. Anonymous traffic and staff actions cannot
    produce a retained cohort.
    """
    now = _as_aware(now)
    data_cutoff = now - timedelta(hours=definition.data_lateness_hours)
    lookback_start = data_cutoff - timedelta(days=definition.lookback_days)
    cohort_starts = [
        row for row in starts
        if _as_aware(row.occurred_at) >= lookback_start
        and _as_aware(row.occurred_at) <= data_cutoff
        and row.contract_version == definition.contract_version
    ]

    activation_by_cohort: dict[tuple[str, str], list] = {}
    for row in activations:
        if row.journey != definition.journey or row.milestone != definition.activation_milestone:
            continue
        if row.cohort_kind != definition.cohort_kind or row.contract_version != definition.contract_version:
            continue
        if _as_aware(row.occurred_at) > data_cutoff:
            continue
        activation_by_cohort.setdefault((row.cohort_kind, row.cohort_key), []).append(row)

    returns_by_identity: dict[int, list[datetime]] = {}
    for identity_id, occurred_at in returns:
        occurred_at = _as_aware(occurred_at)
        if identity_id and occurred_at <= data_cutoff:
            returns_by_identity.setdefault(int(identity_id), []).append(occurred_at)

    eligible = activated = retained = immature = 0
    for start in cohort_starts:
        tz = _zone(start.timezone_name)
        start_day = _start_day(start)
        maturity_at = datetime.combine(
            start_day + timedelta(days=definition.retention_start_day + definition.retention_days),
            time.min,
            tzinfo=tz,
        )
        if data_cutoff < maturity_at:
            immature += 1
            continue

        eligible += 1
        cohort_activations = activation_by_cohort.get((start.cohort_kind, start.cohort_key), ())
        activated_identities = set()
        activation_start = _as_aware(start.occurred_at)
        activation_end = datetime.combine(
            start_day + timedelta(days=definition.activation_days),
            time.min,
            tzinfo=tz,
        )
        for activation in cohort_activations:
            if not activation.identity_id:
                continue
            activation_at = _as_aware(activation.occurred_at)
            if activation_start <= activation_at < activation_end:
                activated_identities.add(int(activation.identity_id))
        if not activated_identities:
            continue

        activated += 1
        retention_start = start_day + timedelta(days=definition.retention_start_day)
        retention_end = retention_start + timedelta(days=definition.retention_days)
        has_return = any(
            retention_start <= occurred_at.astimezone(tz).date() < retention_end
            for identity_id in activated_identities
            for occurred_at in returns_by_identity.get(identity_id, ())
        )
        if has_return:
            retained += 1

    def rate(numerator: int, denominator: int) -> float | None:
        return round(numerator * 100 / denominator, 1) if denominator else None

    maturity = 'ready' if eligible else 'warming_up' if cohort_starts else 'collecting'
    return {
        'contract_version': definition.contract_version,
        'journey': definition.journey,
        'cohort_unit': definition.cohort_kind,
        'eligible_count': eligible,
        'activated_count': activated,
        'retained_count': retained,
        'immature_count': immature,
        'activation_rate': rate(activated, eligible),
        'retention_rate': rate(retained, activated),
        'maturity': maturity,
        'coverage_start': coverage_start,
        'data_cutoff': data_cutoff,
        'activation_window_label': 'D0–D6',
        'retention_window_label': 'D7–D13',
        'data_lateness_hours': definition.data_lateness_hours,
        'lookback_days': definition.lookback_days,
    }


__all__ = [
    'COHORT_DEFINITIONS',
    'RETURN_ACTIVITY_KINDS',
    'StudentCohortDefinition',
    'calculate_student_cohort_report',
]
