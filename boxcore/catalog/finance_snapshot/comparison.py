"""
ARQUIVO: serie historica do snapshot financeiro.

POR QUE ELE EXISTE:
- Separa comparativos mensais e picos usados pelos graficos do financeiro.

O QUE ESTE ARQUIVO FAZ:
1. Monta a serie mensal de receita, ativacoes e cancelamentos.
2. Calcula os picos para escala visual dos graficos.

PONTOS CRITICOS:
- Alteracoes aqui afetam tendencias e comparativos da central financeira.
"""

from calendar import month_abbr
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from finance.models import Enrollment, EnrollmentStatus, Payment, PaymentStatus

from .base import shift_month


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
        series.append(
            {
                'label': f'{month_abbr[start_date.month].upper()}/{str(start_date.year)[-2:]}',
                'revenue': revenue,
                'activations': activations,
                'cancellations': cancellations,
                'net_growth': activations - cancellations,
            }
        )
    return series


def build_comparison_peaks(series):
    max_revenue = max((item['revenue'] for item in series), default=Decimal('0.00'))
    max_count = max((max(item['activations'], item['cancellations']) for item in series), default=0)
    return {
        'max_revenue': max_revenue or Decimal('1.00'),
        'max_count': max_count or 1,
    }


__all__ = ['build_comparison_peaks', 'build_monthly_comparison']