"""
ARQUIVO: contrato de modos da central financeira.

POR QUE ELE EXISTE:
- explicita na UI e no payload a diferenca entre leitura tradicional, assistida e hibrida.
"""


def build_finance_mode_contract(*, default_panel, operational_queue, financial_alerts, finance_follow_up_analytics):
    analytics_summary = finance_follow_up_analytics.get('summary', {}) or {}
    tracked_realized_count = (
        (finance_follow_up_analytics.get('turn_recommendation_adherence') or {}).get('tracked_realized_count', 0)
        or analytics_summary.get('realized_count', 0)
        or 0
    )
    active_mode = 'hybrid' if default_panel == 'tab-finance-queue' else 'traditional'

    modes = [
        {
            'key': 'traditional',
            'label': 'Modo tradicional',
            'kicker': 'Fato operacional',
            'summary': 'Metricas, movimentos, carteira e filtros para leitura objetiva do caixa.',
            'detail': 'O que aconteceu e onde a operacao aperta sem interpretacao assistida.',
            'href': '#tab-finance-movements',
            'href_label': 'Abrir leitura factual',
            'badge': '3 blocos',
            'is_active': active_mode == 'traditional',
            'surface_count': 3,
        },
        {
            'key': 'hybrid',
            'label': 'Modo hibrido',
            'kicker': 'Acao com contexto',
            'summary': 'Fila do turno com regua pronta, prioridade operacional e leitura contextual.',
            'detail': 'Onde fato e recomendacao assistida aparecem lado a lado para decidir rapido.',
            'href': '#tab-finance-queue',
            'href_label': 'Abrir fila guiada',
            'badge': f"{len(operational_queue) + len(financial_alerts)} caso(s)",
            'is_active': active_mode == 'hybrid',
            'surface_count': 2,
        },
        {
            'key': 'ai',
            'label': 'Modo IA',
            'kicker': 'Aprendizado historico',
            'summary': 'Placar de follow-up, melhor jogada do turno e leitura de divergencia acumulada.',
            'detail': 'Mostra o que o historico sugere, sem confundir isso com verdade transacional.',
            'href': '#finance-ai-board',
            'href_label': 'Abrir leitura assistida',
            'badge': f'{tracked_realized_count} follow-up(s)',
            'is_active': False,
            'surface_count': 1,
        },
    ]

    surface_modes = {
        'tab-finance-movements': 'traditional',
        'tab-finance-portfolio': 'traditional',
        'tab-finance-filters': 'traditional',
        'tab-finance-queue': 'hybrid',
        'finance-priority-board': 'hybrid',
        'finance-ai-board': 'ai',
    }

    return {
        'active_mode': active_mode,
        'headline': 'Escolha a lente antes de afundar nos blocos.',
        'summary': 'Tradicional mostra o fato. IA mostra o aprendizado. Hibrido junta os dois para orientar a acao.',
        'modes': modes,
        'surface_modes': surface_modes,
    }


__all__ = ['build_finance_mode_contract']
