"""
ARQUIVO: presentation da Central de Intake.

POR QUE ELE EXISTE:
- Da uma superficie visual propria para entradas provisorias sem empurrar esse ownership para Alunos ou Operacao.

O QUE ESTE ARQUIVO FAZ:
1. Monta o page payload da Central de Intake.
2. Explicita foco operacional, conversao e origem das entradas.
3. Mantem o contrato visual alinhado ao restante do front.

PONTOS CRITICOS:
- Essa tela vira a origem canonica da fila de intake; links globais e handoffs dependem dela.
"""

from django.urls import reverse

from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from shared_support.page_payloads import build_page_assets, build_page_hero, build_page_payload


def build_intake_center_page(*, snapshot, current_role_slug):
    can_manage_students = current_role_slug in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)
    can_resolve_queue = current_role_slug in (ROLE_OWNER, ROLE_MANAGER)
    can_work_queue = current_role_slug in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)
    student_quick_create_url = reverse('student-quick-create')
    first_convertible_item = next(
        (item for item in snapshot.get('queue_items', []) if item['conversion']['can_convert']),
        None,
    )
    hero_actions = []

    if can_manage_students and first_convertible_item is not None:
        hero_actions.append(
            {
                'label': 'Converter primeiro',
                'href': f"{student_quick_create_url}?intake={first_convertible_item['object'].id}#student-form-essential",
                'data_action': 'convert-first-intake',
            }
        )
    elif can_manage_students:
        hero_actions.append(
            {
                'label': 'Nova entrada',
                'href': f'{student_quick_create_url}#student-form-essential',
                'data_action': 'open-student-quick-create',
            }
        )

    if can_manage_students:
        hero_actions.append(
            {'label': 'Novo lead', 'href': '#tab-intake-create-lead', 'kind': 'secondary', 'data_action': 'open-tab-intake-create-lead'}
        )
        hero_actions.append(
            {'label': 'Novo Intake', 'href': '#tab-intake-create-intake', 'kind': 'secondary', 'data_action': 'open-tab-intake-create-intake'}
        )

    hero = build_page_hero(
        eyebrow='Intake',
        title='Entradas em leitura.',
        copy='Veja quem pede resposta agora, quem ja pode converter e onde agir sem ruido.',
        actions=hero_actions,
        aria_label='Panorama da central de intake',
        classes=[],
        data_slot='hero',
        data_panel='intake-hero',
        actions_slot='intake-hero-actions',
    )

    return build_page_payload(
        context={
            'page_key': 'intake-center',
            'title': 'Central de Intake',
            'subtitle': 'Entradas provisorias, triagem e conversao num ponto proprio.',
            'mode': 'workspace',
            'role_slug': current_role_slug,
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
            css=['css/design-system/operations.css', 'css/catalog/shared.css', 'css/catalog/students.css', 'css/onboarding/intakes.css'],
            js=['js/pages/interactive_tabs.js']
        ),
    )


__all__ = ['build_intake_center_page']
