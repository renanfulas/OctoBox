"""
ARQUIVO: leitura executiva do corredor pos-publicacao do WOD.

POR QUE ELE EXISTE:
- tira de `workout_published_history.py` o fechamento executivo do caso.

O QUE ESTE ARQUIVO FAZ:
1. resume memorias operacionais do caso.
2. calcula o fechamento executivo a partir de alertas e follow-up.

PONTOS CRITICOS:
- manter o mesmo shape de retorno usado pela board.
"""

from django.utils import timezone


def build_operational_memory_digest(memories):
    digest = []
    for memory in memories[:4]:
        actor_label = ''
        if memory.created_by is not None:
            actor_label = memory.created_by.get_full_name() or memory.created_by.username
        digest.append(
            {
                'kind_label': memory.get_kind_display(),
                'note': memory.note,
                'created_at_label': timezone.localtime(memory.created_at).strftime('%d/%m %H:%M'),
                'actor_label': actor_label,
            }
        )
    return digest


def build_executive_case_closure(*, runtime_label, alerts, follow_up_actions):
    has_open_action = False
    has_monitoring = False
    has_not_resolved = False
    for action in follow_up_actions:
        result = action.get('result')
        if result is None:
            has_open_action = True
            continue
        if result['monitor_status'] == 'monitoring':
            has_monitoring = True
        elif result['monitor_status'] == 'not_resolved':
            has_not_resolved = True

    if has_not_resolved or (alerts and runtime_label == 'Aula em andamento'):
        return {
            'status': 'strong_intervention',
            'label': 'Intervencao forte',
            'tone': 'danger',
            'summary': 'Esse caso ainda pede resposta forte da operacao para nao contaminar a experiencia da aula.',
        }
    if has_open_action:
        return {
            'status': 'awaiting_action',
            'label': 'Aguardando acao',
            'tone': 'warning',
            'summary': 'A leitura do risco ja existe, mas ainda falta uma resposta registrada para fechar o ciclo.',
        }
    if has_monitoring or alerts:
        return {
            'status': 'monitoring',
            'label': 'Acompanhando',
            'tone': 'accent',
            'summary': 'Ja houve resposta operacional, mas o caso ainda merece vigia curta antes de ser dado como absorvido.',
        }
    return {
        'status': 'absorbed',
        'label': 'Absorvido',
        'tone': 'success',
        'summary': 'A operacao absorveu o caso e nao ha sinal vivo pedindo nova escalada agora.',
    }
