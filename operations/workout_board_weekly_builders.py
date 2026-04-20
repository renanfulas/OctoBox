"""
ARQUIVO: builders semanais e executivos da board de aprovacao do WOD.

POR QUE ELE EXISTE:
- tira de `workout_board_builders.py` o corredor de leitura semanal e governanca executiva.
"""

from datetime import timedelta

from student_app.models import WorkoutWeeklyCheckpointClosure, WorkoutWeeklyCheckpointStatus


def build_weekly_executive_summary(*, history_items, management_priority, recommendations, trend_cards, now):
    week_floor = now - timedelta(days=7)
    weekly_items = [item for item in history_items if item.get('published_at') and item['published_at'] >= week_floor]
    if not weekly_items:
        weekly_items = history_items

    top_entry = management_priority.get('top_entry') if management_priority else None
    top_recommendation = recommendations[0] if recommendations else None
    positive_trend = next((card for card in trend_cards if card.get('trend_label') == 'Melhora recente'), None)

    adjustment_label = top_entry['label'] if top_entry else 'Nenhum corredor pediu ajuste forte acima da linha de ruido'
    improvement_label = positive_trend['label'] if positive_trend else 'Nenhuma melhora consistente ficou clara nesta janela'
    action_label = top_recommendation['label'] if top_recommendation else 'Manter observacao curta sem nova recomendacao principal'

    total_weekly = len(weekly_items)
    summary = (
        f'Nesta semana, o principal ponto de ajuste foi {adjustment_label.lower()}. '
        f'O melhor sinal de melhora veio de {improvement_label.lower()}. '
        f'A recomendacao principal virou {action_label.lower()}.'
    )
    return {
        'label': 'Resumo executivo semanal do box',
        'summary': summary,
        'weekly_total': total_weekly,
        'adjustment_label': adjustment_label,
        'improvement_label': improvement_label,
        'action_label': action_label,
    }


def build_weekly_checkpoint_rhythm(*, checkpoint_history):
    if not checkpoint_history:
        return []

    rhythm_cards = []
    current = checkpoint_history[0]
    previous = checkpoint_history[1] if len(checkpoint_history) > 1 else None

    if previous and current['execution_status'] != previous['execution_status']:
        rhythm_cards.append(
            {
                'tone': 'info' if current['execution_status'] == WorkoutWeeklyCheckpointStatus.COMPLETED else 'accent',
                'label': 'Virada de execucao',
                'summary': (
                    f"O checkpoint saiu de {previous['execution_status_label'].lower()} "
                    f"para {current['execution_status_label'].lower()} na semana de {current['week_label']}."
                ),
            }
        )

    recent_closures = [item['closure_status'] for item in checkpoint_history[:3] if item.get('closure_status')]
    if len(recent_closures) >= 2 and all(status == WorkoutWeeklyCheckpointClosure.PARTIAL for status in recent_closures):
        rhythm_cards.append(
            {
                'tone': 'warning',
                'label': 'Sequencia parcial',
                'summary': 'As ultimas semanas estao fechando como parcial. Vale revisar se a recomendacao esta grande demais ou sem dono forte.',
            }
        )

    if len(recent_closures) >= 2 and all(status == WorkoutWeeklyCheckpointClosure.WORKED for status in recent_closures):
        rhythm_cards.append(
            {
                'tone': 'success',
                'label': 'Sequencia funcionando',
                'summary': 'As ultimas semanas estao fechando com resultado positivo. Vale consolidar esse ritual como padrao de gestao.',
            }
        )

    return rhythm_cards[:3]


def build_weekly_checkpoint_maturity(*, checkpoint_history, rhythm_cards):
    if not checkpoint_history:
        return {
            'label': 'Maturidade operacional',
            'tone': 'accent',
            'state_label': 'Base curta',
            'summary': 'Ainda nao ha semanas suficientes para ler a maturidade do ritual com firmeza.',
        }

    recent_closures = [item['closure_status'] for item in checkpoint_history[:3] if item.get('closure_status')]
    recent_execution = [item['execution_status'] for item in checkpoint_history[:3] if item.get('execution_status')]
    rhythm_labels = {card['label'] for card in rhythm_cards}

    if len(recent_closures) >= 2 and all(status == WorkoutWeeklyCheckpointClosure.WORKED for status in recent_closures):
        return {
            'label': 'Maturidade operacional',
            'tone': 'success',
            'state_label': 'Saudavel',
            'summary': 'O ritual semanal esta fechando bem nas ultimas semanas e mostra cara de rotina madura, nao de improviso.',
        }

    if 'Sequencia parcial' in rhythm_labels or len({status for status in recent_execution[:2]}) > 1:
        return {
            'label': 'Maturidade operacional',
            'tone': 'warning',
            'state_label': 'Instavel',
            'summary': 'O ritual mostra oscilacao ou fechamento parcial repetido. Ele existe, mas ainda nao virou trilho confiavel.',
        }

    if len(recent_execution) >= 2 and all(status == WorkoutWeeklyCheckpointStatus.NOT_STARTED for status in recent_execution[:2]):
        return {
            'label': 'Maturidade operacional',
            'tone': 'danger',
            'state_label': 'Travado',
            'summary': 'O ritual semanal esta travando antes de ganhar corpo. Vale destravar dono, cadencia e fechamento.',
        }

    return {
        'label': 'Maturidade operacional',
        'tone': 'info',
        'state_label': 'Em formacao',
        'summary': 'O ritual esta ganhando forma, mas ainda precisa de repeticao consistente para virar padrao confiavel.',
    }


def build_weekly_governance_action(*, maturity):
    state = maturity.get('state_label')
    if state == 'Saudavel':
        return {
            'tone': 'success',
            'label': 'Formalizar ritual como padrao do box',
            'summary': 'O ritual ja mostra repeticao suficiente para sair do improviso e virar combinacao oficial da operacao.',
            'cadence': 'Levar para padrao nas proximas 2 semanas',
        }
    if state == 'Travado':
        return {
            'tone': 'danger',
            'label': 'Abrir destrave executivo do ritual',
            'summary': 'O ritual esta travando por semanas e precisa de dono forte, cadencia clara e fechamento obrigatorio.',
            'cadence': 'Atacar nas proximas 48h',
        }
    if state == 'Instavel':
        return {
            'tone': 'warning',
            'label': 'Rodar ajuste curto antes de formalizar',
            'summary': 'O ritual existe, mas ainda oscila. Vale reduzir variacao antes de transformar isso em regra da casa.',
            'cadence': 'Revisar ainda nesta semana',
        }
    if state == 'Base curta':
        return {
            'tone': 'accent',
            'label': 'Observar mais uma janela antes de governar',
            'summary': 'Ainda falta base para mexer em governanca com firmeza. Melhor completar mais uma rodada curta.',
            'cadence': 'Reavaliar na proxima semana',
        }
    return {
        'tone': 'info',
        'label': 'Manter ritual em formacao assistida',
        'summary': 'O ritual esta ganhando corpo. Vale acompanhar com dono claro antes de formalizar ou escalar.',
        'cadence': 'Acompanhar nos proximos 7 dias',
    }
