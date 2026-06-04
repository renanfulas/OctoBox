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
                'title': 'Abra a régua assistida antes de descer para a fila automática.',
                'copy': f'{assisted_count} caso(s) já chegam com abordagem sugerida. Resolva essa camada primeiro e deixe a fila de {queue_count} alerta(s) para o que realmente sobrar de pressão.',
                'href': '#finance-priority-board',
                'href_label': 'Abrir régua ativa',
                'data_action': 'open-tab-finance-queue',
                'entry_surface': 'priority-rail',
                'entry_reason': 'Existe abordagem semiassistida pronta antes da fila automática.',
                'secondary_surface': 'queue-board',
            }
        return {
            'eyebrow': 'Primeiro movimento',
            'title': 'A fila automática virou a primeira porta desta leitura.',
            'copy': f'Não há régua assistida aberta agora. Entre direto na fila com {queue_count} alerta(s) e proteja o caixa antes de abrir carteira ou filtros.',
            'href': '#finance-queue-board',
            'href_label': 'Abrir fila financeira',
            'data_action': 'open-tab-finance-queue',
            'entry_surface': 'queue-board',
            'entry_reason': 'A pressão de caixa pede leitura direta da fila automática.',
            'secondary_surface': 'portfolio-board',
        }
    if dominant_key == 'movements':
        return {
            'eyebrow': 'Primeiro movimento',
            'title': 'Leia o caixa realizado e use a tendência para escolher o próximo mergulho.',
            'copy': 'Comece pelo raio-X financeiro, confirme movimentos recentes e só depois desça para fila ou carteira se o recorte pedir.',
            'href': '#finance-movements-board',
            'href_label': 'Abrir raio-X financeiro',
            'data_action': 'open-tab-finance-movements',
            'entry_surface': 'movements-board',
            'entry_reason': 'Sem pressão dominante na fila, o caixa realizado explica melhor o recorte.',
            'secondary_surface': 'queue-board',
        }
    return {
        'eyebrow': 'Primeiro movimento',
        'title': 'Comece pela carteira e deixe a fila para a segunda leitura.',
        'copy': 'Sem pressão dominante na fila ou no caixa, portfólio e mix explicam melhor o momento antes de abrir filtros ou cobranças.',
        'href': '#finance-portfolio-board',
        'href_label': 'Abrir carteira ativa',
        'data_action': 'open-tab-finance-portfolio',
        'entry_surface': 'portfolio-board',
        'entry_reason': 'Carteira e mix explicam mais do que movimentos curtos neste recorte.',
        'secondary_surface': 'queue-board',
    }


__all__ = ['build_finance_flow_bridge']
