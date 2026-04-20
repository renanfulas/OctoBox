"""
ARQUIVO: builders de page payload para workspaces operacionais.

POR QUE ELE EXISTE:
- unifica o contrato de operations com o mesmo shape usado no restante do front.
- mantém a view HTTP curta e previsível mesmo quando a tela ainda consome aliases legados.
"""

from django.urls import reverse

from shared_support.page_payloads import (
    build_page_assets,
    build_page_hero,
    build_page_payload,
    build_page_reading_panel,
    resolve_primary_href,
)


def _build_hero_actions_from_entry_context(entry_context=None, *, tertiary_action=None):
    entry_context = entry_context or {}
    actions = []

    if entry_context.get('entry_href'):
        actions.append(
            {
                'label': entry_context.get('entry_href_label') or 'Abrir agora',
                'href': entry_context['entry_href'],
                'kind': 'primary',
            }
        )

    if entry_context.get('secondary_href'):
        actions.append(
            {
                'label': entry_context.get('secondary_href_label') or 'Abrir depois',
                'href': entry_context['secondary_href'],
                'kind': 'secondary',
            }
        )

    if tertiary_action:
        actions.append(tertiary_action)

    return actions


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
        'copy': 'Confirme a estrutura ou responda a novas demandas.',
    }


def _build_operation_workspace_hero(page_key, snapshot):
    owner_focus = snapshot.get('owner_operational_focus') or []
    owner_primary_focus = owner_focus[0] if owner_focus else None
    owner_entry_context = snapshot.get('owner_decision_entry_context') or {}
    owner_hero = _build_owner_hero_content(snapshot)
    owner_actions = _build_hero_actions_from_entry_context(
        owner_entry_context,
        tertiary_action=(
            {
                'label': owner_focus[2].get('href_label', 'Abrir apoio'),
                'href': owner_focus[2].get('href', reverse('student-directory')),
                'kind': 'secondary',
            }
            if len(owner_focus) > 2 else None
        ),
    )
    if not owner_actions and owner_primary_focus:
        owner_actions = [
            {
                'label': owner_primary_focus.get('href_label', 'Abrir agora'),
                'href': owner_primary_focus.get('href', reverse('intake-center')),
            },
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
            title='Sua gerência, em foco.',
            copy='Veja triagem, vínculos e caixa na ordem certa, sem perder o ritmo.',
            actions=_build_hero_actions_from_entry_context(snapshot.get('manager_decision_entry_context')),
            aria_label='Panorama da gerência',
            classes=['manager-hero'],
            data_panel='manager-hero',
            actions_slot='manager-hero-actions',
        ),
        'operations-coach': build_page_hero(
            eyebrow='Coach',
            title='Turno ativo.',
            copy='Veja agenda, presença e ocorrência sem ruído.',
            actions=_build_hero_actions_from_entry_context(snapshot.get('coach_decision_entry_context'))[:1],
            aria_label='Panorama do coach',
            classes=['coach-hero'],
            data_panel='coach-hero',
            actions_slot='coach-hero-actions',
        ),
        'operations-dev': build_page_hero(
            eyebrow='Sistema',
            title='Leitura técnica controlada.',
            copy='Veja rastro, fronteira e manutenção sem chute técnico.',
            actions=[
                {'label': 'Ver eventos recentes', 'href': '#dev-audit-board'},
                {'label': 'Abrir mapa do sistema', 'href': reverse('system-map'), 'kind': 'secondary'},
            ],
            aria_label='Panorama de desenvolvimento',
            classes=['dev-hero'],
            data_panel='dev-hero',
            actions_slot='dev-hero-actions',
        ),
        'operations-reception': build_page_hero(
            eyebrow='Recepção',
            title='Seu balcão, em foco.',
            copy='Veja quem atender primeiro, resolva cobranças curtas e oriente a próxima aula sem travar o atendimento.',
            actions=_build_hero_actions_from_entry_context(
                snapshot.get('reception_decision_entry_context'),
                tertiary_action={
                    'label': 'Ver próximas aulas',
                    'href': '#reception-class-grid-board',
                    'kind': 'secondary',
                },
            ),
            aria_label='Panorama da recepção',
            classes=['reception-hero'],
            data_panel='reception-hero',
            actions_slot='reception-jump-links',
        ),
    }
    return hero_map[page_key]


def _build_operation_workspace_reading_panel(page_key, snapshot):
    owner_decision_entry_context = snapshot.get('owner_decision_entry_context') or {}
    owner_priority_context = snapshot.get('owner_priority_context') or {}
    manager_priority_context = snapshot.get('manager_priority_context') or {}
    manager_decision_entry_context = snapshot.get('manager_decision_entry_context') or {}
    coach_decision_entry_context = snapshot.get('coach_decision_entry_context') or {}
    reception_decision_entry_context = snapshot.get('reception_decision_entry_context') or {}
    reception_focus_visible = [
        item
        for item in (snapshot.get('reception_focus') or [])
        if (item.get('count') or 0) > 0
    ]

    def _resolve_primary_href(items, fallback):
        for item in items or []:
            if item.get('is_clickable', True):
                return item.get('href') or fallback
        return ''

    panel_map = {
        'operations-owner': build_page_reading_panel(
            items=snapshot.get('owner_operational_focus'),
            primary_href=resolve_primary_href(snapshot.get('owner_operational_focus'), owner_decision_entry_context.get('entry_href')),
            pill_label=owner_priority_context.get('pill_label'),
            pill_class=owner_priority_context.get('pill_class'),
            class_name='owner-command-panel',
            panel_id='owner-command-lane',
        ),
        'operations-manager': build_page_reading_panel(
            items=snapshot.get('manager_operational_focus'),
            primary_href=manager_decision_entry_context.get('entry_href'),
            pill_label=manager_priority_context.get('pill_label'),
            pill_class=manager_priority_context.get('pill_class'),
            class_name='manager-command-panel',
            panel_id='manager-command-lane',
        ),
        'operations-coach': build_page_reading_panel(
            items=snapshot.get('coach_operational_focus'),
            primary_href='',
            pill_label='Ritmo do coach',
            pill_class='accent',
            unwrap=True,
        ),
        'operations-dev': build_page_reading_panel(
            items=snapshot.get('dev_operational_focus'),
            primary_href='#dev-audit-board',
            pill_label='Leitura técnica',
            pill_class='accent',
            class_name='dev-focus-lane',
            panel_id='dev-command-lane',
        ),
        'operations-reception': build_page_reading_panel(
            items=reception_focus_visible,
            primary_href=resolve_primary_href(reception_focus_visible, reception_decision_entry_context.get('entry_href')),
            pill_label='Atendimento vivo',
            pill_class='accent',
            class_name='reception-command-panel',
            panel_id='reception-command-lane',
        ),
    }
    return panel_map.get(page_key)


def build_operation_workspace_page(*, page_key, title, subtitle, scope, snapshot, current_role_slug, focus_key, capabilities=None):
    focus = snapshot.get(focus_key) or []
    transport_payload = snapshot.get('transport_payload') or {}
    return build_page_payload(
        context={
            'page_key': page_key,
            'title': title,
            'subtitle': subtitle,
            'mode': 'workspace',
            'role_slug': current_role_slug,
        },
        data={
            **snapshot,
            **transport_payload,
            'transport_payload': transport_payload,
            'hero': _build_operation_workspace_hero(page_key, snapshot),
            'reading_panel': _build_operation_workspace_reading_panel(page_key, snapshot),
        },
        behavior={
            'surface_key': page_key,
            'scope': scope,
            'snapshot_version': snapshot.get('snapshot_version', ''),
        },
        capabilities=capabilities or {},
        assets=build_page_assets(css=['css/design-system/operations.css']),
    )
