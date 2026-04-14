"""
ARQUIVO: carteira canonica da camada tradicional do snapshot financeiro.
"""

from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from finance.models import EnrollmentStatus, PaymentStatus


def build_plan_portfolio(plans, payments, enrollments):
    month_start = timezone.localdate().replace(day=1)
    payment_ids = list(payments.values_list('id', flat=True))
    enrollment_ids = list(enrollments.values_list('id', flat=True))
    return plans.annotate(
        active_enrollments=Count(
            'enrollments',
            filter=Q(enrollments__status=EnrollmentStatus.ACTIVE, enrollments__id__in=enrollment_ids or [-1]),
            distinct=True,
        ),
        pending_enrollments=Count(
            'enrollments',
            filter=Q(enrollments__status=EnrollmentStatus.PENDING, enrollments__id__in=enrollment_ids or [-1]),
            distinct=True,
        ),
        revenue_this_month=Coalesce(
            Sum(
                'enrollments__payments__amount',
                filter=Q(
                    enrollments__payments__status=PaymentStatus.PAID,
                    enrollments__payments__due_date__gte=month_start,
                    enrollments__payments__id__in=payment_ids or [-1],
                ),
            ),
            Decimal('0.00'),
        ),
    ).order_by('-active', 'price', 'name')


def build_plan_mix(plan_portfolio):
    total_revenue = sum(float(plan.revenue_this_month or 0) for plan in plan_portfolio) or 1
    mix = []
    for plan in plan_portfolio:
        revenue_this_month = float(plan.revenue_this_month or 0)
        mix.append(
            {
                'name': plan.name,
                'active_enrollments': plan.active_enrollments,
                'width': round((revenue_this_month / total_revenue) * 100, 1) if revenue_this_month else 6,
                'share': round((revenue_this_month / total_revenue) * 100, 1) if revenue_this_month else 0,
                'revenue_this_month': plan.revenue_this_month,
            }
        )
    return mix[:6]


__all__ = ['build_plan_mix', 'build_plan_portfolio']
