"""
ARQUIVO: presenter da tela de diretorio de alunos.

POR QUE ELE EXISTE:
- tira da view HTTP a montagem da fachada operacional da base de alunos.
- organiza a tela por contrato explicito para facilitar evolucao do catalogo.
"""

from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from access.shell_actions import build_shell_action_buttons_from_focus
from shared_support.page_payloads import build_page_hero

from .shared import build_catalog_assets, build_catalog_page_payload


def build_student_directory_page(*, student_count, students, student_filter_form, snapshot, current_role_slug, export_links):
    can_manage_students = current_role_slug in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)
    can_export_students = current_role_slug in (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER)
    can_open_student_admin = current_role_slug in (ROLE_OWNER, ROLE_DEV)
    priority_students = snapshot['priority_students']
    intake_queue = snapshot['intake_queue']
    hero_actions = []

    if can_manage_students:
        hero_actions.append(
            {'label': 'Novo aluno', 'href': '/alunos/novo/#student-form-essential', 'data_action': 'open-student-create'}
        )

    hero_actions.append(
        {'label': 'Ver prioridades', 'href': '#student-priority-board', 'kind': 'secondary', 'data_action': 'jump-student-priorities'}
    )

    if can_export_students:
        hero_actions.append(
            {'label': 'Exportar CSV', 'href': export_links['csv'], 'kind': 'secondary', 'data_action': 'export-students-csv'}
        )

    operational_focus = [
        {
            'label': 'Triagem imediata',
            'summary': f'{len(priority_students)} aluno(s) ou lead(s) ja pedem leitura antes de esfriarem.',
            'count': len(priority_students),
            'pill_class': 'warning' if len(priority_students) > 0 else 'success',
            'href': '#student-priority-board',
            'href_label': 'Ver prioridades',
        },
        {
            'label': 'Conversao pronta',
            'summary': f'{len(intake_queue)} entrada(s) provisoria(s) ja podem virar aluno com pouco atrito.',
            'count': len(intake_queue),
            'pill_class': 'info' if len(intake_queue) > 0 else 'accent',
            'href': '/entradas/#intake-queue-board',
            'href_label': 'Abrir central de intake',
        },
        {
            'label': 'Base no recorte atual',
            'summary': f'{student_count} registro(s) sustentam a leitura desta tela e precisam ser escaneados sem fadiga.',
            'count': student_count,
            'pill_class': 'accent',
            'href': '#student-directory-board',
            'href_label': 'Ver base principal',
        },
    ]
    shell_action_buttons = build_shell_action_buttons_from_focus(focus=operational_focus, scope='students')
    hero = build_page_hero(
        eyebrow='Mesa de atendimento',
        title='Encontre, entenda e aja sem travar.',
        copy='Triagem, pendencia e proxima acao sem caca visual.',
        actions=hero_actions,
        side={
            'kind': 'stat-grid',
            'eyebrow': 'Radar da base',
            'copy': 'Contato quente, pendencia e conversao.',
            'items': [
                {'label': 'Visiveis', 'value': len(students)},
                {'label': 'Triagem agora', 'value': len(priority_students)},
                {'label': 'Intakes prontos', 'value': len(intake_queue)},
                {'label': 'Modo', 'value': 'acao' if can_manage_students else 'consulta'},
            ],
            'stack': True,
            'data_panel': 'students-hero-summary',
        },
        aria_label='Panorama de alunos',
        classes=['catalog-hero', 'student-hero'],
        data_slot='hero',
        data_panel='students-hero',
        actions_slot='students-hero-actions',
    )

    return build_catalog_page_payload(
        context={
            'page_key': 'student-directory',
            'title': 'Alunos',
            'subtitle': 'Triagem, pendencia e proxima acao sem caca visual.',
            'mode': 'management' if can_manage_students else 'read-only',
            'role_slug': current_role_slug,
        },
        shell={
            'shell_action_buttons': shell_action_buttons,
        },
        data={
            'hero': hero,
            'students': students,
            'student_filter_form': student_filter_form,
            'student_metrics': snapshot['metrics'],
            'student_funnel': snapshot['funnel'],
            'priority_students': priority_students,
            'intake_queue': intake_queue,
        },
        actions={
            'student_export_links': export_links,
        },
        capabilities={
            'can_manage_students': can_manage_students,
            'can_export_students': can_export_students,
            'can_open_student_admin': can_open_student_admin,
        },
        assets=build_catalog_assets(css=['css/catalog/students.css'], include_catalog_shared=True),
    )