"""
ARQUIVO: builders do contrato de runtime de superficie compartilhado.

POR QUE ELE EXISTE:
- padroniza a linguagem entre backend e frontend para cache local, hidratacao, invalidacao e assets.
- evita que cada presenter invente seu proprio shape de runtime.

O QUE ESTE ARQUIVO FAZ:
1. monta `surface_behavior` com defaults seguros.
2. monta `asset_behavior` para ligar dados e assets no mesmo contrato.
3. devolve um bloco unico de contrato pronto para entrar em `behavior`.

PONTOS CRITICOS:
- o contrato nao transforma o frontend em fonte da verdade.
- campos novos precisam permanecer baratos de calcular e estaveis no payload.
"""

from __future__ import annotations


DEFAULT_RUNTIME_CONTRACT_VERSION = 'v1'
DEFAULT_ASSET_CONTRACT_VERSION = 'v1'


def build_surface_behavior(
    *,
    surface_key,
    role_slug='',
    storage_tier='session',
    cache_enabled=True,
    cache_key='default',
    refresh_token='',
    snapshot_version='',
    ttl_ms=120000,
    bootstrap_mode='minimal',
    bootstrap_item_count=0,
    bootstrap_has_more=False,
    bootstrap_next_offset=None,
    hydration_mode='on-demand',
    hydration_page_url='',
    hydration_page_size=0,
    hydration_prefetch_limit=0,
    hydration_max_parallel_requests=1,
    local_filters=None,
    server_filters=None,
    events_primary='none',
    events_fallback='none',
    events_poll_interval_ms=0,
    data_classification='operational',
    persist_to_disk=False,
    requires_server_revalidation_before_commit=True,
    runtime_contract_version=DEFAULT_RUNTIME_CONTRACT_VERSION,
):
    return {
        'surface_key': surface_key,
        'runtime_contract_version': runtime_contract_version,
        'scope': {
            'role_slug': role_slug,
            'session_scope': 'authenticated',
            'storage_tier': storage_tier,
        },
        'cache': {
            'enabled': bool(cache_enabled),
            'cache_key': cache_key or 'default',
            'refresh_token': refresh_token or '',
            'snapshot_version': snapshot_version or '',
            'ttl_ms': int(ttl_ms or 0),
        },
        'bootstrap': {
            'mode': bootstrap_mode,
            'item_count': int(bootstrap_item_count or 0),
            'has_more': bool(bootstrap_has_more),
            'next_offset': bootstrap_next_offset,
        },
        'hydration': {
            'mode': hydration_mode,
            'page_url': hydration_page_url or '',
            'page_size': int(hydration_page_size or 0),
            'prefetch_limit': int(hydration_prefetch_limit or 0),
            'max_parallel_requests': int(hydration_max_parallel_requests or 1),
        },
        'filters': {
            'local': list(local_filters or []),
            'server': list(server_filters or []),
        },
        'events': {
            'primary': events_primary,
            'fallback': events_fallback,
            'poll_interval_ms': int(events_poll_interval_ms or 0),
        },
        'invalidation': {
            'on_refresh_token_change': True,
            'on_snapshot_version_change': True,
            'on_mutation_success': True,
            'on_role_change': True,
            'on_contract_version_change': True,
            'cross_tab_sync': True,
        },
        'safety': {
            'data_classification': data_classification,
            'persist_to_disk': bool(persist_to_disk),
            'requires_server_revalidation_before_commit': bool(requires_server_revalidation_before_commit),
        },
    }


def build_asset_behavior(
    *,
    critical_css=None,
    deferred_css=None,
    enhancement_css=None,
    critical_js=None,
    progressive_js=None,
    interaction_triggers=None,
    asset_contract_version=DEFAULT_ASSET_CONTRACT_VERSION,
):
    return {
        'asset_contract_version': asset_contract_version,
        'critical_css': list(critical_css or []),
        'deferred_css': list(deferred_css or []),
        'enhancement_css': list(enhancement_css or []),
        'critical_js': list(critical_js or []),
        'progressive_js': list(progressive_js or []),
        'interaction_triggers': dict(interaction_triggers or {}),
    }


def build_surface_runtime_contract(*, surface_behavior, asset_behavior=None, telemetry_key='', surface_budget_key='', expected_hot_path=''):
    return {
        'surface_behavior': surface_behavior,
        'asset_behavior': asset_behavior or build_asset_behavior(),
        'observability': {
            'telemetry_key': telemetry_key or surface_behavior.get('surface_key', ''),
            'surface_budget_key': surface_budget_key or surface_behavior.get('surface_key', ''),
            'expected_hot_path': expected_hot_path or '',
        },
    }


__all__ = [
    'DEFAULT_ASSET_CONTRACT_VERSION',
    'DEFAULT_RUNTIME_CONTRACT_VERSION',
    'build_asset_behavior',
    'build_surface_behavior',
    'build_surface_runtime_contract',
]
