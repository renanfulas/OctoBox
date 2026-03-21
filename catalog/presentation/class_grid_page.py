"""
ARQUIVO: presenter da tela de grade de aulas.

POR QUE ELE EXISTE:
- tira da view HTTP a maior parte da montagem da fachada da grade.
- organiza a tela por contrato explicito para preparar a convergencia com page payload.
"""

from access.admin import admin_changelist_url
from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER
from access.shell_actions import build_shell_action_buttons_from_focus
from shared_support.page_payloads import build_page_hero

from .shared import build_catalog_assets, build_catalog_page_payload


def _build_operational_focus(*, today_schedule, grouped_sessions, monthly_calendar, can_manage_classes):
    today_sessions = today_schedule['sessions'] if today_schedule else []
    today_pressure_count = sum(
        1
        for item in today_sessions
        if item['occupied_slots'] >= item['capacity'] or item['occupancy_percent'] >= 85
    )
    busiest_day = max(grouped_sessions, key=lambda item: len(item['sessions']), default=None)
    busy_days = sum(
        1
        for week in monthly_calendar
        for day in week
        if day['is_in_month'] and day['session_count'] >= 8
    )
    free_days = sum(
        1
        for week in monthly_calendar
        for day in week
        if day['is_in_month'] and day['session_count'] == 0
    )

    return [
        {
            'title': 'Comece pelo ritmo de hoje',
            'chip_label': 'Hoje',
            'summary': (
                f"{len(today_sessions)} aula(s) no dia e {today_pressure_count} horário(s) com lotação alta."
                if today_schedule else
                'Nenhuma aula marcada hoje. Revise a semana para evitar surpresas.'
            ),
            'count': len(today_sessions) if today_schedule else None,
            'action_label': 'Ver agenda de hoje',
            'action_href': '#today-board',
            'href': '#today-board',
        },
        {
            'title': 'Leia o pico da semana',
            'chip_label': 'Semana',
            'summary': (
                f"O pico cai em {busiest_day['date'].strftime('%d/%m')} com {len(busiest_day['sessions'])} aula(s)."
                if busiest_day else
                'Nenhum pico de agenda identificado na janela atual.'
            ),
            'action_label': 'Ver visão semanal',
            'action_href': '#weekly-board',
            'href': '#weekly-board',
        },
        {
            'title': 'Ajuste o mês',
            'chip_label': 'Planejar',
            'summary': (
                f"{busy_days} dia(s) carregado(s) e {free_days} dia(s) livres para redistribuir."
                if can_manage_classes else
                f"{busy_days} dia(s) carregado(s) e {free_days} dia(s) livres no mês."
            ),
            'action_label': 'Ver mapa do mês' if not can_manage_classes else 'Revisar mês',
            'action_href': '#monthly-board' if not can_manage_classes else '#planner-board',
            'href': '#monthly-board' if not can_manage_classes else '#planner-board',
        },
    ]


def build_class_grid_page(*, base_context, snapshot, schedule_form, selected_session, session_edit_form, current_query_string):
    role_slug = base_context['current_role'].slug
    can_manage_classes = role_slug in (ROLE_OWNER, ROLE_MANAGER)
    can_open_class_admin = role_slug in (ROLE_OWNER, ROLE_DEV)
    operational_focus = _build_operational_focus(
        today_schedule=snapshot['today_schedule'],
        grouped_sessions=snapshot['grouped_sessions'],
        monthly_calendar=snapshot['monthly_calendar'],
        can_manage_classes=can_manage_classes,
    )
    class_focus = [
        'Valide a agenda real da equipe de forma rápida e visual.',
        'A grade mostra reservas, lotação e distribuição das aulas por dia.',
        'Em caso de dúvida, comece por aqui antes de aprofundar em outros painéis.',
    ]
    shell_action_buttons = build_shell_action_buttons_from_focus(focus=operational_focus, scope='class-grid')
    hero = build_page_hero(
        eyebrow='Aulas',
        title='Grade de aulas.',
        copy='Acompanhe agenda, lotação e ritmo das turmas num ponto só.',
        actions=[
            {'label': 'Hoje', 'href': '#today-board'},
            {'label': 'Semana', 'href': '#weekly-board', 'kind': 'secondary'},
            *([
                {'label': 'Planejar', 'href': '#planner-board', 'kind': 'secondary'},
            ] if can_manage_classes else []),
        ],
        aria_label='Panorama da grade',
        classes=['operation-hero'],
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
        shell={
            'shell_action_buttons': shell_action_buttons,
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
            'operational_focus': operational_focus,
            'class_focus': class_focus,
        },
        actions={
            'anchors': {
                'today': '#today-board',
                'weekly': '#weekly-board',
                'monthly': '#monthly-board',
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