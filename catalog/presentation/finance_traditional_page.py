"""
ARQUIVO: presenter da camada tradicional da central financeira.

POR QUE ELE EXISTE:
- traduz carteira, movimento e filtros sem misturar leitura assistida.
"""

from django.urls import reverse
from django.utils import timezone


FINANCE_PORTFOLIO_COLORS = ('cyan', 'violet', 'green', 'amber', 'rose', 'slate')


def build_finance_revenue_chart(monthly_comparison, comparison_peaks):
    max_revenue = comparison_peaks.get('max_revenue') or 0
    axis_step = 3000
    axis_max = axis_step

    if max_revenue:
        axis_max = ((int(max_revenue) + axis_step - 1) // axis_step) * axis_step
        axis_max = max(axis_max, axis_step)

    ticks = []
    for step in range(4, -1, -1):
        value = int(axis_max * step / 4)
        ticks.append(
            {
                'value': value,
                'label': f'{int(round(value / 1000))}k',
            }
        )

    items = []
    for item in monthly_comparison:
        revenue = item['revenue']
        expected_revenue = item.get('expected_revenue', revenue)
        items.append(
            {
                'label': item.get('short_label') or item['label'],
                'realized_value': revenue,
                'expected_value': expected_revenue,
                'realized_height': max(8, round((float(revenue) / axis_max) * 100)) if axis_max else 8,
                'expected_height': max(8, round((float(expected_revenue) / axis_max) * 100)) if axis_max else 8,
            }
        )

    return {
        'ticks': ticks,
        'items': items,
    }


def build_finance_churn_chart(monthly_comparison, comparison_peaks):
    max_count = comparison_peaks.get('max_count') or 1
    axis_max = max(max_count, 1)

    ticks = []
    for step in range(4, -1, -1):
        value = int(round(axis_max * step / 4))
        ticks.append({'value': value, 'label': str(value)})

    items = []
    for item in monthly_comparison:
        activations = item['activations']
        cancellations = item['cancellations']
        items.append(
            {
                'label': item.get('short_label') or item['label'],
                'activations': activations,
                'cancellations': cancellations,
                'net_growth': item['net_growth'],
                'activation_height': max(8, round((activations / axis_max) * 100)) if axis_max else 8,
                'cancellation_height': max(8, round((cancellations / axis_max) * 100)) if axis_max else 8,
            }
        )

    return {
        'ticks': ticks,
        'items': items,
    }


def build_finance_overdue_rows(financial_alerts):
    today = timezone.localdate()
    rows = []

    for payment in financial_alerts:
        student_name = payment.student.full_name
        initials = ''.join(part[0] for part in student_name.split()[:2]).upper()
        due_date = payment.due_date
        overdue_days = max((today - due_date).days, 0)

        rows.append(
            {
                'student_name': student_name,
                'student_url': f"{reverse('student-quick-update', args=[payment.student.id])}#student-financial-overview",
                'initials': initials[:2],
                'plan_name': payment.enrollment.plan.name if payment.enrollment else 'Sem vinculo de plano',
                'amount': payment.amount,
                'overdue_days': overdue_days,
                'badge': 'Urgente' if overdue_days >= 7 else 'Atencao',
            }
        )

    return rows


def build_finance_portfolio_panel(plan_portfolio):
    active_rows = []
    total_revenue = 0.0

    for plan in plan_portfolio:
        revenue = float(plan.revenue_this_month or 0)
        active_enrollments = int(plan.active_enrollments or 0)
        is_active_plan = bool(getattr(plan, 'active', False))
        if revenue <= 0 and active_enrollments <= 0 and not is_active_plan:
            continue

        active_rows.append(
            {
                'name': plan.name,
                'revenue': revenue,
                'active_enrollments': active_enrollments,
                'is_active_plan': is_active_plan,
            }
        )
        total_revenue += revenue

    if not active_rows:
        return {'items': [], 'total_revenue': 0.0}

    active_rows.sort(key=lambda item: (-int(item['is_active_plan']), -item['revenue'], -item['active_enrollments'], item['name']))

    total_revenue = total_revenue or 1.0
    items = []
    for index, row in enumerate(active_rows[:6]):
        items.append(
            {
                'name': row['name'],
                'revenue': row['revenue'],
                'active_enrollments': row['active_enrollments'],
                'width': max(12, round((row['revenue'] / total_revenue) * 100)),
                'color': FINANCE_PORTFOLIO_COLORS[index % len(FINANCE_PORTFOLIO_COLORS)],
                'is_new_empty_plan': row['revenue'] <= 0 and row['active_enrollments'] <= 0,
            }
        )

    return {
        'items': items,
        'total_revenue': sum(item['revenue'] for item in items),
    }


def build_finance_filter_summary(filter_form):
    months_choices = dict(filter_form.fields['months'].choices)
    status_choices = dict(filter_form.fields['payment_status'].choices)
    method_choices = dict(filter_form.fields['payment_method'].choices)

    months_value = '6'
    selected_plan = None
    payment_status = ''
    payment_method = ''

    if filter_form.is_valid():
        months_value = str(filter_form.cleaned_data.get('months') or '6')
        selected_plan = filter_form.cleaned_data.get('plan')
        payment_status = filter_form.cleaned_data.get('payment_status') or ''
        payment_method = filter_form.cleaned_data.get('payment_method') or ''

    return [
        {
            'label': 'Janela atual',
            'value': months_choices.get(months_value, '6 meses'),
            'summary': 'Define o horizonte da leitura gerencial antes de comparar caixa e retencao.',
        },
        {
            'label': 'Plano em foco',
            'value': selected_plan.name if selected_plan else 'Todos os planos',
            'summary': 'Mostra se o recorte esta amplo ou se ja esta olhando uma carteira especifica.',
        },
        {
            'label': 'Status financeiro',
            'value': status_choices.get(payment_status, 'Todos'),
            'summary': 'Ajuda a separar leitura total de leitura de pressao operacional.',
        },
        {
            'label': 'Metodo de pagamento',
            'value': method_choices.get(payment_method, 'Todos'),
            'summary': 'Util quando a analise precisa isolar comportamento de recebimento.',
        },
        {
            'label': 'Missao da fila',
            'value': dict(filter_form.fields['queue_focus'].choices).get(
                filter_form.cleaned_data.get('queue_focus') if filter_form.is_valid() else '',
                'Todas',
            ),
            'summary': 'Recorta a fila para a missao operacional que merece foco agora.',
        },
    ]


__all__ = [
    'build_finance_churn_chart',
    'build_finance_filter_summary',
    'build_finance_overdue_rows',
    'build_finance_portfolio_panel',
    'build_finance_revenue_chart',
]
