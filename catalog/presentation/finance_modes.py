"""
ARQUIVO: contrato de modos da central financeira.

POR QUE ELE EXISTE:
- explicita na UI e no payload a diferenca entre leitura tradicional, assistida e hibrida.
"""


def build_finance_mode_contract(
    *,
    finance_follow_up_analytics,
):
    analytics_summary = finance_follow_up_analytics.get('summary', {}) or {}
    tracked_realized_count = (
        (finance_follow_up_analytics.get('turn_recommendation_adherence') or {}).get('tracked_realized_count', 0)
        or analytics_summary.get('realized_count', 0)
        or 0
    )
    active_mode = 'hybrid'

    modes = [
        {
            'key': 'traditional',
            'label': 'Modo tradicional',
            'kicker': 'Fato operacional',
            'summary': 'Abre so o que e factual e direto para decidir.',
            'detail': 'Leitura objetiva do que aconteceu, sem a camada de recomendacao assistida.',
            'badge': '3 blocos',
            'is_active': active_mode == 'traditional',
            'surface_count': 3,
        },
        {
            'key': 'hybrid',
            'label': 'Modo hibrido',
            'kicker': 'Acao com contexto',
            'summary': 'Abre o factual junto da leitura assistida no mesmo contexto.',
            'detail': 'E a visao mais completa do turno, com fato e IA lado a lado para decidir rapido.',
            'badge': 'Vista completa',
            'is_active': active_mode == 'hybrid',
            'surface_count': 5,
        },
        {
            'key': 'ai',
            'label': 'Modo IA',
            'kicker': 'Aprendizado historico',
            'summary': 'Abre so o aprendizado e a leitura assistida da maquina.',
            'detail': 'Foca no que o historico sugere e no que o time tem aprendido com a execucao.',
            'badge': f'{tracked_realized_count} follow-up(s)',
            'is_active': active_mode == 'ai',
            'surface_count': 1,
        },
    ]

    return {
        'active_mode': active_mode,
        'headline': 'Escolha como voce quer ler o financeiro.',
        'summary': 'Tradicional abre o factual. Hibrido junta factual e IA. IA abre so a leitura assistida.',
        'modes': modes,
    }


__all__ = ['build_finance_mode_contract']
