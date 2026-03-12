"""
ARQUIVO: base de filtros e querysets do snapshot financeiro.

POR QUE ELE EXISTE:
- Separa a resolucao dos filtros e dos querysets base da montagem dos indicadores.

O QUE ESTE ARQUIVO FAZ:
1. Resolve os filtros do formulario financeiro.
2. Monta os querysets base de pagamentos, matriculas e planos.

PONTOS CRITICOS:
- Qualquer filtro errado aqui distorce todo o snapshot financeiro.
"""

from django.utils import timezone

from boxcore.models import Enrollment, MembershipPlan, Payment


def shift_month(source_date, month_delta):
    month_index = source_date.month - 1 + month_delta
    year = source_date.year + month_index // 12
    month = month_index % 12 + 1
    return source_date.replace(year=year, month=month, day=1)


def get_finance_filter_values(filter_form):
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


def build_finance_base(filter_form):
    months, selected_plan, payment_status, payment_method = get_finance_filter_values(filter_form)
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


__all__ = ['build_finance_base', 'get_finance_filter_values', 'shift_month']