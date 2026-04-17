"""
ARQUIVO: comparativos canonicos da camada tradicional do snapshot financeiro.
"""

from calendar import month_abbr
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.db.models.functions import TruncMonth
from django.utils import timezone

from finance.models import Enrollment, EnrollmentStatus, Payment, PaymentStatus

from .base import shift_month

PT_MONTH_ABBR = {
    1: 'Jan',
    2: 'Fev',
    3: 'Mar',
    4: 'Abr',
    5: 'Mai',
    6: 'Jun',
    7: 'Jul',
    8: 'Ago',
    9: 'Set',
    10: 'Out',
    11: 'Nov',
    12: 'Dez',
}


def _normalize_month_bucket(value):
    if value is None:
        return None
    if hasattr(value, 'date'):
        value = value.date()
    return value.replace(day=1)


def build_monthly_comparison(months, selected_plan, payment_status, payment_method):
    series = []
    month_anchor = timezone.localdate().replace(day=1)
    first_month_start = shift_month(month_anchor, -(months - 1))
    last_month_end = shift_month(month_anchor, 1) - timezone.timedelta(days=1)

    revenue_payments = Payment.objects.filter(
        status=PaymentStatus.PAID,
        due_date__gte=first_month_start,
        due_date__lte=last_month_end,
    )
    if selected_plan is not None:
        revenue_payments = revenue_payments.filter(enrollment__plan=selected_plan)
    if payment_method:
        revenue_payments = revenue_payments.filter(method=payment_method)
    if payment_status:
        revenue_payments = revenue_payments.filter(status=payment_status)
    revenue_by_month = {
        _normalize_month_bucket(item['month']): item['total']
        for item in revenue_payments.annotate(month=TruncMonth('due_date'))
        .values('month')
        .annotate(total=Coalesce(Sum('amount'), Decimal('0.00')))
    }

    activations_query = Enrollment.objects.filter(
        status=EnrollmentStatus.ACTIVE,
        start_date__gte=first_month_start,
        start_date__lte=last_month_end,
    )
    cancellations_query = Enrollment.objects.filter(
        status=EnrollmentStatus.CANCELED,
        updated_at__date__gte=first_month_start,
        updated_at__date__lte=last_month_end,
    )
    if selected_plan is not None:
        activations_query = activations_query.filter(plan=selected_plan)
        cancellations_query = cancellations_query.filter(plan=selected_plan)

    activations_by_month = {
        _normalize_month_bucket(item['month']): {
            'count': item['count'],
            'total': item['total'],
        }
        for item in activations_query.annotate(month=TruncMonth('start_date'))
        .values('month')
        .annotate(
            count=Count('id'),
            total=Coalesce(Sum('plan__price'), Decimal('0.00')),
        )
    }
    cancellations_by_month = {
        _normalize_month_bucket(item['month']): {
            'count': item['count'],
            'total': item['total'],
        }
        for item in cancellations_query.annotate(month=TruncMonth('updated_at'))
        .values('month')
        .annotate(
            count=Count('id'),
            total=Coalesce(Sum('plan__price'), Decimal('0.00')),
        )
    }

    for offset in range(months - 1, -1, -1):
        start_date = shift_month(month_anchor, -offset)
        revenue = revenue_by_month.get(start_date, Decimal('0.00'))
        activation_summary = activations_by_month.get(start_date, {})
        cancellation_summary = cancellations_by_month.get(start_date, {})
        activations = activation_summary.get('count', 0)
        cancellations = cancellation_summary.get('count', 0)
        activations_amount = activation_summary.get('total', Decimal('0.00'))
        cancellations_amount = cancellation_summary.get('total', Decimal('0.00'))
        series.append(
            {
                'label': f'{month_abbr[start_date.month].upper()}/{str(start_date.year)[-2:]}',
                'short_label': PT_MONTH_ABBR[start_date.month],
                'revenue': revenue,
                'activations': activations,
                'activations_amount': activations_amount,
                'cancellations': cancellations,
                'cancellations_amount': cancellations_amount,
                'net_growth': activations - cancellations,
            }
        )

    for index, item in enumerate(series):
        history = [entry['revenue'] for entry in series[max(0, index - 3):index]]
        if history:
            expected_revenue = sum(history, Decimal('0.00')) / Decimal(len(history))
        else:
            expected_revenue = item['revenue']
        item['expected_revenue'] = expected_revenue.quantize(Decimal('0.01'))

    return series


def build_comparison_peaks(series):
    max_revenue = max(
        (
            max(item['revenue'], item.get('expected_revenue', Decimal('0.00')))
            for item in series
        ),
        default=Decimal('0.00'),
    )
    max_count = max((max(item['activations'], item['cancellations']) for item in series), default=0)
    return {
        'max_revenue': max_revenue or Decimal('1.00'),
        'max_count': max_count or 1,
    }


__all__ = ['build_comparison_peaks', 'build_monthly_comparison']
