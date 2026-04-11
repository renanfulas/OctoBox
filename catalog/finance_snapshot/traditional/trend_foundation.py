"""
ARQUIVO: fundacao canonica do board de tendencia financeira.

POR QUE ELE EXISTE:
- prepara o contrato factual de Liquido, Recebido, Gastos e Churn antes da camada final de UI.

O QUE ESTE ARQUIVO FAZ:
1. define quais metricas ja estao prontas;
2. reserva o lugar das metricas que ainda dependem de fundacao;
3. entrega a serie canonica do apoio visual do board.
"""

from decimal import Decimal


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


def _build_ready_metric(*, key, label, raw_value, previous_raw_value, delta_label, direction, semantic_state, help_text):
    return {
        'key': key,
        'label': label,
        'availability_status': 'ready',
        'raw_value': raw_value,
        'previous_raw_value': previous_raw_value,
        'display_value': _format_currency_compact(raw_value) if isinstance(raw_value, Decimal) else str(raw_value),
        'delta_label': delta_label,
        'direction': direction,
        'semantic_state': semantic_state,
        'help_text': help_text,
    }


def _build_pending_metric(*, key, label, placeholder_label, pending_reason, dependencies):
    return {
        'key': key,
        'label': label,
        'availability_status': 'pending_foundation',
        'display_value': placeholder_label,
        'delta_label': 'Sem base ainda',
        'direction': 'flat',
        'semantic_state': 'pending',
        'pending_reason': pending_reason,
        'dependencies': dependencies,
        'help_text': pending_reason,
    }


def _resolve_window_label(filter_form):
    months_value = '6'
    if filter_form.is_valid():
        months_value = str(filter_form.cleaned_data.get('months') or '6')
    return dict(filter_form.fields['months'].choices).get(months_value, '6 meses')


def _build_received_sparkline(monthly_comparison):
    if not monthly_comparison:
        return {
            'metric_key': 'received',
            'headline': 'Recebido no recorte',
            'summary': 'Sem leitura suficiente ainda.',
            'value_display': 'Sem leitura suficiente ainda.',
            'delta_display': '',
            'semantic_state': 'steady',
            'realized_points': [],
            'expected_points': [],
            'realized_polyline_points': '',
            'expected_polyline_points': '',
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
            point_delta_label, _ = _format_delta_percent(
                current_item.get('revenue', Decimal('0.00')),
                previous_item.get('revenue', Decimal('0.00')),
            )
            tooltip = (
                f"{current_item.get('short_label')}: {_format_currency_compact(current_item.get('revenue', Decimal('0.00')))}"
                f" | anterior: {_format_currency_compact(previous_item.get('revenue', Decimal('0.00')))}"
                f" | {point_delta_label}"
            )
        else:
            tooltip = (
                f"{current_item.get('short_label')}: {_format_currency_compact(current_item.get('revenue', Decimal('0.00')))}"
                " | primeira leitura do recorte"
            )
        enriched_realized_points.append(
            {
                'x': point['x'],
                'y': point['y'],
                'label': current_item.get('short_label') or current_item.get('label'),
                'tooltip': tooltip,
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
        'metric_key': 'received',
        'headline': 'Recebido no recorte',
        'summary': f"{_format_currency_compact(current_value)} | {delta_label}",
        'value_display': _format_currency_compact(current_value),
        'delta_display': delta_label,
        'semantic_state': semantic_state,
        'realized_points': enriched_realized_points,
        'expected_points': enriched_expected_points,
        'realized_polyline_points': ' '.join(f"{point['x']},{point['y']}" for point in enriched_realized_points),
        'expected_polyline_points': ' '.join(f"{point['x']},{point['y']}" for point in enriched_expected_points),
    }


def _build_churn_sparkline(monthly_comparison):
    if not monthly_comparison:
        return {
            'metric_key': 'churn',
            'headline': 'Churn no recorte',
            'summary': 'Sem leitura suficiente ainda.',
            'value_display': 'Sem leitura suficiente ainda.',
            'delta_display': '',
            'semantic_state': 'steady',
            'realized_points': [],
            'expected_points': [],
            'realized_polyline_points': '',
            'expected_polyline_points': '',
        }

    current_period = monthly_comparison[-1]
    previous_period = monthly_comparison[-2] if len(monthly_comparison) > 1 else current_period
    current_value = int(current_period.get('cancellations', 0))
    previous_value = int(previous_period.get('cancellations', 0))
    delta_label, direction = _format_delta_count(current_value, previous_value)

    if direction == 'up':
        semantic_state = 'bad'
    elif direction == 'down':
        semantic_state = 'good'
    else:
        semantic_state = 'steady'

    cancellations_points = _build_sparkline_points([item.get('cancellations', 0) for item in monthly_comparison])
    activations_points = _build_sparkline_points([item.get('activations', 0) for item in monthly_comparison])

    enriched_cancellations_points = []
    enriched_activations_points = []

    for index, point in enumerate(cancellations_points):
        current_item = monthly_comparison[index]
        previous_item = monthly_comparison[index - 1] if index > 0 else None
        if previous_item is not None:
            point_delta_label, _ = _format_delta_count(
                current_item.get('cancellations', 0),
                previous_item.get('cancellations', 0),
            )
            tooltip = (
                f"{current_item.get('short_label')}: {current_item.get('cancellations', 0)} cancelamentos"
                f" | anterior: {previous_item.get('cancellations', 0)}"
                f" | {point_delta_label}"
            )
        else:
            tooltip = (
                f"{current_item.get('short_label')}: {current_item.get('cancellations', 0)} cancelamentos"
                ' | primeira leitura do recorte'
            )

        enriched_cancellations_points.append(
            {
                'x': point['x'],
                'y': point['y'],
                'label': current_item.get('short_label') or current_item.get('label'),
                'tooltip': tooltip,
            }
        )

    for index, point in enumerate(activations_points):
        current_item = monthly_comparison[index]
        enriched_activations_points.append(
            {
                'x': point['x'],
                'y': point['y'],
                'label': current_item.get('short_label') or current_item.get('label'),
                'tooltip': f"{current_item.get('short_label')}: {current_item.get('activations', 0)} ativacoes",
            }
        )

    return {
        'metric_key': 'churn',
        'headline': 'Churn no recorte',
        'summary': f"{current_value} cancelamentos | {delta_label}",
        'value_display': f'{current_value} cancelamentos',
        'delta_display': delta_label,
        'semantic_state': semantic_state,
        'realized_points': enriched_cancellations_points,
        'expected_points': enriched_activations_points,
        'realized_polyline_points': ' '.join(f"{point['x']},{point['y']}" for point in enriched_cancellations_points),
        'expected_polyline_points': ' '.join(f"{point['x']},{point['y']}" for point in enriched_activations_points),
    }


def build_finance_trend_foundation(*, filter_form, finance_metrics, monthly_comparison):
    current_period = monthly_comparison[-1] if monthly_comparison else {}
    previous_period = monthly_comparison[-2] if len(monthly_comparison) > 1 else current_period

    received_current = Decimal(current_period.get('revenue', Decimal('0.00')))
    received_previous = Decimal(previous_period.get('revenue', Decimal('0.00')))
    received_delta_label, received_direction = _format_delta_percent(received_current, received_previous)
    if received_direction == 'up':
        received_semantic = 'accent'
    elif received_direction == 'down':
        received_semantic = 'bad'
    else:
        received_semantic = 'steady'

    churn_current = int(current_period.get('cancellations', 0))
    churn_previous = int(previous_period.get('cancellations', 0))
    churn_delta_label, churn_direction = _format_delta_count(churn_current, churn_previous)
    if churn_direction == 'up':
        churn_semantic = 'bad'
    elif churn_direction == 'down':
        churn_semantic = 'good'
    else:
        churn_semantic = 'steady'

    window_label = _resolve_window_label(filter_form)
    metric_views = {
        'recebido': {
            'key': 'recebido',
            'title': 'Receita mensal',
            'subtitle': f'Realizado vs esperado no recorte de {window_label}.',
            'legend': {
                'primary': 'Realizado',
                'primary_state': 'realized',
                'secondary': 'Esperado',
                'secondary_state': 'expected',
            },
            'chart_mode': 'revenue',
            'sparkline': _build_received_sparkline(monthly_comparison),
        },
        'churn': {
            'key': 'churn',
            'title': 'Churn e crescimento',
            'subtitle': f'Ativacoes vs cancelamentos no recorte de {window_label}.',
            'legend': {
                'primary': 'Ativacoes',
                'primary_state': 'activation',
                'secondary': 'Cancelamentos',
                'secondary_state': 'cancellation',
            },
            'chart_mode': 'churn',
            'sparkline': _build_churn_sparkline(monthly_comparison),
        },
    }

    metric_pills = [
        _build_pending_metric(
            key='liquido',
            label='Liquido',
            placeholder_label='Aguardando base',
            pending_reason='Falta definir a formula canonica de liquido com politica de estorno e base de gastos.',
            dependencies=['refund_netting_policy', 'expenses_ledger'],
        ),
        _build_ready_metric(
            key='recebido',
            label='Recebido',
            raw_value=received_current,
            previous_raw_value=received_previous,
            delta_label=received_delta_label,
            direction=received_direction,
            semantic_state=received_semantic,
            help_text=finance_metrics['Receita recebida no mes']['note'],
        ),
        _build_pending_metric(
            key='gastos',
            label='Gastos',
            placeholder_label='Em breve',
            pending_reason='Ainda nao existe ledger canonico de gastos do box no dominio financeiro.',
            dependencies=['expenses_ledger'],
        ),
        _build_ready_metric(
            key='churn',
            label='Churn',
            raw_value=Decimal(churn_current),
            previous_raw_value=Decimal(churn_previous),
            delta_label=churn_delta_label,
            direction=churn_direction,
            semantic_state=churn_semantic,
            help_text='Leitura curta das saidas do recorte atual frente ao mes anterior.',
        ),
    ]

    default_metric_key = 'recebido'
    for metric in metric_pills:
        metric['is_interactive'] = metric['availability_status'] == 'ready' and metric['key'] in metric_views
        metric['is_active'] = metric['key'] == default_metric_key
        if metric['is_interactive']:
            metric['view'] = metric_views[metric['key']]

    return {
        'contract': {
            'surface_key': 'finance_trend_board_v1',
            'metric_keys': ['liquido', 'recebido', 'gastos', 'churn'],
            'availability_statuses': ['ready', 'pending_foundation'],
            'sparkline_metric_key': 'received',
            'comparison_mode': 'realized_vs_expected',
            'default_metric_key': default_metric_key,
            'interactive_metric_keys': ['recebido', 'churn'],
            'pending_foundation_contract': {
                'liquido': {
                    'reason': 'Falta regra canonica de liquido.',
                    'dependencies': ['refund_netting_policy', 'expenses_ledger'],
                },
                'gastos': {
                    'reason': 'Falta ledger canonico de gastos.',
                    'dependencies': ['expenses_ledger'],
                },
            },
        },
        'window_label': window_label,
        'metric_pills': metric_pills,
        'metric_views': metric_views,
        'default_metric_key': default_metric_key,
        'sparkline': metric_views[default_metric_key]['sparkline'],
        'legend': {
            'primary': 'Realizado',
            'secondary': 'Esperado',
        },
    }


__all__ = ['build_finance_trend_foundation']
