"""
ARQUIVO: presenter da tela de grade de aulas.

POR QUE ELE EXISTE:
- tira da view HTTP a maior parte da montagem da fachada da grade.
- organiza a tela por contrato explicito para preparar a convergencia com page payload.
"""

from access.admin import admin_changelist_url
from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER
from shared_support.page_payloads import build_page_hero

from .shared import build_catalog_assets, build_catalog_page_payload


def build_class_grid_page(*, base_context, snapshot, schedule_form, selected_session, session_edit_form, current_query_string):
    role_slug = base_context['current_role'].slug
    can_manage_classes = role_slug in (ROLE_OWNER, ROLE_MANAGER)
    can_open_class_admin = role_slug in (ROLE_OWNER, ROLE_DEV)
    hero = build_page_hero(
        eyebrow='Aulas',
        title='Grade em leitura.',
        copy='Veja o ritmo do dia, a pressao da semana e onde ajustar sem ruido.',
        actions=[
            {'label': 'Ver hoje', 'href': '#today-board'},
            {'label': 'Ver semana', 'href': '#class-weekly-modal', 'kind': 'secondary', 'data_action': 'open-weekly-modal-full'},
            {'label': 'Ver m\u00eas', 'href': '#class-monthly-modal', 'kind': 'secondary', 'data_action': 'open-monthly-calendar'},
            {'label': 'Abrir planejamento', 'href': '#planner-board', 'kind': 'secondary'},
        ],
        aria_label='Panorama da grade',
        classes=['class-grid-hero'],
        contract={'max_primary_actions': 4},
    )
    payload = build_catalog_page_payload(
        context={
            'page_key': 'class-grid',
            'title': 'Grade de aulas',
            'subtitle': 'Agenda, lotacao e ajuste de janela numa leitura curta.',
            'mode': 'management' if can_manage_classes else 'read-only',
            'role_slug': role_slug,
            'today': base_context['today'],
        },
        data={
            'hero': hero,
            'grouped_sessions': snapshot['grouped_sessions'],
            'today_schedule': snapshot['today_schedule'],
            'weekly_calendar': snapshot['weekly_calendar'],
            'monthly_calendar': snapshot['monthly_calendar'],
            'class_metrics': snapshot['class_metrics'],
            'selected_month_label': snapshot['selected_month_label'],
            'schedule_form': schedule_form,
            'selected_session': selected_session,
            'session_edit_form': session_edit_form,
        },
        actions={
            'anchors': {
                'today': '#today-board',
                'weekly': '#class-weekly-modal',
                'monthly': '#class-monthly-modal',
                'planner': '#planner-board',
            },
            'admin': admin_changelist_url('boxcore', 'classsession') if can_open_class_admin else None,
        },
        behavior={
            'workspace_storage_key': 'octobox-class-grid-layout-v2',
            'current_query_string': current_query_string,
        },
        capabilities={
            'can_manage_classes': can_manage_classes,
            'can_open_class_admin': can_open_class_admin,
        },
        assets=build_catalog_assets(
            css=['css/catalog/class-grid.css'],
            js=['js/pages/class-grid/class-grid.js'],
            include_catalog_shared=True,
        ),
    )
    return payload
