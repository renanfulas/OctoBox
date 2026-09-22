"""Stable experiment assignment and read-only outcome analysis for Curva."""

from __future__ import annotations

import hashlib
import math
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import OuterRef, Q, Subquery
from django.utils import timezone

from .models import (
    PublicWorkoutExperiment,
    PublicWorkoutExperimentAssignment,
    PublicWorkoutExperimentStatus,
    PublicWorkoutPayment,
    PublicWorkoutPaymentStatus,
)


def _select_variant(experiment, variants, acquisition_session):
    total_weight = sum(variant.allocation_weight for variant in variants)
    digest = hashlib.sha256(
        f'{experiment.pk}:{acquisition_session.pk}'.encode('ascii')
    ).digest()
    bucket = int.from_bytes(digest[:8], 'big') % total_weight
    cursor = 0
    for variant in variants:
        cursor += variant.allocation_weight
        if bucket < cursor:
            return variant
    return variants[-1]


def active_experiments(*, at=None):
    at = at or timezone.now()
    return PublicWorkoutExperiment.objects.filter(
        status=PublicWorkoutExperimentStatus.RUNNING,
    ).filter(
        Q(starts_at__isnull=True) | Q(starts_at__lte=at),
        Q(ends_at__isnull=True) | Q(ends_at__gt=at),
    ).prefetch_related('variants')


def assign_active_experiments(acquisition_session, *, at=None):
    """Assign every active experiment once; deterministic choice survives races."""
    if acquisition_session is None:
        return []
    at = at or timezone.now()
    assignments = []
    for experiment in active_experiments(at=at):
        existing = PublicWorkoutExperimentAssignment.objects.filter(
            experiment=experiment, acquisition_session=acquisition_session,
        ).select_related('experiment', 'variant').first()
        if existing:
            assignments.append(existing)
            continue
        variants = [variant for variant in experiment.variants.all() if variant.is_active]
        if len(variants) < 2:
            continue
        selected = _select_variant(experiment, variants, acquisition_session)
        try:
            with transaction.atomic():
                assignment, _created = PublicWorkoutExperimentAssignment.objects.get_or_create(
                    experiment=experiment,
                    acquisition_session=acquisition_session,
                    defaults={'variant': selected, 'assigned_at': at},
                )
        except IntegrityError:
            assignment = PublicWorkoutExperimentAssignment.objects.get(
                experiment=experiment, acquisition_session=acquisition_session,
            )
        assignments.append(assignment)
    return assignments


def serialize_assignments(assignments):
    return [
        {
            'experiment': assignment.experiment.key,
            'variant': assignment.variant.key,
            'payload': assignment.variant.payload,
        }
        for assignment in assignments
    ]


def _percent(value, total):
    return round(100 * value / total, 2) if total else None


def _wilson_interval(successes, total, z=1.959963984540054):
    if not total:
        return None, None
    ratio = successes / total
    denominator = 1 + z * z / total
    center = (ratio + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((ratio * (1 - ratio) + z * z / (4 * total)) / total) / denominator
    return round(100 * max(0, center - margin), 2), round(100 * min(1, center + margin), 2)


def build_experiment_report(*, at=None, window_days=90):
    """Variant outcomes based on assignment time and confirmed first payment."""
    at = at or timezone.now()
    since = at - timedelta(days=window_days)
    positive_payments = PublicWorkoutPayment.objects.filter(
        paid_at__isnull=False, paid_at__lte=at, gross_amount__gt=0,
        status__in=(PublicWorkoutPaymentStatus.PAID, PublicWorkoutPaymentStatus.REFUNDED),
        subscription__account_id=OuterRef('acquisition_session__account_id'),
    ).order_by('paid_at', 'pk')
    experiments = []
    queryset = PublicWorkoutExperiment.objects.prefetch_related('variants').order_by('-created_at')
    for experiment in queryset:
        assignments = PublicWorkoutExperimentAssignment.objects.filter(
            experiment=experiment, assigned_at__gte=since, assigned_at__lte=at,
        ).select_related('variant').annotate(
            first_paid_at=Subquery(positive_payments.values('paid_at')[:1]),
        )
        variant_data = {
            variant.pk: {
                'key': variant.key,
                'name': variant.name,
                'is_active': variant.is_active,
                'assigned': 0,
                'mature_visitors': 0,
                'paid': 0,
                'mature_paid': 0,
            }
            for variant in experiment.variants.all()
        }
        excluded_existing_customers = 0
        for assignment in assignments.iterator(chunk_size=1000):
            item = variant_data.get(assignment.variant_id)
            if item is None:
                continue
            deadline = assignment.assigned_at + timedelta(days=experiment.conversion_days)
            mature = deadline <= at
            paid_at = assignment.first_paid_at
            if paid_at is not None and paid_at < assignment.assigned_at:
                excluded_existing_customers += 1
                continue
            paid = paid_at is not None and assignment.assigned_at <= paid_at <= min(at, deadline)
            item['assigned'] += 1
            item['mature_visitors'] += int(mature)
            item['paid'] += int(paid)
            item['mature_paid'] += int(mature and paid)
        rows = []
        for item in variant_data.values():
            if not item['is_active'] and not item['assigned']:
                continue
            low, high = _wilson_interval(item['mature_paid'], item['mature_visitors'])
            rows.append({
                **item,
                'conversion_percent': _percent(item['paid'], item['assigned']),
                'mature_conversion_percent': _percent(item['mature_paid'], item['mature_visitors']),
                'confidence_low_percent': low,
                'confidence_high_percent': high,
            })
            rows[-1].pop('is_active')
        rows.sort(key=lambda row: (-(row['mature_conversion_percent'] or -1), row['key']))
        eligible = [row for row in rows if row['mature_visitors'] >= experiment.minimum_sample_size]
        decision = 'collecting'
        candidate = None
        if len(eligible) == len(rows) and len(rows) >= 2:
            candidate = rows[0]
            runner_up = rows[1]
            decision = 'leader' if (
                candidate['confidence_low_percent'] is not None
                and runner_up['confidence_high_percent'] is not None
                and candidate['confidence_low_percent'] > runner_up['confidence_high_percent']
            ) else 'inconclusive'
        experiments.append({
            'key': experiment.key,
            'name': experiment.name,
            'hypothesis': experiment.hypothesis,
            'status': experiment.status,
            'conversion_days': experiment.conversion_days,
            'minimum_sample_size': experiment.minimum_sample_size,
            'decision': decision,
            'candidate_variant': candidate['key'] if candidate and decision == 'leader' else None,
            'excluded_existing_customers': excluded_existing_customers,
            'variants': rows,
        })
    return {'window_days': window_days, 'experiments': experiments}


__all__ = [
    'active_experiments', 'assign_active_experiments', 'build_experiment_report',
    'serialize_assignments',
]
