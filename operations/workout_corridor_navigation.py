"""
ARQUIVO: navegacao compartilhada do corredor de WOD.

POR QUE ELE EXISTE:
- mantem a navegacao do corredor consistente entre editor, aprovacao, historico e resumo.

O QUE ESTE ARQUIVO FAZ:
1. define tabs por papel.
2. centraliza os hrefs canônicos do corredor.
3. evita duplicacao de navegação nos builders de contexto.
"""

from django.urls import reverse

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER


_TAB_SPECS = (
    {
        'key': 'editor',
        'label': 'Editor',
        'route_name': 'workout-editor-home',
        'allowed_roles': {ROLE_COACH, ROLE_OWNER},
    },
    {
        'key': 'approval',
        'label': 'Aprovacoes',
        'route_name': 'workout-approval-board',
        'allowed_roles': {ROLE_MANAGER, ROLE_OWNER},
    },
    {
        'key': 'history',
        'label': 'Historico',
        'route_name': 'workout-publication-history',
        'allowed_roles': {ROLE_COACH, ROLE_MANAGER, ROLE_OWNER},
    },
    {
        'key': 'summary',
        'label': 'Resumo executivo',
        'route_name': 'operations-executive-summary',
        'allowed_roles': {ROLE_COACH, ROLE_MANAGER, ROLE_OWNER},
    },
)


def build_workout_corridor_tabs(*, current_key, current_role_slug, editor_href=''):
    tabs = []
    for spec in _TAB_SPECS:
        if current_role_slug not in spec['allowed_roles']:
            continue
        href = editor_href if spec['key'] == 'editor' and editor_href else reverse(spec['route_name'])
        tabs.append(
            {
                'key': spec['key'],
                'label': spec['label'],
                'href': href,
                'is_active': spec['key'] == current_key,
            }
        )
    return tuple(tabs)


__all__ = ['build_workout_corridor_tabs']
