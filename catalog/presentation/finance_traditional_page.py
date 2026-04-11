"""
ARQUIVO: presenter da camada tradicional da central financeira.

POR QUE ELE EXISTE:
- traduz carteira, movimento e filtros sem misturar leitura assistida.
"""

from decimal import Decimal

from django.urls import reverse
from django.utils import timezone


FINANCE_PORTFOLIO_COLORS = ('cyan', 'violet', 'green', 'amber', 'rose', 'slate')


def _format_currency_compact(value):
    value = Decimal(value or 0)
    absolute = abs(value)
    if absolute >= Decimal('1000000'):
        return f"R$ {(value / Decimal('1000000')).quantize(Decimal('0.1'))}".replace('.', ',') + ' mi'
    if absolute >= Decimal('1000'):
        return f"R$ {(value / Decimal('1000')).quantize(Decimal('0.1'))}".replace('.', ',') + 'k'
    return f"R$ {value.quantize(Decimal('0.01'))}".replace('.', ',')


def _format_delta_percent(current, previous):
    current = Decimal(current or 0)
    previous = Decimal(previous or 0)
    if previous == 0:
        if current == 0:
            return 'Sem variacao', 'flat'
        return 'Sem base anterior', 'up'
    change = ((current - previous) / previous) * Decimal('100')
    rounded = change.quantize(Decimal('0.1'))
    if rounded == 0:
        return 'Sem variacao', 'flat'
    signal = '+' if rounded > 0 else ''
    direction = 'up' if rounded > 0 else 'down'
    return f'{signal}{str(rounded).replace(".", ",")}% vs mes anterior', direction


def _format_delta_count(current, previous):
    current = int(current or 0)
    previous = int(previous or 0)
    delta = current - previous
    if delta == 0:
        return 'Mesmo nivel do mes anterior', 'flat'
    direction = 'up' if delta > 0 else 'down'
    signal = '+' if delta > 0 else ''
    return f'{signal}{delta} vs mes anterior', direction


def _build_metric_pill(*, key, label, value, delta_label, direction, semantic_state, availability_status='ready', helper_text=''):
    return {
        'key': key,
        'label': label,
        'value': value,
        'delta_label': delta_label,
        'direction': direction,
        'semantic_state': semantic_state,
        'availability_status': availability_status,
        'helper_text': helper_text,
    }


def _build_pending_metric_pill(*, key, label, placeholder_label):
    return {
        'key': key,
        'label': label,
        'value': placeholder_label,
        'delta_label': 'Sem base ainda',
        'direction': 'flat',
        'semantic_state': 'pending',
        'availability_status': 'pending_foundation',
        'helper_text': 'Estrutura reservada para a proxima fundacao do financeiro.',
    }


def _build_sparkline_points(series):
    values = [Decimal(item or 0) for item in series]
    if not values:
        return []

    min_value = min(values)
    max_value = max(values)
    span = max_value - min_value
    if span == 0:
        span = Decimal('1')

    if len(values) == 1:
        x_positions = [50]
    else:
        step = Decimal('100') / Decimal(len(values) - 1)
        x_positions = [float((step * index).quantize(Decimal('0.01'))) for index in range(len(values))]

    points = []
    for index, value in enumerate(values):
        normalized = (value - min_value) / span
        y = float((Decimal('30') - (normalized * Decimal('24'))).quantize(Decimal('0.01')))
        points.append({'x': x_positions[index], 'y': y, 'value': value})
    return points


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
                'performance_state': 'good' if revenue >= expected_revenue else 'bad',
                'performance_label': 'Fechou acima da meta' if revenue >= expected_revenue else 'Fechou abaixo da meta',
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
        net_growth = item['net_growth']
        if net_growth > 0:
            performance_state = 'good'
            performance_label = 'Fechou com ganho de base'
        elif net_growth < 0:
            performance_state = 'bad'
            performance_label = 'Fechou com perda de base'
        else:
            performance_state = 'steady'
            performance_label = 'Fechou em equilibrio'
        items.append(
            {
                'label': item.get('short_label') or item['label'],
                'activations': activations,
                'cancellations': cancellations,
                'net_growth': net_growth,
                'activation_height': max(8, round((activations / axis_max) * 100)) if axis_max else 8,
                'cancellation_height': max(8, round((cancellations / axis_max) * 100)) if axis_max else 8,
                'performance_state': performance_state,
                'performance_label': performance_label,
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
            'key': 'months',
            'label': 'Janela',
            'value': months_choices.get(months_value, '6 meses'),
            'is_default': months_value == '6',
            'summary': 'Define o horizonte da leitura gerencial antes de comparar caixa e retencao.',
        },
        {
            'key': 'plan',
            'label': 'Plano',
            'value': selected_plan.name if selected_plan else 'Todos os planos',
            'is_default': selected_plan is None,
            'summary': 'Mostra se o recorte esta amplo ou se ja esta olhando uma carteira especifica.',
        },
        {
            'key': 'payment_status',
            'label': 'Status',
            'value': status_choices.get(payment_status, 'Todos'),
            'is_default': not payment_status,
            'summary': 'Ajuda a separar leitura total de leitura de pressao operacional.',
        },
        {
            'key': 'payment_method',
            'label': 'Metodo',
            'value': method_choices.get(payment_method, 'Todos'),
            'is_default': not payment_method,
            'summary': 'Util quando a analise precisa isolar comportamento de recebimento.',
        },
        {
            'key': 'queue_focus',
            'label': 'Missao',
            'value': dict(filter_form.fields['queue_focus'].choices).get(
                filter_form.cleaned_data.get('queue_focus') if filter_form.is_valid() else '',
                'Todas',
            ),
            'is_default': not (filter_form.cleaned_data.get('queue_focus') if filter_form.is_valid() else ''),
            'summary': 'Recorta a fila para a missao operacional que merece foco agora.',
        },
    ]


def build_finance_filter_summary_current(summary_items):
    active_values = []
    for item in summary_items:
        if item.get('key') == 'months':
            active_values.append(item['value'])
            continue
        if not item.get('is_default'):
            active_values.append(item['value'])
    if active_values:
        return 'Recorte atual: ' + ' | '.join(active_values)
    return 'Recorte atual: padrao da leitura financeira.'


def build_finance_trend_metric_pills(finance_metrics, monthly_comparison):
    current_period = monthly_comparison[-1] if monthly_comparison else {}
    previous_period = monthly_comparison[-2] if len(monthly_comparison) > 1 else current_period

    received_current = current_period.get('revenue', Decimal('0.00'))
    received_previous = previous_period.get('revenue', Decimal('0.00'))
    received_delta_label, received_direction = _format_delta_percent(received_current, received_previous)
    received_semantic = 'good' if received_direction == 'up' else 'bad' if received_direction == 'down' else 'steady'

    churn_current = current_period.get('cancellations', 0)
    churn_previous = previous_period.get('cancellations', 0)
    churn_delta_label, churn_direction = _format_delta_count(churn_current, churn_previous)
    if churn_direction == 'up':
        churn_semantic = 'bad'
    elif churn_direction == 'down':
        churn_semantic = 'good'
    else:
        churn_semantic = 'steady'

    return [
        _build_pending_metric_pill(
            key='liquido',
            label='Liquido',
            placeholder_label='Aguardando base',
        ),
        _build_metric_pill(
            key='recebido',
            label='Recebido',
            value=_format_currency_compact(received_current),
            delta_label=received_delta_label,
            direction=received_direction,
            semantic_state='accent' if received_semantic == 'good' else 'bad' if received_semantic == 'bad' else 'steady',
            helper_text=finance_metrics['Receita recebida no mes']['note'],
        ),
        _build_pending_metric_pill(
            key='gastos',
            label='Gastos',
            placeholder_label='Em breve',
        ),
        _build_metric_pill(
            key='churn',
            label='Churn',
            value=str(churn_current),
            delta_label=churn_delta_label,
            direction=churn_direction,
            semantic_state=churn_semantic,
            helper_text='Leitura curta das saidas do recorte atual frente ao mes anterior.',
        ),
    ]


def build_finance_received_sparkline(monthly_comparison):
    if not monthly_comparison:
        return {
            'realized_points': [],
            'expected_points': [],
            'realized_polyline_points': '',
            'expected_polyline_points': '',
            'semantic_state': 'steady',
            'headline': 'Recebido no recorte',
            'summary': 'Sem leitura suficiente ainda.',
        }

    current_period = monthly_comparison[-1]
    previous_period = monthly_comparison[-2] if len(monthly_comparison) > 1 else current_period
    current_value = Decimal(current_period.get('revenue', Decimal('0.00')))
    previous_value = Decimal(previous_period.get('revenue', Decimal('0.00')))
    delta_label, direction = _format_delta_percent(current_value, previous_value)
    if direction == 'up':
        semantic_state = 'good'
    elif direction == 'down':
        semantic_state = 'bad'
    else:
        semantic_state = 'steady'

    realized_points = _build_sparkline_points([item.get('revenue', Decimal('0.00')) for item in monthly_comparison])
    expected_points = _build_sparkline_points([item.get('expected_revenue', Decimal('0.00')) for item in monthly_comparison])
    enriched_realized_points = []
    enriched_expected_points = []
    for index, point in enumerate(realized_points):
        current_item = monthly_comparison[index]
        previous_item = monthly_comparison[index - 1] if index > 0 else None
        if previous_item is not None:
            point_delta_label, _ = _format_delta_percent(current_item.get('revenue', Decimal('0.00')), previous_item.get('revenue', Decimal('0.00')))
            comparison_text = f"{current_item.get('short_label')}: {_format_currency_compact(current_item.get('revenue', Decimal('0.00')))} | anterior: {_format_currency_compact(previous_item.get('revenue', Decimal('0.00')))} | {point_delta_label}"
        else:
            comparison_text = f"{current_item.get('short_label')}: {_format_currency_compact(current_item.get('revenue', Decimal('0.00')))} | primeira leitura do recorte"
        enriched_realized_points.append(
            {
                'x': point['x'],
                'y': point['y'],
                'label': current_item.get('short_label') or current_item.get('label'),
                'tooltip': comparison_text,
            }
        )

    for index, point in enumerate(expected_points):
        current_item = monthly_comparison[index]
        enriched_expected_points.append(
            {
                'x': point['x'],
                'y': point['y'],
                'label': current_item.get('short_label') or current_item.get('label'),
                'tooltip': f"{current_item.get('short_label')}: esperado {_format_currency_compact(current_item.get('expected_revenue', Decimal('0.00')))}",
            }
        )

    return {
        'realized_points': enriched_realized_points,
        'expected_points': enriched_expected_points,
        'realized_polyline_points': ' '.join(f"{point['x']},{point['y']}" for point in enriched_realized_points),
        'expected_polyline_points': ' '.join(f"{point['x']},{point['y']}" for point in enriched_expected_points),
        'semantic_state': semantic_state,
        'headline': 'Recebido no recorte',
        'summary': f"{_format_currency_compact(current_value)} | {delta_label}",
    }


__all__ = [
    'build_finance_churn_chart',
    'build_finance_filter_summary',
    'build_finance_filter_summary_current',
    'build_finance_received_sparkline',
    'build_finance_trend_metric_pills',
    'build_finance_overdue_rows',
    'build_finance_portfolio_panel',
    'build_finance_revenue_chart',
]
