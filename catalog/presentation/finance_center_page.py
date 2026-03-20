"""
ARQUIVO: presenter da central financeira.

POR QUE ELE EXISTE:
- tira da view HTTP a montagem da fachada financeira.
- organiza a tela por contrato explicito para reduzir contexto solto e facilitar a evolucao da area.
"""

from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER
from access.shell_actions import build_shell_action_buttons_from_focus
from shared_support.page_payloads import build_page_hero

from .shared import build_catalog_assets, build_catalog_page_payload


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
    ]


def build_finance_center_page(*, snapshot, operational_queue, operational_metrics, export_links, current_role_slug, form):
    filter_form = snapshot['filter_form']
    financial_alerts = snapshot['financial_alerts']
    plan_portfolio = snapshot['plan_portfolio']
    recent_movements = snapshot['recent_movements']
    finance_pulse = snapshot['finance_pulse']
    pressure_total = len(operational_queue) + len(financial_alerts)
    can_manage_finance = current_role_slug in (ROLE_OWNER, ROLE_MANAGER)

    if pressure_total > 0:
        priority_badge = 'warning'
        priority_label = f'{pressure_total} sinal(is) agora'
    else:
        priority_badge = 'success'
        priority_label = 'Pressao controlada'

    finance_right_rail_snapshot = [
        {
            'label': 'Pressao combinada',
            'value': pressure_total,
            'summary': 'Soma contato assistido com fila financeira no recorte atual.',
        },
        {
            'label': 'Em aberto',
            'value': f"R$ {finance_pulse['open']:.2f}",
            'summary': 'Mostra o volume que ainda pede conversao em caixa.',
        },
        {
            'label': 'Alunos em atraso',
            'value': finance_pulse['overdue_students'],
            'summary': 'Ajuda a medir se a pressao e pontual ou ja alcancou a base.',
        },
    ]
    operational_focus = [
        {
            'label': 'Cobranca pede contato',
            'chip_label': 'Cobranças',
            'summary': f'{len(operational_queue)} caso(s) ja tem abordagem sugerida e nao deveriam esperar outra leitura para virar acao.',
            'count': len(operational_queue),
            'pill_class': 'warning' if len(operational_queue) > 0 else 'success',
            'href': '#finance-rail-board',
            'href_label': 'Abrir regua',
        },
        {
            'label': 'Fila pressionando caixa',
            'chip_label': 'Fila',
            'summary': f'{len(financial_alerts)} cobranca(s) ja aparecem como pendencia ou atraso no recorte atual.',
            'count': len(financial_alerts),
            'pill_class': 'warning' if len(financial_alerts) > 0 else 'info',
            'href': '#finance-queue-board',
            'href_label': 'Ver fila financeira',
        },
        {
            'label': 'Pulso executivo',
            'chip_label': 'Carteira',
            'summary': f"Recebido: R$ {finance_pulse['received']:.2f} | Em aberto: R$ {finance_pulse['open']:.2f}.",
            'pill_class': 'accent',
            'href': '#finance-trend-board',
            'href_label': 'Ver tendencia',
        },
    ]
    shell_action_buttons = build_shell_action_buttons_from_focus(
        focus=operational_focus,
        next_action={
            'href': '#finance-portfolio-board',
            'summary': 'Depois da pressao viva, desca para a carteira e leia a proxima acao estrutural do financeiro.',
        },
        scope='finance',
    )
    hero_actions = [
        {'label': 'Ver regua', 'href': '#finance-priority-board', 'kind': 'primary', 'data_action': 'open-tab-finance-priority'},
        {'label': 'Ver fila financeira', 'href': '#finance-queue-board', 'kind': 'secondary', 'data_action': 'open-tab-finance-queue'},
    ]
    if can_manage_finance:
        hero_actions.append({'label': 'Cadastrar plano', 'href': '#cadastro-plano', 'kind': 'secondary', 'data_action': 'open-tab-finance-portfolio'})
    else:
        hero_actions.append({'label': 'Ver carteira', 'href': '#finance-portfolio-board', 'kind': 'secondary', 'data_action': 'open-tab-finance-portfolio'})
    hero = build_page_hero(
        eyebrow='Caixa',
        title='Seu saldo.',
        copy='Controle receitas, mensalidades atrasadas e o pulso financeiro.',
        actions=hero_actions,
        aria_label='Panorama financeiro',
        classes=['operation-hero', 'finance-hero'],
    )

    return build_catalog_page_payload(
        context={
            'page_key': 'finance-center',
            'title': 'Financeiro',
            'subtitle': 'Planos, receita, retencao e sinais operacionais num so painel.',
            'mode': 'management' if can_manage_finance else 'read-only',
            'role_slug': current_role_slug,
        },
        shell={
            'shell_action_buttons': shell_action_buttons,
        },
        data={
            'hero': hero,
            'can_manage_finance': can_manage_finance,
            'finance_filter_form': filter_form,
            'finance_metrics': snapshot['finance_metrics'],
            'finance_pulse': finance_pulse,
            'interactive_kpis': snapshot.get('interactive_kpis', []),
            'plan_portfolio': plan_portfolio,
            'plan_mix': snapshot['plan_mix'],
            'monthly_comparison': snapshot['monthly_comparison'],
            'comparison_peaks': snapshot['comparison_peaks'],
            'financial_alerts': financial_alerts,
            'recent_movements': recent_movements,
            'operational_queue': operational_queue,
            'operational_metrics': operational_metrics,
            'finance_right_rail_snapshot': finance_right_rail_snapshot,
            'finance_right_rail_priority_badge': priority_badge,
            'finance_right_rail_priority_label': priority_label,
            'finance_filter_summary': build_finance_filter_summary(filter_form),
            'form': form,
        },
        actions={
            'finance_export_links': export_links,
        },
        capabilities={
            'can_manage_finance': can_manage_finance,
            'can_export_finance': current_role_slug in (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER),
        },
        assets=build_catalog_assets(css=['css/catalog/finance.css'], include_catalog_shared=True),
    )