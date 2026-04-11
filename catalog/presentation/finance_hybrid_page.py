"""
ARQUIVO: presenter da camada hibrida da central financeira.

POR QUE ELE EXISTE:
- organiza a ponte visual entre leitura tradicional e leitura assistida.
"""

from shared_support.page_payloads import build_page_hero


def build_finance_operational_focus(*, finance_priority_context, operational_queue, financial_alerts, finance_pulse):
    return [
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
            'href': '#finance-priority-board' if operational_queue else '#finance-queue-board',
            'href_label': 'Abrir regua' if operational_queue else 'Abrir fila',
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


def build_finance_hero(*, finance_priority_context, has_operational_queue):
    hero_actions = [
        {
            'label': 'Ver prioridades',
            'href': '#finance-priority-board' if has_operational_queue else '#finance-queue-board',
            'kind': 'primary',
            'data_action': 'open-tab-finance-queue',
        },
        {
            'label': 'Abrir carteira',
            'href': '#finance-portfolio-board',
            'kind': 'secondary',
            'data_action': 'open-tab-finance-portfolio',
        },
    ]

    dominant_key = finance_priority_context.get('dominant_key')
    if dominant_key == 'portfolio':
        hero_title = 'Carteira em leitura.'
    elif dominant_key == 'queue':
        hero_title = 'Fila financeira.'
    else:
        hero_title = 'Financeiro ativo.'

    return build_page_hero(
        eyebrow='Financeiro',
        title=hero_title,
        copy='Veja a pressao dominante, abra a primeira passagem e desca sem ruido.',
        actions=hero_actions,
        aria_label='Panorama financeiro',
        classes=['finance-hero'],
        heading_level='h1',
    )


__all__ = ['build_finance_hero', 'build_finance_operational_focus']
