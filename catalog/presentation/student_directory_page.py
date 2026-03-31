"""
ARQUIVO: presenter da tela de diretorio de alunos.

POR QUE ELE EXISTE:
- tira da view HTTP a montagem da fachada operacional da base de alunos.
- organiza a tela por contrato explicito para facilitar evolucao do catalogo.
"""

from access.navigation_contracts import get_shell_route_url
from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from access.shell_actions import build_shell_action_buttons_from_focus
from django.urls import reverse
from shared_support.page_payloads import build_page_hero

from .shared import build_catalog_assets, build_catalog_page_payload


def build_student_directory_page(*, student_count, students, student_filter_form, snapshot, current_role_slug, base_query_string):
    can_manage_students = current_role_slug in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)
    can_open_student_admin = current_role_slug in (ROLE_OWNER, ROLE_DEV)
    priority_students = snapshot['priority_students']
    intake_queue = snapshot['intake_queue']

    operational_focus = [
        {
            'label': 'Quem pede triagem primeiro',
            'chip_label': 'Prioridades',
            'summary': f'{len(priority_students)} aluno(s) ou lead(s) ja pedem leitura para nao perder tempo nem contexto.',
            'count': len(priority_students),
            'pill_class': 'warning' if len(priority_students) > 0 else 'success',
            'href': '#tab-students-priority',
            'href_label': 'Ver prioridades',
        },
        {
            'label': 'Quem ja pode virar aluno',
            'chip_label': 'Entradas',
            'summary': f'{len(intake_queue)} entrada(s) provisoria(s) ja podem virar aluno com pouco atrito.',
            'count': len(intake_queue),
            'pill_class': 'info' if len(intake_queue) > 0 else 'accent',
            'href': get_shell_route_url('intake', fragment='intake-queue-board'),
            'href_label': 'Abrir central de intake',
        },
        {
            'label': 'O tamanho da base agora',
            'chip_label': 'Base',
            'summary': f'{student_count} registro(s) sustentam esta leitura e pedem uma varredura calma, sem fadiga.',
            'count': student_count,
            'pill_class': 'accent',
            'href': '#tab-students-directory',
            'href_label': 'Ver base principal',
        },
    ]

    hero_actions = [
        {'label': 'Ver prioridades', 'href': '#tab-students-priority', 'kind': 'primary', 'data_action': 'open-tab-students-priority'},
        {'label': 'Abrir intake', 'href': get_shell_route_url('intake', fragment='intake-queue-board'), 'kind': 'secondary', 'data_action': 'open-student-intake-center'},
    ]

    if can_manage_students:
        hero_actions.append(
            {'label': 'Novo aluno', 'href': f"{reverse('student-quick-create')}#student-form-essential", 'kind': 'secondary', 'data_action': 'open-student-create'}
        )

    shell_action_buttons = build_shell_action_buttons_from_focus(focus=operational_focus, scope='students')
    hero = build_page_hero(
        eyebrow='Base',
        title='O que pede cuidado na sua base hoje.',
        copy='Veja quem merece leitura primeiro, quem ja pode avancar e onde agir sem ruido.',
        actions=hero_actions,
        aria_label='Panorama de alunos',
        classes=['student-hero'],
        heading_level='h1',
        data_slot='hero',
        data_panel='students-hero',
        actions_slot='students-hero-actions',
    )

    return build_catalog_page_payload(
        context={
            'page_key': 'student-directory',
            'title': 'Alunos',
            'subtitle': 'Triagem, contexto e proxima acao com leitura limpa.',
            'mode': 'management' if can_manage_students else 'read-only',
            'role_slug': current_role_slug,
        },
        shell={
            'shell_action_buttons': shell_action_buttons,
        },
        data={
            'hero': hero,
            'students': students,
            'base_query_string': base_query_string,
            'student_filter_form': student_filter_form,
            'operational_focus': operational_focus,
            'interactive_kpis': snapshot.get('interactive_kpis', {}),
            'priority_students': priority_students,
            'intake_queue': intake_queue,
            'total_students': student_count,
        },
        actions={},
        capabilities={
            'can_manage_students': can_manage_students,
            'can_open_student_admin': can_open_student_admin,
        },
        assets=build_catalog_assets(css=['css/catalog/students.css'], include_catalog_shared=True),
    )
