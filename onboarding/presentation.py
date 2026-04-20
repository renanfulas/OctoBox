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
from shared_support.page_payloads import build_page_assets, build_page_context, build_page_hero, build_page_payload
from shared_support.surface_runtime_contracts import build_asset_behavior, build_surface_behavior, build_surface_runtime_contract


def build_intake_center_page(*, snapshot, current_role_slug, intake_search=None):
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
            {'label': 'Em conversa', 'href': '#tab-intake-create-intake', 'kind': 'secondary', 'data_action': 'open-tab-intake-create-intake'}
        )

    hero = build_page_hero(
        eyebrow='Entradas',
        title='Suas entradas, com prioridade clara.',
        copy='Veja quem pede resposta agora, quem ja esta aquecido e onde converter sem perder contexto.',
        actions=hero_actions,
        aria_label='Panorama da central de entradas',
        classes=[],
        data_slot='hero',
        data_panel='intake-hero',
        actions_slot='intake-hero-actions',
    )
    intake_search_payload = intake_search or {}
    surface_runtime_contract = build_surface_runtime_contract(
        surface_behavior=build_surface_behavior(
            surface_key='intake-center',
            role_slug=current_role_slug,
            storage_tier='session',
            cache_enabled=True,
            cache_key=intake_search_payload.get('cache_key') or 'all',
            refresh_token=intake_search_payload.get('refresh_token') or '',
            ttl_ms=120000,
            bootstrap_mode='minimal',
            bootstrap_item_count=len(intake_search_payload.get('index') or []),
            bootstrap_has_more=intake_search_payload.get('has_next', False),
            bootstrap_next_offset=intake_search_payload.get('next_offset'),
            hydration_mode='idle',
            hydration_page_url=intake_search_payload.get('page_url') or '',
            hydration_page_size=intake_search_payload.get('page_size') or 0,
            hydration_prefetch_limit=2,
            hydration_max_parallel_requests=1,
            local_filters=['query', 'semantic-stage:new-leads', 'sort:registration'],
            server_filters=['status', 'source', 'created_window', 'assignment'],
            events_primary='none',
            events_fallback='none',
            data_classification='operational',
            persist_to_disk=False,
            requires_server_revalidation_before_commit=True,
        ),
        asset_behavior=build_asset_behavior(
            critical_css=['operations-shell', 'catalog-shared', 'students-shared', 'intake-scene'],
            progressive_js=['surface-runtime', 'intake-center'],
            interaction_triggers={
                'queue_search': 'input',
                'queue_hydration': 'idle',
            },
        ),
        telemetry_key='intake-center',
        surface_budget_key='intake-hot-path',
        expected_hot_path='cache-hit-after-first-load',
    )

    return build_page_payload(
        context={
            **build_page_context(
                page_key='intake-center',
                title='Central de Entradas',
                subtitle='Triagem, conversa e conversao em uma central propria.',
                mode='workspace',
                role_slug=current_role_slug,
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
        behavior={
            'intake_search': intake_search_payload,
            'surface_runtime': surface_runtime_contract,
        },
        assets=build_page_assets(
            css=['css/design-system/operations.css', 'css/catalog/shared.css', 'css/catalog/students.css', 'css/onboarding/intakes.css'],
            js=['js/pages/interactive_tabs.js']
        ),
    )


__all__ = ['build_intake_center_page']
