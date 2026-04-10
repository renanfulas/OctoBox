"""
ARQUIVO: presenter da central financeira.

POR QUE ELE EXISTE:
- tira da view HTTP a montagem da fachada financeira.
- organiza a tela por contrato explicito para reduzir contexto solto e facilitar a evolucao da area.
"""

from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER
from django.urls import reverse
from django.utils import timezone
from shared_support.page_payloads import build_page_hero

from ..finance_snapshot.follow_up_analytics import build_turn_recommendation
from .finance_risk_queue_page import build_finance_risk_queue
from .shared import build_catalog_assets, build_catalog_page_payload


FINANCE_PORTFOLIO_COLORS = ('cyan', 'violet', 'green', 'amber', 'rose', 'slate')


def _build_follow_up_analytics_board(analytics):
    analytics = analytics or {}
    action_map = {
        'review_winback': 'Revisar winback',
        'monitor_recent_reactivation': 'Acompanhar reativacao',
        'escalate_manual_retention': 'Escalar retencao manual',
        'send_financial_followup': 'Enviar follow-up financeiro',
        'monitor_and_nudge': 'Monitorar e lembrar',
        'observe_payment_resolution': 'Observar regularizacao',
        'maintain_relationship': 'Manter relacionamento',
        'overdue': 'WhatsApp de cobranca',
        'reactivation': 'WhatsApp de reativacao',
    }
    signal_bucket_map = {
        'already_inactive': 'Ja inativo',
        'high_signal': 'Alto risco',
        'watch': 'Observacao',
        'recovered': 'Recuperado',
        'stable': 'Estavel',
        'unknown': 'Sem classificacao',
    }
    recommendation_performance = []
    for item in analytics.get('recommendation_performance', [])[:4]:
        recommendation_performance.append(
            {
                'label': action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' ')),
                'historical_score': item['historical_score'],
                'success_rate': item['success_rate'],
                'execution_rate': item['execution_rate'],
                'sample': item['realized_count'],
            }
        )

    realized_actions = []
    for item in analytics.get('realized_action_performance', [])[:3]:
        realized_actions.append(
            {
                'label': action_map.get(item['action_kind'], item['action_kind']),
                'executed_count': item['executed_count'],
                'succeeded_count': item['succeeded_count'],
            }
        )

    weakest = []
    for item in analytics.get('weakest_recommendations', [])[:3]:
        weakest.append(
            {
                'label': action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' ')),
                'failure_rate': item['failure_rate'],
                'failed_count': item['failed_count'],
            }
        )

    windows = list(analytics.get('window_performance', [])[:3])
    timing = list(analytics.get('window_stage_performance', [])[:3])
    recommendation_timing = []
    for item in analytics.get('recommendation_timing_matrix', [])[:4]:
        recommendation_timing.append(
            {
                'action_label': action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' ')),
                'timing_label': item['suggestion_window_label'],
                'success_rate': item['success_rate'],
                'realized_count': item['realized_count'],
                'average_queue_assist_score': item['average_queue_assist_score'],
            }
        )
    recommendation_window = []
    for item in analytics.get('recommendation_window_matrix', [])[:4]:
        recommendation_window.append(
            {
                'action_label': action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' ')),
                'outcome_window': item['outcome_window'],
                'success_rate': item['success_rate'],
                'realized_count': item['realized_count'],
            }
        )
    divergence_timing = []
    for item in analytics.get('divergence_timing_matrix', [])[:4]:
        divergence_timing.append(
            {
                'timing_label': item['suggestion_window_label'],
                'divergent_realized_count': item['divergent_realized_count'],
                'smart_divergence_count': item['smart_divergence_count'],
                'bad_divergence_count': item['bad_divergence_count'],
                'smart_divergence_rate': item['smart_divergence_rate'],
                'bad_divergence_rate': item['bad_divergence_rate'],
            }
        )
    divergence_action = []
    for item in analytics.get('divergence_action_matrix', [])[:4]:
        divergence_action.append(
            {
                'action_label': action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' ')),
                'divergent_realized_count': item['divergent_realized_count'],
                'smart_divergence_count': item['smart_divergence_count'],
                'bad_divergence_count': item['bad_divergence_count'],
                'smart_divergence_rate': item['smart_divergence_rate'],
                'bad_divergence_rate': item['bad_divergence_rate'],
            }
        )
    divergence_signal_bucket = []
    for item in analytics.get('divergence_signal_bucket_matrix', [])[:4]:
        divergence_signal_bucket.append(
            {
                'signal_bucket_label': signal_bucket_map.get(item['signal_bucket'], item['signal_bucket']),
                'divergent_realized_count': item['divergent_realized_count'],
                'smart_divergence_count': item['smart_divergence_count'],
                'bad_divergence_count': item['bad_divergence_count'],
                'smart_divergence_rate': item['smart_divergence_rate'],
                'bad_divergence_rate': item['bad_divergence_rate'],
            }
        )
    turn_priority_tension_timing = []
    for item in analytics.get('turn_priority_tension_timing_matrix', [])[:4]:
        turn_priority_tension_timing.append(
            {
                'timing_label': item['suggestion_window_label'],
                'realized_count': item['realized_count'],
                'healthy_tension_count': item['healthy_tension_count'],
                'dangerous_tension_count': item['dangerous_tension_count'],
                'healthy_tension_rate': item['healthy_tension_rate'],
                'dangerous_tension_rate': item['dangerous_tension_rate'],
            }
        )
    turn_priority_tension_signal_bucket = []
    for item in analytics.get('turn_priority_tension_signal_bucket_matrix', [])[:4]:
        turn_priority_tension_signal_bucket.append(
            {
                'signal_bucket_label': signal_bucket_map.get(item['signal_bucket'], item['signal_bucket']),
                'realized_count': item['realized_count'],
                'healthy_tension_count': item['healthy_tension_count'],
                'dangerous_tension_count': item['dangerous_tension_count'],
                'healthy_tension_rate': item['healthy_tension_rate'],
                'dangerous_tension_rate': item['dangerous_tension_rate'],
            }
        )
    turn_priority_tension_compound = []
    for item in analytics.get('turn_priority_tension_compound_matrix', [])[:4]:
        turn_priority_tension_compound.append(
            {
                'timing_label': item['suggestion_window_label'],
                'signal_bucket_label': signal_bucket_map.get(item['signal_bucket'], item['signal_bucket']),
                'realized_count': item['realized_count'],
                'healthy_tension_rate': item['healthy_tension_rate'],
                'dangerous_tension_rate': item['dangerous_tension_rate'],
            }
        )
    divergence_compound = []
    for item in analytics.get('divergence_compound_matrix', [])[:4]:
        divergence_compound.append(
            {
                'action_label': action_map.get(item['recommended_action'], item['recommended_action'].replace('_', ' ')),
                'timing_label': item['suggestion_window_label'],
                'signal_bucket_label': signal_bucket_map.get(item['signal_bucket'], item['signal_bucket']),
                'divergent_realized_count': item['divergent_realized_count'],
                'smart_divergence_rate': item['smart_divergence_rate'],
                'bad_divergence_rate': item['bad_divergence_rate'],
            }
        )
    best_play = build_turn_recommendation(analytics)
    if best_play.get('recommended_action'):
        action_label = action_map.get(best_play['recommended_action'], best_play['recommended_action'].replace('_', ' '))
        best_play['action_label'] = action_label
        best_play['summary'] = (
            f"{action_label} esta liderando no historico ativo dentro da janela {best_play.get('outcome_window', '')}, "
            f"com {best_play.get('success_rate', 0.0)}% de sucesso em {best_play.get('realized_count', 0)} realizado(s)."
        )
    adherence = analytics.get('turn_recommendation_adherence', {}) or {}
    turn_outcome = analytics.get('turn_recommendation_outcome', {}) or {}
    turn_learning = analytics.get('turn_recommendation_learning', {}) or {}
    turn_priority_outcome = analytics.get('turn_priority_outcome', {}) or {}
    turn_priority_learning = analytics.get('turn_priority_learning', {}) or {}

    return {
        'summary': analytics.get('summary', {}),
        'best_play': best_play,
        'turn_recommendation_adherence': adherence,
        'turn_recommendation_outcome': {
            'aligned': {
                'label': 'Seguiu o turno',
                'realized_count': (turn_outcome.get('aligned') or {}).get('realized_count', 0),
                'succeeded_count': (turn_outcome.get('aligned') or {}).get('succeeded_count', 0),
                'failed_count': (turn_outcome.get('aligned') or {}).get('failed_count', 0),
                'success_rate': (turn_outcome.get('aligned') or {}).get('success_rate', 0.0),
            },
            'divergent': {
                'label': 'Divergiu do turno',
                'realized_count': (turn_outcome.get('divergent') or {}).get('realized_count', 0),
                'succeeded_count': (turn_outcome.get('divergent') or {}).get('succeeded_count', 0),
                'failed_count': (turn_outcome.get('divergent') or {}).get('failed_count', 0),
                'success_rate': (turn_outcome.get('divergent') or {}).get('success_rate', 0.0),
            },
        },
        'turn_recommendation_learning': {
            'smart_divergence': {
                'headline': (turn_learning.get('smart_divergence') or {}).get('headline', 'Quando divergir valeu a pena'),
                'realized_count': (turn_learning.get('smart_divergence') or {}).get('realized_count', 0),
                'success_rate': (turn_learning.get('smart_divergence') or {}).get('success_rate', 0.0),
                'summary': (turn_learning.get('smart_divergence') or {}).get(
                    'summary',
                    'Ainda sem casos suficientes para provar divergencia inteligente.',
                ),
            },
            'bad_divergence': {
                'headline': (turn_learning.get('bad_divergence') or {}).get(
                    'headline',
                    'Quando divergir piorou o resultado',
                ),
                'realized_count': (turn_learning.get('bad_divergence') or {}).get('realized_count', 0),
                'failure_rate': (turn_learning.get('bad_divergence') or {}).get('failure_rate', 0.0),
                'summary': (turn_learning.get('bad_divergence') or {}).get(
                    'summary',
                    'Ainda sem casos suficientes para provar desvio ruim.',
                ),
            },
        },
        'turn_priority_outcome': {
            'aligned': {
                'label': 'Turno alinhado',
                'realized_count': (turn_priority_outcome.get('aligned') or {}).get('realized_count', 0),
                'succeeded_count': (turn_priority_outcome.get('aligned') or {}).get('succeeded_count', 0),
                'failed_count': (turn_priority_outcome.get('aligned') or {}).get('failed_count', 0),
                'success_rate': (turn_priority_outcome.get('aligned') or {}).get('success_rate', 0.0),
            },
            'tension': {
                'label': 'Turno em tensao',
                'realized_count': (turn_priority_outcome.get('tension') or {}).get('realized_count', 0),
                'succeeded_count': (turn_priority_outcome.get('tension') or {}).get('succeeded_count', 0),
                'failed_count': (turn_priority_outcome.get('tension') or {}).get('failed_count', 0),
                'success_rate': (turn_priority_outcome.get('tension') or {}).get('success_rate', 0.0),
            },
        },
        'turn_priority_learning': {
            'healthy_tension': {
                'headline': (turn_priority_learning.get('healthy_tension') or {}).get(
                    'headline',
                    'Quando a tensao valeu a pena',
                ),
                'realized_count': (turn_priority_learning.get('healthy_tension') or {}).get('realized_count', 0),
                'success_rate': (turn_priority_learning.get('healthy_tension') or {}).get('success_rate', 0.0),
                'summary': (turn_priority_learning.get('healthy_tension') or {}).get(
                    'summary',
                    'Ainda sem casos suficientes para provar tensao saudavel.',
                ),
            },
            'dangerous_tension': {
                'headline': (turn_priority_learning.get('dangerous_tension') or {}).get(
                    'headline',
                    'Quando a tensao virou dispersao',
                ),
                'realized_count': (turn_priority_learning.get('dangerous_tension') or {}).get('realized_count', 0),
                'failure_rate': (turn_priority_learning.get('dangerous_tension') or {}).get('failure_rate', 0.0),
                'summary': (turn_priority_learning.get('dangerous_tension') or {}).get(
                    'summary',
                    'Ainda sem casos suficientes para provar tensao perigosa.',
                ),
            },
        },
        'turn_priority_tension_timing': turn_priority_tension_timing,
        'turn_priority_tension_signal_bucket': turn_priority_tension_signal_bucket,
        'turn_priority_tension_compound': turn_priority_tension_compound,
        'recommendations': recommendation_performance,
        'realized_actions': realized_actions,
        'weakest': weakest,
        'windows': windows,
        'timing': timing,
        'recommendation_timing': recommendation_timing,
        'recommendation_window': recommendation_window,
        'divergence_timing': divergence_timing,
        'divergence_action': divergence_action,
        'divergence_signal_bucket': divergence_signal_bucket,
        'divergence_compound': divergence_compound,
        'score_guide': analytics.get('score_guide', {}),
    }


def _build_finance_revenue_chart(monthly_comparison, comparison_peaks):
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


def _build_finance_churn_chart(monthly_comparison, comparison_peaks):
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


def _build_finance_overdue_rows(financial_alerts):
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


def _build_finance_portfolio_panel(plan_portfolio):
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


def build_finance_center_page(*, snapshot, operational_queue, export_links, current_role_slug, form):
    filter_form = snapshot['filter_form']
    financial_alerts = snapshot['financial_alerts']
    financial_churn_foundation = snapshot.get('financial_churn_foundation', {})
    finance_follow_up_analytics = snapshot.get('finance_follow_up_analytics', {})
    finance_follow_up_analytics_board = _build_follow_up_analytics_board(finance_follow_up_analytics)
    plan_portfolio = snapshot['plan_portfolio']
    finance_pulse = snapshot['finance_pulse']
    finance_priority_context = snapshot['finance_priority_context']
    pressure_total = len(operational_queue) + len(financial_alerts)
    can_manage_finance = current_role_slug in (ROLE_OWNER, ROLE_MANAGER)
    has_operational_queue = bool(operational_queue)

    default_panel = finance_priority_context['default_panel']
    default_action = finance_priority_context['default_action']

    operational_focus = [
        {
            'label': 'Quem pede contato agora' if finance_priority_context['dominant_key'] == 'queue' else 'Onde a fila ainda pode virar caixa',
            'chip_label': 'Cobrancas',
            'summary': (
                f'{len(operational_queue)} caso(s) ja tem abordagem sugerida e nao deveriam esperar outra leitura para virar acao.'
                if finance_priority_context['dominant_key'] == 'queue' else
                f'{len(operational_queue)} caso(s) continuam prontos para acao, mas hoje dividem a abertura com leitura de caixa e carteira.'
            ),
            'count': len(operational_queue),
            'pill_class': 'warning' if len(operational_queue) > 0 else 'success',
            'href': '#finance-priority-board' if has_operational_queue else '#finance-queue-board',
            'href_label': 'Abrir regua' if has_operational_queue else 'Abrir fila',
            'data_action': 'open-tab-finance-queue',
        },
        {
            'label': 'Onde a fila pressiona o caixa',
            'chip_label': 'Fila',
            'summary': f'{len(financial_alerts)} cobranca(s) ja aparecem como pendencia ou atraso no periodo atual.',
            'count': len(financial_alerts),
            'pill_class': 'warning' if len(financial_alerts) > 0 else 'info',
            'href': '#finance-queue-board',
            'href_label': 'Ver fila financeira',
            'data_action': 'open-tab-finance-queue',
        },
        {
            'label': 'Como a carteira respira',
            'chip_label': 'Carteira',
            'summary': f"Recebido: R$ {finance_pulse['received']:.2f} | Em aberto: R$ {finance_pulse['open']:.2f}.",
            'count': finance_pulse['overdue_students'],
            'pill_class': 'accent',
            'href': '#finance-trend-board',
            'href_label': 'Ver tendencia',
            'data_action': 'open-tab-finance-movements',
        },
    ]

    hero_actions = [
        {
            'label': 'Ver prioridades',
            'href': '#finance-priority-board' if has_operational_queue else '#finance-queue-board',
            'kind': 'primary',
            'data_action': 'open-tab-finance-queue',
        },
        {'label': 'Abrir carteira', 'href': '#finance-portfolio-board', 'kind': 'secondary', 'data_action': 'open-tab-finance-portfolio'},
    ]

    dominant_key = finance_priority_context.get('dominant_key')
    if dominant_key == 'portfolio':
        hero_title = 'Carteira em leitura.'
    elif dominant_key == 'queue':
        hero_title = 'Fila financeira.'
    else:
        hero_title = 'Financeiro ativo.'

    hero = build_page_hero(
        eyebrow='Financeiro',
        title=hero_title,
        copy='Veja a pressao dominante, abra a primeira passagem e desca sem ruido.',
        actions=hero_actions,
        aria_label='Panorama financeiro',
        classes=['finance-hero'],
        heading_level='h1',
    )

    return build_catalog_page_payload(
        context={
            'page_key': 'finance-center',
            'title': 'Financeiro',
            'subtitle': 'Receita, carteira e sinais operacionais em leitura guiada.',
            'mode': 'management' if can_manage_finance else 'read-only',
            'role_slug': current_role_slug,
        },
        data={
            'hero': hero,
            'can_manage_finance': can_manage_finance,
            'finance_filter_form': filter_form,
            'finance_metrics': snapshot['finance_metrics'],
            'finance_pulse': finance_pulse,
            'financial_churn_foundation': financial_churn_foundation,
            'finance_risk_queue': build_finance_risk_queue(
                financial_churn_foundation,
                follow_up_analytics_board=finance_follow_up_analytics_board,
            ),
            'finance_follow_up_analytics': finance_follow_up_analytics,
            'finance_follow_up_analytics_board': finance_follow_up_analytics_board,
            'finance_revenue_chart': _build_finance_revenue_chart(snapshot['monthly_comparison'], snapshot['comparison_peaks']),
            'finance_churn_chart': _build_finance_churn_chart(snapshot['monthly_comparison'], snapshot['comparison_peaks']),
            'finance_overdue_rows': _build_finance_overdue_rows(financial_alerts),
            'interactive_kpis': snapshot.get('interactive_kpis', []),
            'finance_priority_context': finance_priority_context,
            'operational_focus': operational_focus,
            'plan_portfolio': plan_portfolio,
            'finance_portfolio_panel': _build_finance_portfolio_panel(plan_portfolio),
            'monthly_comparison': snapshot['monthly_comparison'],
            'comparison_peaks': snapshot['comparison_peaks'],
            'financial_alerts': financial_alerts,
            'operational_queue': operational_queue,
            'finance_filter_summary': build_finance_filter_summary(filter_form),
            'form': form,
        },
        actions={
            'finance_export_links': export_links,
        },
        behavior={
            'default_panel': default_panel,
            'default_action': default_action,
        },
        capabilities={
            'can_manage_finance': can_manage_finance,
            'can_export_finance': current_role_slug in (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER),
        },
        assets=build_catalog_assets(
            css=['css/catalog/finance.css', 'css/design-system/financial.css'],
            include_catalog_shared=True,
        ),
    )
