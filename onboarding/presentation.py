"""
ARQUIVO: presentation da Central de Intake.

POR QUE ELE EXISTE:
- Da uma superficie visual propria para entradas provisórias sem empurrar esse ownership para Alunos ou Operacao.

O QUE ESTE ARQUIVO FAZ:
1. Monta o page payload da Central de Intake.
2. Explicita foco operacional, conversao e origem das entradas.
3. Mantem o contrato visual alinhado ao restante do front.

PONTOS CRITICOS:
- Essa tela vira a origem canonica da fila de intake; links globais e handoffs dependem dela.
"""

from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from access.shell_actions import build_shell_action_buttons_from_focus
from shared_support.page_payloads import build_page_assets, build_page_hero, build_page_payload


def build_intake_center_page(*, snapshot, current_role_slug):
    can_manage_students = current_role_slug in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)
    can_resolve_queue = current_role_slug in (ROLE_OWNER, ROLE_MANAGER)
    can_work_queue = current_role_slug in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)
    first_convertible_item = next(
        (item for item in snapshot.get('queue_items', []) if item['conversion']['can_convert']),
        None,
    )
    hero_actions = []

    if can_manage_students and first_convertible_item is not None:
        hero_actions.append(
            {
                'label': 'Converter primeiro da fila',
                'href': f"/alunos/novo/?intake={first_convertible_item['object'].id}#student-form-essential",
                'data_action': 'convert-first-intake',
            }
        )
    elif can_manage_students:
        hero_actions.append(
            {
                'label': 'Abrir cadastro rapido',
                'href': '/alunos/novo/#student-form-essential',
                'data_action': 'open-student-quick-create',
            }
        )

    hero_actions.append(
        {'label': 'Abrir alunos', 'href': '/alunos/', 'kind': 'secondary', 'data_action': 'open-students-directory'}
    )

    if current_role_slug == ROLE_RECEPTION:
        hero_actions.append(
            {'label': 'Abrir recepcao', 'href': '/operacao/recepcao/', 'kind': 'secondary', 'data_action': 'open-reception-workspace'}
        )
    elif current_role_slug == ROLE_MANAGER:
        hero_actions.append(
            {'label': 'Abrir operacao', 'href': '/operacao/manager/', 'kind': 'secondary', 'data_action': 'open-manager-workspace'}
        )
    elif current_role_slug == ROLE_OWNER:
        hero_actions.append(
            {'label': 'Abrir operacao', 'href': '/operacao/', 'kind': 'secondary', 'data_action': 'open-owner-workspace'}
        )

    hero = build_page_hero(
        eyebrow='Central de entrada',
        title='Triagem e conversao antes do aluno definitivo.',
        copy='Aqui vivem as entradas provisórias que ainda pedem dono, leitura e proximo passo.',
        actions=hero_actions,
        side={
            'kind': 'stat-grid',
            'eyebrow': 'Pulso da fila',
            'copy': 'O que chegou, o que travou e o que ja pode virar ficha.',
            'items': snapshot['hero_stats'],
            'stack': True,
            'data_panel': 'intake-hero-summary',
        },
        aria_label='Panorama da central de intake',
        classes=['catalog-hero', 'intake-hero'],
        data_slot='hero',
        data_panel='intake-hero',
        actions_slot='intake-hero-actions',
    )

    return build_page_payload(
        context={
            'page_key': 'intake-center',
            'title': 'Central de Intake',
            'subtitle': 'Entradas provisórias, triagem e conversao num ponto proprio.',
            'mode': 'workspace',
            'role_slug': current_role_slug,
        },
        shell={
            'shell_action_buttons': build_shell_action_buttons_from_focus(
                focus=snapshot['intake_operational_focus'],
                scope='intake-center',
            ),
        },
        data={
            **snapshot,
            'hero': hero,
        },
        capabilities={
            'can_resolve_queue': can_resolve_queue,
            'can_view_as_read_only': current_role_slug == ROLE_DEV,
            'can_manage_students': can_manage_students,
            'can_work_queue': can_work_queue,
        },
        assets=build_page_assets(
            css=['css/design-system/operations.css', 'css/catalog/students.css', 'css/onboarding/intakes.css']
        ),
    )


__all__ = ['build_intake_center_page']