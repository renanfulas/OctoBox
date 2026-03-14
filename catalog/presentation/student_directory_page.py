"""
ARQUIVO: presenter da tela de diretorio de alunos.

POR QUE ELE EXISTE:
- tira da view HTTP a montagem da fachada operacional da base de alunos.
- organiza a tela por contrato explicito para facilitar evolucao do catalogo.
"""

from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from access.shell_actions import build_shell_action_buttons

from .shared import build_catalog_page_payload, build_page_assets


def build_student_directory_page(*, student_count, students, student_filter_form, snapshot, current_role_slug, export_links):
    can_manage_students = current_role_slug in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)
    can_export_students = current_role_slug in (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER)
    can_open_student_admin = current_role_slug in (ROLE_OWNER, ROLE_MANAGER)
    priority_students = snapshot['priority_students']
    intake_queue = snapshot['intake_queue']
    operational_focus = [
        {
            'label': 'Triagem imediata',
            'summary': f'{len(priority_students)} aluno(s) ou lead(s) ja pedem leitura antes de esfriarem.',
            'pill_class': 'warning' if len(priority_students) > 0 else 'success',
            'href': '#student-priority-board',
            'href_label': 'Ver prioridades',
        },
        {
            'label': 'Conversao pronta',
            'summary': f'{len(intake_queue)} entrada(s) provisoria(s) ja podem virar aluno com pouco atrito.',
            'pill_class': 'info' if len(intake_queue) > 0 else 'accent',
            'href': '#student-intake-board',
            'href_label': 'Ver fila de entrada',
        },
        {
            'label': 'Base no recorte atual',
            'summary': f'{student_count} registro(s) sustentam a leitura desta tela e precisam ser escaneados sem fadiga.',
            'pill_class': 'accent',
            'href': '#student-directory-board',
            'href_label': 'Ver base principal',
        },
    ]
    shell_action_buttons = build_shell_action_buttons(
        priority={'href': operational_focus[0]['href'], 'summary': operational_focus[0]['summary'], 'count': len(priority_students)},
        pending={'href': operational_focus[1]['href'], 'summary': operational_focus[1]['summary'], 'count': len(intake_queue)},
        next_action={'href': operational_focus[2]['href'], 'summary': operational_focus[2]['summary'], 'count': student_count},
        scope='students',
    )

    return build_catalog_page_payload(
        context={
            'page_key': 'student-directory',
            'title': 'Alunos',
            'subtitle': 'Reduza interpretacao. Localize e converta sem esforco; veja pendencia e proxima acao sem cacar informacao.',
            'mode': 'management' if can_manage_students else 'read-only',
            'role_slug': current_role_slug,
        },
        shell={
            'shell_action_buttons': shell_action_buttons,
        },
        data={
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
        assets=build_page_assets(),
    )