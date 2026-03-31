"""
ARQUIVO: builders de page payload para workspaces operacionais.

POR QUE ELE EXISTE:
- unifica o contrato de operations com o mesmo shape usado no restante do front.
- mantem a view HTTP curta e previsivel mesmo quando a tela ainda consome aliases legados.
"""

from django.urls import reverse

from access.shell_actions import build_shell_action_buttons_from_focus
from shared_support.page_payloads import build_page_assets, build_page_hero, build_page_payload


def _build_owner_hero_content(snapshot):
    owner_focus = snapshot.get('owner_operational_focus') or []
    primary_focus = owner_focus[0] if owner_focus else {}
    primary_key = primary_focus.get('key')
    metrics = snapshot.get('headline_metrics') or {}

    if primary_key == 'intakes':
        return {
            'title': 'Novas entradas.',
            'copy': 'Existe demanda esperando resposta agora.' if metrics.get('pending_intakes') else 'A fila de entradas está limpa hoje.',
        }
    if primary_key == 'payments':
        return {
            'title': 'Seu caixa.',
            'copy': 'Há cobrança atrasada pedindo contato agora.' if metrics.get('overdue_payments') else 'As cobranças estão sob controle.',
        }
    return {
        'title': 'Operação ativa.',
        'copy': 'Confirme a estrutura ou responda novas demandas.',
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
                'href': owner_primary_focus.get('href', reverse('intake-center')),
            },
            *[
                {'label': item['href_label'], 'href': item['href'], 'kind': 'secondary'}
                for item in owner_focus[1:3]
            ],
        ]
    hero_map = {
        'operations-owner': build_page_hero(
            eyebrow='Comando',
            title=owner_hero['title'],
            copy=owner_hero['copy'],
            actions=owner_actions,
            aria_label='Comando do dia do owner',
        ),
        'operations-manager': build_page_hero(
            eyebrow='Gerência',
            title='Fila e fluxos.',
            copy='Resolva pendências, vínculos e cobranças abertas.',
            actions=[
                {'label': 'Ver alertas financeiros', 'href': '#manager-finance-board'},
                {'label': 'Ver entradas', 'href': '#manager-intake-board', 'kind': 'secondary'},
                {'label': 'Ver vinculos pendentes', 'href': '#manager-link-board', 'kind': 'secondary'},
            ],
            aria_label='Panorama da gerencia',
        ),
        'operations-coach': build_page_hero(
            eyebrow='Coach',
            title='Sua turma.',
            copy='Registre presenças e feche o diário do treino.',
            actions=[
                {'label': 'Ver aulas do dia', 'href': '#coach-sessions-board'},
            ],
            aria_label='Panorama do coach',
        ),
        'operations-dev': build_page_hero(
            eyebrow='Leitura técnica controlada',
            title='Rastro recente, fronteira, sistema inteiro.',
            copy='Rastro, fronteira e manutencao sem chute tecnico.',
            actions=[
                {'label': 'Ver eventos recentes', 'href': '#dev-audit-board'},
                {'label': 'Abrir mapa do sistema', 'href': reverse('system-map'), 'kind': 'secondary'},
            ],
            aria_label='Panorama de desenvolvimento',
        ),
        'operations-reception': build_page_hero(
            eyebrow='Recepção',
            title='Seu balcão.',
            copy='Acompanhe chegadas e acerte pagamentos curtos.',
            actions=[
                {'label': 'Ver cobranca curta', 'href': '#reception-payment-board', 'data_action': 'jump-reception-payments'},
                {'label': 'Ver entradas', 'href': '#reception-intake-board', 'kind': 'secondary', 'data_action': 'jump-reception-intakes'},
                {'label': 'Ver grade em leitura', 'href': '#reception-class-grid-board', 'kind': 'secondary', 'data_action': 'jump-reception-class-grid'},
            ],
            aria_label='Panorama da recepcao',
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
