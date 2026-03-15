"""
ARQUIVO: builders de page payload para workspaces operacionais.

POR QUE ELE EXISTE:
- unifica o contrato de operations com o mesmo shape usado no restante do front.
- mantem a view HTTP curta e previsivel mesmo quando a tela ainda consome aliases legados.
"""

from access.shell_actions import build_shell_action_buttons_from_focus
from shared_support.page_payloads import build_page_assets, build_page_hero, build_page_payload


def _build_operation_workspace_hero(page_key, snapshot):
    hero_map = {
        'operations-owner': build_page_hero(
            eyebrow='Leitura executiva do box',
            title='Crescimento, caixa e estrutura andando juntos.',
            copy='Crescimento, caixa e risco na mesma leitura.',
            actions=[
                {'label': 'Ver crescimento', 'href': '#owner-growth-board'},
                {'label': 'Ver risco de caixa', 'href': '#owner-risk-board', 'kind': 'secondary'},
                {'label': 'Ver estrutura pronta', 'href': '#owner-structure-board', 'kind': 'secondary'},
            ],
            side={
                'kind': 'stats-panel',
                'eyebrow': 'Pulso de agora',
                'copy': 'Pressão da base, entrada e cobrança.',
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
        'operations-reception-preview': build_page_hero(
            eyebrow='Preview oculto',
            title='Recepção por baixo dos panos.',
            copy='Balcao, grade e cobranca curta antes do rollout.',
            actions=[
                {'label': 'Ver cobranca curta', 'href': '#reception-payment-board'},
                {'label': 'Ver entradas', 'href': '#reception-intake-board', 'kind': 'secondary'},
                {'label': 'Ver grade em leitura', 'href': '#reception-class-grid-board', 'kind': 'secondary'},
            ],
            side={
                'kind': 'stats-panel',
                'eyebrow': 'Pulso do preview',
                'copy': 'Valide se a recepção sustenta entrada, caixa rápido e orientação de aulas.',
                'stats': snapshot.get('hero_stats'),
            },
            aria_label='Preview da recepção',
            classes=['reception-preview-hero'],
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