"""
ARQUIVO: contexto e payload da Central de Intake.

POR QUE ELE EXISTE:
- tira da view a montagem do contexto da tela e do payload do indice paginado.

O QUE ESTE ARQUIVO FAZ:
1. monta capacidades da tela por papel.
2. serializa itens do indice de busca de intake.
3. monta o contexto completo da tela principal.
4. monta o payload JSON do indice paginado.

PONTOS CRITICOS:
- qualquer mudanca aqui altera contrato visual, busca paginada e handoff com o front da central.
- o payload precisa continuar enxuto e sem duplicar leitura desnecessaria.
"""

from django.urls import reverse
from django.utils import timezone

from access.roles import ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION

from .presentation import build_intake_center_page
from .queries import build_intake_center_snapshot


def build_intake_page_capabilities(*, current_role_slug: str) -> dict:
    can_manage_students = current_role_slug in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)
    can_work_queue = current_role_slug in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)
    return {
        'can_manage_students': can_manage_students,
        'can_work_queue': can_work_queue,
    }


def clean_intake_search_index_params(params):
    index_params = params.copy()
    for key in ('query', 'panel', 'offset', 'status', 'semantic_stage', 'created_window', 'assignment'):
        if key in index_params:
            del index_params[key]
    return index_params


def parse_non_negative_int(value, default=0):
    try:
        parsed_value = int(value)
    except (TypeError, ValueError):
        return default
    return max(parsed_value, 0)


def serialize_intake_search_entry(*, item, request):
    intake = item['object']
    conversion = item['conversion']
    permissions = item['action_permissions']
    capabilities = getattr(request, 'intake_page_capabilities', {})
    can_manage_students = capabilities.get('can_manage_students', False)
    can_work_queue = capabilities.get('can_work_queue', False)
    conversion_href = ''
    if can_manage_students and conversion['can_convert'] and conversion['action_type'] == 'convert-student':
        conversion_href = f"{reverse('student-quick-create')}?intake={intake.id}#student-form-essential"

    return {
        'id': intake.id,
        'full_name': intake.full_name,
        'channel_label': intake.email or intake.phone or '',
        'source_label': intake.get_source_display(),
        'registration_age_days': item['registration_age_days'],
        'registration_age_label': item['registration_age_label'],
        'semantic_stage': item['semantic_state']['semantic_stage'],
        'semantic_label': item['semantic_state']['semantic_label'],
        'conversion_reason': conversion['reason'],
        'created_today': bool(getattr(intake, 'created_at', None) and intake.created_at.date() == timezone.localdate()),
        'assigned': bool(getattr(intake, 'assigned_to_id', None)),
        'assigned_label': (
            intake.assigned_to.get_full_name() or intake.assigned_to.username
            if getattr(intake, 'assigned_to', None)
            else 'Aguardando'
        ),
        'whatsapp_href': item['whatsapp_href'],
        'conversion': {
            'can_convert': bool(conversion['can_convert']),
            'action_type': conversion['action_type'],
            'action_label': conversion['action_label'],
            'href': conversion_href,
            'requires_post': bool(
                can_work_queue and conversion['can_convert'] and conversion['action_type'] == 'move-to-conversation'
            ),
        },
        'permissions': {
            'can_reject': bool(can_work_queue and permissions.get('can_reject')),
        },
    }


def build_intake_center_context(
    *,
    request,
    snapshot,
    current_role_slug: str,
    active_panel,
    lead_create_form,
    intake_create_form,
    search_bootstrap_limit: int,
    search_page_limit: int,
):
    request.intake_page_capabilities = build_intake_page_capabilities(current_role_slug=current_role_slug)
    index_params = clean_intake_search_index_params(request.GET)
    search_snapshot = build_intake_center_snapshot(
        params=index_params,
        actor_role_slug=current_role_slug,
        queue_limit=search_bootstrap_limit,
    )
    page_payload = build_intake_center_page(
        snapshot=snapshot,
        current_role_slug=current_role_slug,
        intake_search={
            'cache_key': index_params.urlencode() or 'all',
            'refresh_token': search_snapshot.get('queue_refresh_token', ''),
            'page_url': reverse('intake-search-index-page'),
            'page_size': search_page_limit,
            'total': search_snapshot.get('queue_total_count', 0),
            'has_next': search_snapshot.get('queue_has_next', False),
            'next_offset': search_snapshot.get('queue_next_offset'),
            'index': [
                serialize_intake_search_entry(item=item, request=request)
                for item in search_snapshot.get('queue_items', [])
            ],
        },
    )
    return {
        'active_intake_panel': active_panel,
        'lead_create_form': lead_create_form,
        'intake_create_form': intake_create_form,
        'intake_center_page': page_payload,
    }


def build_intake_search_index_payload(*, request, current_role_slug: str, offset: int, page_limit: int):
    index_params = clean_intake_search_index_params(request.GET)
    snapshot = build_intake_center_snapshot(
        params=index_params,
        actor_role_slug=current_role_slug,
        queue_limit=page_limit,
        queue_offset=offset,
    )
    request.intake_page_capabilities = build_intake_page_capabilities(current_role_slug=current_role_slug)
    return {
        'cache_key': index_params.urlencode() or 'all',
        'refresh_token': snapshot.get('queue_refresh_token', ''),
        'page_size': page_limit,
        'total': snapshot.get('queue_total_count', 0),
        'has_next': snapshot.get('queue_has_next', False),
        'next_offset': snapshot.get('queue_next_offset'),
        'index': [
            serialize_intake_search_entry(item=item, request=request)
            for item in snapshot.get('queue_items', [])
        ],
    }


__all__ = [
    'build_intake_center_context',
    'build_intake_page_capabilities',
    'build_intake_search_index_payload',
    'clean_intake_search_index_params',
    'parse_non_negative_int',
    'serialize_intake_search_entry',
]
