"""
ARQUIVO: queries de financeiro do catalogo.

POR QUE ELE EXISTE:
- Centraliza leituras, filtros e agregacoes da central financeira.

O QUE ESTE ARQUIVO FAZ:
1. Monta o snapshot financeiro com filtros, portfolio, mix e comparativos.
2. Reaproveita consultas entre tela e exportacoes.

PONTOS CRITICOS:
- Mudancas aqui afetam indicadores, filtros, exportacoes e leitura gerencial do produto.
"""

from calendar import month_abbr
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from boxcore.models import Enrollment, EnrollmentStatus, MembershipPlan, Payment, PaymentStatus

from .forms import FinanceFilterForm


def shift_month(source_date, month_delta):
    month_index = source_date.month - 1 + month_delta
    year = source_date.year + month_index // 12
    month = month_index % 12 + 1
    return source_date.replace(year=year, month=month, day=1)


def _get_finance_filter_values(filter_form):
    months = 6
    selected_plan = None
    payment_status = ''
    payment_method = ''
    if filter_form.is_valid():
        months = int(filter_form.cleaned_data.get('months') or 6)
        selected_plan = filter_form.cleaned_data.get('plan')
        payment_status = filter_form.cleaned_data.get('payment_status') or ''
        payment_method = filter_form.cleaned_data.get('payment_method') or ''
    return months, selected_plan, payment_status, payment_method


def _build_finance_base(filter_form):
    months, selected_plan, payment_status, payment_method = _get_finance_filter_values(filter_form)
    start_date = shift_month(timezone.localdate().replace(day=1), -(months - 1))
    payments = Payment.objects.select_related('student', 'enrollment__plan').filter(due_date__gte=start_date)
    enrollments = Enrollment.objects.select_related('student', 'plan').filter(start_date__gte=start_date)
    plans = MembershipPlan.objects.all()

    if selected_plan is not None:
        payments = payments.filter(enrollment__plan=selected_plan)
        enrollments = enrollments.filter(plan=selected_plan)
        plans = plans.filter(pk=selected_plan.id)
    if payment_status:
        payments = payments.filter(status=payment_status)
    if payment_method:
        payments = payments.filter(method=payment_method)

    return {
        'months': months,
        'selected_plan': selected_plan,
        'payment_status': payment_status,
        'payment_method': payment_method,
        'start_date': start_date,
        'payments': payments,
        'enrollments': enrollments,
        'plans': plans,
    }


def _build_finance_metrics(payments, enrollments):
    today = timezone.localdate()
    month_start = today.replace(day=1)
    previous_month_end = month_start - timezone.timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)

    revenue_this_month = payments.filter(
        status=PaymentStatus.PAID,
        due_date__gte=month_start,
    ).aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']
    revenue_previous_month = Payment.objects.filter(
        status=PaymentStatus.PAID,
        due_date__gte=previous_month_start,
        due_date__lte=previous_month_end,
    ).aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']
    open_revenue = payments.filter(
        status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
    ).aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']
    paid_count = payments.filter(status=PaymentStatus.PAID, due_date__gte=month_start).count()
    active_growth = enrollments.filter(
        status=EnrollmentStatus.ACTIVE,
        start_date__gte=month_start,
    ).count()
    cancellations = enrollments.filter(
        status=EnrollmentStatus.CANCELED,
        updated_at__date__gte=month_start,
    ).count()
    overdue_students = payments.filter(status=PaymentStatus.OVERDUE).values('student_id').distinct().count()

    return {
        'faturamento_mes': {
            'value': revenue_this_month,
            'note': f'Mes anterior: R$ {revenue_previous_month}',
        },
        'receita_em_aberto': {
            'value': open_revenue,
            'note': 'Soma de pagamentos pendentes e atrasados.',
        },
        'novos_ativos_mes': {
            'value': active_growth,
            'note': 'Matriculas ativas iniciadas neste mes.',
        },
        'cancelamentos_mes': {
            'value': cancellations,
            'note': 'Matriculas canceladas registradas neste mes.',
        },
        'ticket_medio_pago': {
            'value': revenue_this_month / paid_count if paid_count else Decimal('0.00'),
            'note': 'Media dos pagamentos efetivamente recebidos no mes.',
        },
        'alunos_em_atraso': {
            'value': overdue_students,
            'note': 'Quantidade de alunos com pagamento vencido.',
        },
    }


def _build_plan_portfolio(plans, payments, enrollments):
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


def _build_plan_mix(plan_portfolio):
    total_active = sum(plan.active_enrollments for plan in plan_portfolio) or 1
    mix = []
    for plan in plan_portfolio:
        mix.append(
            {
                'name': plan.name,
                'active_enrollments': plan.active_enrollments,
                'width': round((plan.active_enrollments / total_active) * 100, 1) if plan.active_enrollments else 6,
                'revenue_this_month': plan.revenue_this_month,
            }
        )
    return mix[:6]


def _build_monthly_comparison(months, selected_plan, payment_status, payment_method):
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


def _build_comparison_peaks(series):
    max_revenue = max((item['revenue'] for item in series), default=Decimal('0.00'))
    max_count = max((max(item['activations'], item['cancellations']) for item in series), default=0)
    return {
        'max_revenue': max_revenue or Decimal('1.00'),
        'max_count': max_count or 1,
    }


def build_finance_snapshot(params=None):
    filter_form = FinanceFilterForm(params or None)
    finance_base = _build_finance_base(filter_form)
    payments = finance_base['payments']
    enrollments = finance_base['enrollments']
    plans = finance_base['plans']
    plan_portfolio = list(_build_plan_portfolio(plans, payments, enrollments))
    monthly_comparison = _build_monthly_comparison(
        finance_base['months'],
        finance_base['selected_plan'],
        finance_base['payment_status'],
        finance_base['payment_method'],
    )

    return {
        'filter_form': filter_form,
        'payments': payments,
        'enrollments': enrollments,
        'plans': plans,
        'finance_metrics': _build_finance_metrics(payments, enrollments),
        'plan_portfolio': plan_portfolio,
        'plan_mix': _build_plan_mix(plan_portfolio),
        'monthly_comparison': monthly_comparison,
        'comparison_peaks': _build_comparison_peaks(monthly_comparison),
        'financial_alerts': payments.filter(
            status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
        ).order_by('due_date', 'student__full_name')[:8],
        'recent_movements': enrollments.order_by('-updated_at', '-created_at')[:8],
    }