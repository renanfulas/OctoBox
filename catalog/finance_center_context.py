"""
ARQUIVO: corredor de contexto da central financeira.

POR QUE ELE EXISTE:
- tira de `catalog/views/finance_views.py` a montagem pesada de contexto/payload.

O QUE ESTE ARQUIVO FAZ:
1. resolve filtros efetivos e estado restaurado.
2. mede queue, snapshot e presenter.
3. devolve o contexto final pronto para anexar na view.
"""

from time import perf_counter

from catalog.finance_queries import build_finance_snapshot
from catalog.presentation import build_finance_center_page
from catalog.presentation.shared import attach_catalog_page_payload
from catalog.services.operational_queue import build_operational_queue_snapshot


def build_finance_center_view_context(view, *, context, form):
    started_at = perf_counter()
    base_context = view.get_base_context()
    context.update(base_context)

    operational_queue_started_at = perf_counter()
    operational_queue = build_operational_queue_snapshot()
    operational_queue_ms = round((perf_counter() - operational_queue_started_at) * 1000, 2)

    effective_params, filters_applied_now, filters_restored = view.get_effective_finance_filter_params()
    default_panel_override = (
        'tab-finance-filters'
        if (filters_applied_now or view.request.GET.get('reset_filters') == '1')
        else None
    )

    snapshot_started_at = perf_counter()
    snapshot = build_finance_snapshot(
        effective_params,
        operational_queue=operational_queue,
        persist_follow_ups=True,
    )
    snapshot_ms = round((perf_counter() - snapshot_started_at) * 1000, 2)

    presenter_started_at = perf_counter()
    performance_timing = {
        **(snapshot.get('performance_timing') or {}),
        'operational_queue_ms': operational_queue_ms,
        'snapshot_build_ms': snapshot_ms,
    }
    page_payload = build_finance_center_page(
        snapshot=snapshot,
        operational_queue=operational_queue,
        export_links=view.get_finance_export_links(effective_params),
        current_role_slug=base_context['current_role'].slug,
        form=form,
        default_panel_override=default_panel_override,
        filter_state_restored=filters_restored,
        performance_timing=performance_timing,
    )
    performance_timing['presenter_ms'] = round((perf_counter() - presenter_started_at) * 1000, 2)
    performance_timing['view_total_ms'] = round((perf_counter() - started_at) * 1000, 2)
    page_payload['behavior']['performance_timing'] = performance_timing
    return attach_catalog_page_payload(
        context,
        payload_key='finance_center_page',
        payload=page_payload,
        include_sections=('context', 'shell'),
    )
