"""Tenant-local query adapter for versioned student activation cohorts."""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Min
from django.utils import timezone

from student_app.models import StudentJourneyMilestone

from ..domain.cohort_contracts import COHORT_DEFINITIONS, calculate_student_cohort_report


def build_activation_cohort_reports(*, now=None) -> list[dict]:
    now = now or timezone.now()
    cutoff = now - timedelta(hours=48)
    lookback = cutoff - timedelta(days=90)
    starts_qs = StudentJourneyMilestone.objects.filter(
        milestone__in=('invite_created', 'link_created'),
        contract_version=1,
        occurred_at__gte=lookback,
        occurred_at__lte=cutoff,
    ).order_by('occurred_at', 'id')
    activations = list(
        StudentJourneyMilestone.objects.filter(
            milestone='app_entry_completed',
            contract_version=1,
            occurred_at__gte=lookback,
            occurred_at__lte=cutoff,
        ).order_by('occurred_at', 'id')
    )
    starts = list(starts_qs)
    identity_ids = {row.identity_id for row in activations if row.identity_id}
    return_rows = []
    if identity_ids:
        return_rows = list(
            StudentJourneyMilestone.objects.filter(
                journey='',
                milestone='authenticated_return',
                contract_version=1,
                identity_id__in=identity_ids,
                occurred_at__gte=lookback,
                occurred_at__lte=cutoff,
            )
            .order_by()
            .values_list('identity_id', 'occurred_at')
            .distinct()
        )

    coverage_start = StudentJourneyMilestone.objects.filter(contract_version=1).aggregate(
        first_recorded=Min('created_at'),
    )['first_recorded']
    reports = []
    for definition in COHORT_DEFINITIONS:
        definition_starts = [
            row for row in starts
            if row.journey == definition.journey
            and row.milestone == definition.start_milestone
            and row.cohort_kind == definition.cohort_kind
        ]
        report = calculate_student_cohort_report(
                definition=definition,
                starts=definition_starts,
                activations=activations,
                returns=return_rows,
                now=now,
                coverage_start=coverage_start,
            )
        report['cohort_unit_label'] = 'link do grupo' if definition.cohort_kind == 'invite_link' else 'convite individual'
        report['activation_rate_label'] = (
            f"{report['activation_rate']:.1f}%" if report['activation_rate'] is not None else 'Sem coorte madura'
        )
        report['retention_rate_label'] = (
            f"{report['retention_rate']:.1f}%" if report['retention_rate'] is not None else 'Sem ativados maduros'
        )
        report['maturity_label'] = {
            'ready': 'Janelas maduras',
            'warming_up': 'Aguardando D14',
            'collecting': 'Coleta iniciando',
        }[report['maturity']]
        reports.append(report)
    return reports


__all__ = ['build_activation_cohort_reports']
