"""
ARQUIVO: presenter da tela de diretorio de alunos.

POR QUE ELE EXISTE:
- tira da view HTTP a montagem da fachada operacional da base de alunos.
- organiza a tela por contrato explicito para facilitar evolucao do catalogo.
"""

from access.navigation_contracts import get_shell_route_url
from access.roles import ROLE_COACH, ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from django.urls import reverse
from shared_support.page_payloads import build_page_context, build_page_hero
from shared_support.surface_runtime_contracts import build_asset_behavior, build_surface_behavior, build_surface_runtime_contract

from .shared import build_catalog_assets, build_catalog_page_payload


def build_student_directory_page(
    *,
    student_count,
    students,
    student_filter_form,
    snapshot,
    support_snapshot=None,
    current_role_slug,
    base_query_string,
    directory_search=None,
    performance_timing=None,
):
    can_manage_students = current_role_slug in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)
    can_open_student_admin = current_role_slug in (ROLE_OWNER, ROLE_DEV)
    support_data = support_snapshot or {}
    directory_search_payload = directory_search or {}
    hero_actions = [
        {'label': 'Ver base', 'href': '#tab-students-directory', 'kind': 'primary', 'data_action': 'open-tab-students-directory'},
    ]

    if current_role_slug != ROLE_COACH:
        hero_actions.append(
            {
                'label': 'Abrir intake',
                'href': get_shell_route_url('intake', fragment='intake-queue-board'),
                'kind': 'secondary',
                'data_action': 'open-student-intake-center',
            }
        )

    if can_manage_students:
        hero_actions.append(
            {'label': 'Novo aluno', 'href': f"{reverse('student-quick-create')}#student-form-essential", 'kind': 'secondary'}
        )

    hero = build_page_hero(
        eyebrow='Base',
        title='Sua base de alunos, com prioridade clara.',
        copy='Veja quem está bem, quem pede atenção e onde agir primeiro sem perder contexto.',
        actions=hero_actions,
        aria_label='Panorama de alunos',
        classes=['student-hero'],
        heading_level='h1',
        data_slot='hero',
        data_panel='students-hero',
        actions_slot='students-hero-actions',
    )
    surface_runtime_contract = build_surface_runtime_contract(
        surface_behavior=build_surface_behavior(
            surface_key='student-directory',
            role_slug=current_role_slug,
            storage_tier='session',
            cache_enabled=True,
            cache_key=directory_search_payload.get('cache_key') or 'all',
            refresh_token=directory_search_payload.get('refresh_token') or '',
            ttl_ms=120000,
            bootstrap_mode='minimal',
            bootstrap_item_count=len(directory_search_payload.get('index') or []),
            bootstrap_has_more=directory_search_payload.get('has_next', False),
            bootstrap_next_offset=directory_search_payload.get('next_offset'),
            hydration_mode='idle',
            hydration_page_url=directory_search_payload.get('page_url') or '',
            hydration_page_size=directory_search_payload.get('page_size') or 0,
            hydration_prefetch_limit=3,
            hydration_max_parallel_requests=1,
            local_filters=['query', 'status', 'sort'],
            server_filters=['student_status', 'commercial_status', 'payment_status', 'created_window'],
            events_primary='none',
            events_fallback='none',
            data_classification='operational',
            persist_to_disk=False,
            requires_server_revalidation_before_commit=True,
        ),
        asset_behavior=build_asset_behavior(
            critical_css=[
                'catalog-shared-scene',
                'students-scene',
                'students-filters',
                'students-intake-directory',
                'students-responsive',
            ],
            deferred_css=['students-secondary-panels'],
            enhancement_css=['students-quick-panel'],
            progressive_js=['surface-runtime', 'student-directory'],
            interaction_triggers={
                'quick_panel': 'click',
                'search_hydration': 'idle',
            },
        ),
        telemetry_key='student-directory',
        surface_budget_key='students-hot-path',
        expected_hot_path='cache-hit-after-first-load',
    )

    return build_catalog_page_payload(
        context={
            **build_page_context(
                page_key='student-directory',
                title='Alunos',
                subtitle='Base, prioridade e próxima ação em uma leitura que cabe na rotina.',
                mode='management' if can_manage_students else 'read-only',
                role_slug=current_role_slug,
            ),
        },
        data={
            'hero': hero,
            'students': students,
            'base_query_string': base_query_string,
            'student_filter_form': student_filter_form,
            'interactive_kpis': snapshot.get('interactive_kpis', {}),
            'total_students': student_count,
            'priority_students': support_data.get('priority_students', []),
            'intake_queue': support_data.get('intake_queue', []),
            'pending_intakes_count': support_data.get('pending_intakes_count', 0),
            'em_dia_count': snapshot.get('em_dia_count', 0),
            'pendentes_count': snapshot.get('pendentes_count', 0),
        },
        actions={},
        behavior={
            'default_panel': 'tab-students-directory',
            'default_action': 'open-tab-students-directory',
            'student_prefetch': {
                'enabled': True,
                'hover_delay_ms': 120,
                'cache_ttl_ms': 120000,
                'idle_prefetch_limit': 3,
            },
            'directory_search': directory_search_payload,
            'performance_timing': performance_timing or {},
            'surface_runtime': surface_runtime_contract,
        },
        capabilities={
            'can_manage_students': can_manage_students,
            'can_open_student_admin': can_open_student_admin,
        },
        assets=build_catalog_assets(
            css=[
                'css/catalog/shared/scene.css',
                'css/catalog/students/scene.css',
                'css/catalog/students/filters.css',
                'css/catalog/students/intake-directory.css',
                'css/catalog/students/responsive.css',
            ],
            deferred_css=[
                'bundle:css/catalog/students-deferred.css',
            ],
            enhancement_css=[
                'bundle:css/catalog/students-enhancement.css',
            ],
        ),
    )
