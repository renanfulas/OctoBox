"""
ARQUIVO: builders de page payload para workspaces operacionais.

POR QUE ELE EXISTE:
- unifica o contrato de operations com o mesmo shape usado no restante do front.
- mantem a view HTTP curta e previsivel mesmo quando a tela ainda consome aliases legados.
"""

from access.shell_actions import build_shell_action_buttons_from_focus
from shared_support.page_payloads import build_page_assets, build_page_hero, build_page_payload


def _build_owner_hero_content(snapshot):
    owner_focus = snapshot.get('owner_operational_focus') or []
    primary_focus = owner_focus[0] if owner_focus else {}
    primary_key = primary_focus.get('key')
    metrics = snapshot.get('headline_metrics') or {}

    if primary_key == 'intakes':
        return {
            'title': 'Abra as entradas.',
            'copy': (
                'Tem gente esperando resposta agora.'
                if metrics.get('pending_intakes')
                else 'A fila de entradas esta limpa agora.'
            ),
        }
    if primary_key == 'payments':
        return {
            'title': 'Veja as cobrancas.',
            'copy': (
                'Tem cobranca atrasada pedindo contato agora.'
                if metrics.get('overdue_payments')
                else 'As cobrancas atrasadas nao pedem acao agora.'
            ),
        }
    return {
        'title': 'Confirme a base.',
        'copy': 'Veja se WhatsApp, historico e estrutura continuam no lugar.',
    }


def _build_operation_workspace_hero(page_key, snapshot):
    owner_focus = snapshot.get('owner_operational_focus') or []
    owner_primary_focus = owner_focus[0] if owner_focus else None
    owner_hero = _build_owner_hero_content(snapshot)
    owner_actions = []
    if owner_primary_focus:
        owner_actions = [
            {
                'label': owner_primary_focus.get('href_label', 'Abrir agora'),
                'href': owner_primary_focus.get('href', '#owner-growth-board'),
            },
            *[
                {'label': item['href_label'], 'href': item['href'], 'kind': 'secondary'}
                for item in owner_focus[1:3]
            ],
        ]
    hero_map = {
        'operations-owner': build_page_hero(
            eyebrow='Agora',
            title=owner_hero['title'],
            copy=owner_hero['copy'],
            actions=owner_actions,
            side={
                'kind': 'stats-panel',
                'eyebrow': 'Resumo rapido',
                'copy': 'Quatro numeros para saber se o dia esta sob controle.',
                'stats': snapshot.get('hero_stats'),
            },
            aria_label='Panorama do dono',
        ),
        'operations-manager': build_page_hero(
            eyebrow='Centro do manager',
            title='Triagem, vínculo e cobrança, nessa ordem.',
            copy='Triagem, vinculo e cobranca na ordem que destrava a fila.',
            actions=[
                {'label': 'Ver alertas financeiros', 'href': '#manager-finance-board'},
                {'label': 'Ver entradas', 'href': '#manager-intake-board', 'kind': 'secondary'},
                {'label': 'Ver vinculos pendentes', 'href': '#manager-link-board', 'kind': 'secondary'},
            ],
            side={
                'kind': 'stats-panel',
                'eyebrow': 'Fila operacional',
                'copy': 'Pontos que pedem ação antes que a rotina trave.',
                'stats': snapshot.get('hero_stats'),
            },
            aria_label='Panorama da gerencia',
        ),
        'operations-coach': build_page_hero(
            eyebrow='Rotina do coach',
            title='Abra o dia, registre presença, feche a turma.',
            copy='Agenda, presenca e ocorrencia sem perder o compasso do turno.',
            actions=[
                {'label': 'Ver aulas do dia', 'href': '#coach-sessions-board'},
            ],
            side={
                'kind': 'stats-panel',
                'eyebrow': 'Turno de hoje',
                'copy': 'Agenda e rotina do turno.',
                'stats': snapshot.get('hero_stats'),
            },
            aria_label='Panorama do coach',
        ),
        'operations-dev': build_page_hero(
            eyebrow='Leitura técnica controlada',
            title='Rastro recente, fronteira, sistema inteiro.',
            copy='Rastro, fronteira e manutencao sem chute tecnico.',
            actions=[
                {'label': 'Ver eventos recentes', 'href': '#dev-audit-board'},
                {'label': 'Abrir mapa do sistema', 'href': '/mapa-sistema/', 'kind': 'secondary'},
            ],
            side={
                'kind': 'stats-panel',
                'eyebrow': 'Telemetria rápida',
                'copy': 'Volume de rastros e cobertura por papel.',
                'stats': snapshot.get('hero_stats'),
            },
            aria_label='Panorama de desenvolvimento',
        ),
        'operations-reception': build_page_hero(
            eyebrow='Centro da recepcao',
            title='Quem chegou, qual aula importa e qual cobrança cabe no balcão.',
            copy='Chegada, aula e caixa curto no compasso do balcao.',
            actions=[
                {'label': 'Ver cobranca curta', 'href': '#reception-payment-board', 'data_action': 'jump-reception-payments'},
                {'label': 'Ver entradas', 'href': '#reception-intake-board', 'kind': 'secondary', 'data_action': 'jump-reception-intakes'},
                {'label': 'Ver grade em leitura', 'href': '#reception-class-grid-board', 'kind': 'secondary', 'data_action': 'jump-reception-class-grid'},
            ],
            side={
                'kind': 'stats-panel',
                'eyebrow': 'Pulso do balcão',
                'copy': 'Decida se o turno pede acolhimento, caixa curto ou orientação de agenda.',
                'stats': snapshot.get('hero_stats'),
                'data_panel': 'reception-pulse-panel',
            },
            aria_label='Panorama da recepção',
            classes=['reception-hero'],
            data_panel='reception-hero',
            actions_slot='reception-jump-links',
        ),
    }
    return hero_map[page_key]


def build_operation_workspace_page(*, page_key, title, subtitle, scope, snapshot, current_role_slug, focus_key, capabilities=None):
    focus = snapshot.get(focus_key) or []
    return build_page_payload(
        context={
            'page_key': page_key,
            'title': title,
            'subtitle': subtitle,
            'mode': 'workspace',
            'role_slug': current_role_slug,
        },
        shell={
            'shell_action_buttons': build_shell_action_buttons_from_focus(focus=focus, scope=scope),
        },
        data={
            **snapshot,
            'hero': _build_operation_workspace_hero(page_key, snapshot),
        },
        capabilities=capabilities or {},
        assets=build_page_assets(css=['css/design-system/operations.css']),
    )