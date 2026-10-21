"""
ARQUIVO: navegacao compartilhada das duas superficies principais de WOD.

POR QUE ELE EXISTE:
- mantém a navegacao consistente entre WOD Semana e Calendario; rotas de apoio nao viram abas primarias.

O QUE ESTE ARQUIVO FAZ:
1. define tabs por papel.
2. centraliza os hrefs canonicos do corredor.
3. evita duplicacao de navegacao nos builders de contexto.
"""

from django.urls import reverse

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER


_TAB_SPECS = (
    {
        'key': 'smart_paste',
        'label': 'WOD Semana',
        'route_name': 'workout-smart-paste',
        'allowed_roles': {ROLE_COACH, ROLE_MANAGER, ROLE_OWNER},
    },
    {
        'key': 'planner',
        'label': 'Calendário',
        'route_name': 'workout-planner',
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
