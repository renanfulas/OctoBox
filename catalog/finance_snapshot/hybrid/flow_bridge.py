"""
ARQUIVO: ponte hibrida entre fila assistida e leitura tradicional do financeiro.
"""


def build_finance_flow_bridge(*, priority_context, operational_queue, financial_alerts):
    assisted_count = len(operational_queue or [])
    queue_count = len(financial_alerts or [])
    dominant_key = priority_context['dominant_key']

    if dominant_key == 'queue':
        if assisted_count > 0:
            return {
                'eyebrow': 'Primeiro movimento',
                'title': 'Abra a regua assistida antes de descer para a fila automatica.',
                'copy': f'{assisted_count} caso(s) ja chegam com abordagem sugerida. Resolva essa camada primeiro e deixe a fila de {queue_count} alerta(s) para o que realmente sobrar de pressao.',
                'href': '#finance-priority-board',
                'href_label': 'Abrir regua ativa',
                'data_action': 'open-tab-finance-queue',
                'entry_surface': 'priority-rail',
                'entry_reason': 'Existe abordagem semiassistida pronta antes da fila automatica.',
                'secondary_surface': 'queue-board',
            }
        return {
            'eyebrow': 'Primeiro movimento',
            'title': 'A fila automatica virou a primeira porta desta leitura.',
            'copy': f'Nao ha regua assistida aberta agora. Entre direto na fila com {queue_count} alerta(s) e proteja o caixa antes de abrir carteira ou filtros.',
            'href': '#finance-queue-board',
            'href_label': 'Abrir fila financeira',
            'data_action': 'open-tab-finance-queue',
            'entry_surface': 'queue-board',
            'entry_reason': 'A pressao de caixa pede leitura direta da fila automatica.',
            'secondary_surface': 'portfolio-board',
        }
    if dominant_key == 'movements':
        return {
            'eyebrow': 'Primeiro movimento',
            'title': 'Leia o caixa realizado e use a tendencia para escolher o proximo mergulho.',
            'copy': 'Comece pelo raio-X financeiro, confirme movimentos recentes e so depois desca para fila ou carteira se o recorte pedir.',
            'href': '#finance-movements-board',
            'href_label': 'Abrir raio-X financeiro',
            'data_action': 'open-tab-finance-movements',
            'entry_surface': 'movements-board',
            'entry_reason': 'Sem pressao dominante na fila, o caixa realizado explica melhor o recorte.',
            'secondary_surface': 'queue-board',
        }
    return {
        'eyebrow': 'Primeiro movimento',
        'title': 'Comece pela carteira e deixe a fila para a segunda leitura.',
        'copy': 'Sem pressao dominante na fila ou no caixa, portfolio e mix explicam melhor o momento antes de abrir filtros ou cobrancas.',
        'href': '#finance-portfolio-board',
        'href_label': 'Abrir carteira ativa',
        'data_action': 'open-tab-finance-portfolio',
        'entry_surface': 'portfolio-board',
        'entry_reason': 'Carteira e mix explicam mais do que movimentos curtos neste recorte.',
        'secondary_surface': 'queue-board',
    }


__all__ = ['build_finance_flow_bridge']
