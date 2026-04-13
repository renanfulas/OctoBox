"""
ARQUIVO: comparativos canonicos da camada tradicional do snapshot financeiro.
"""

from calendar import month_abbr
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce
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


def build_monthly_comparison(months, selected_plan, payment_status, payment_method):
    series = []
    month_anchor = timezone.localdate().replace(day=1)

    for offset in range(months - 1, -1, -1):
        start_date = shift_month(month_anchor, -offset)
        end_date = shift_month(start_date, 1) - timezone.timedelta(days=1)
        revenue_payments = Payment.objects.filter(
            status=PaymentStatus.PAID,
            due_date__gte=start_date,
            due_date__lte=end_date,
        )
        if selected_plan is not None:
            revenue_payments = revenue_payments.filter(enrollment__plan=selected_plan)
        if payment_method:
            revenue_payments = revenue_payments.filter(method=payment_method)
        if payment_status:
            revenue_payments = revenue_payments.filter(status=payment_status)
        revenue = revenue_payments.aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']

        activations_query = Enrollment.objects.filter(
            status=EnrollmentStatus.ACTIVE,
            start_date__gte=start_date,
            start_date__lte=end_date,
        )
        cancellations_query = Enrollment.objects.filter(
            status=EnrollmentStatus.CANCELED,
            updated_at__date__gte=start_date,
            updated_at__date__lte=end_date,
        )
        if selected_plan is not None:
            activations_query = activations_query.filter(plan=selected_plan)
            cancellations_query = cancellations_query.filter(plan=selected_plan)
        activations = activations_query.count()
        cancellations = cancellations_query.count()
        activations_amount = activations_query.aggregate(
            total=Coalesce(Sum('plan__price'), Decimal('0.00'))
        )['total']
        cancellations_amount = cancellations_query.aggregate(
            total=Coalesce(Sum('plan__price'), Decimal('0.00'))
        )['total']
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
