"""
ARQUIVO: helpers compartilhados para contratos de tela entre backend e frontend.

POR QUE ELE EXISTE:
- centraliza o shape canonico de page payload fora de um app especifico.
- reduz duplicacao de bridge legado entre payload namespaced e templates ainda em migracao.
"""


def _merge_asset_lists(existing, incoming):
    merged = list(existing or [])
    for asset_path in incoming or []:
        if asset_path and asset_path not in merged:
            merged.append(asset_path)
    return merged


def build_page_payload(*, context, shell=None, data=None, actions=None, behavior=None, capabilities=None, assets=None):
    return {
        'context': context,
        'shell': shell or {},
        'data': data or {},
        'actions': actions or {},
        'behavior': behavior or {},
        'capabilities': capabilities or {},
        'assets': assets or {},
    }


def build_page_assets(*, css=None, js=None):
    return {
        'css': css or [],
        'js': js or [],
    }


PAGE_HERO_CONTENT_RULES = {
    'max_primary_actions': 3,
    'max_side_stats': 4,
    'max_side_grid_items': 4,
    'max_title_lines': 2,
    'max_copy_lines': 2,
    'max_panel_copy_lines': 2,
}


def _limit_collection(items, *, max_items):
    return list(items or [])[:max_items]


def _normalize_hero_side(side):
    normalized = dict(side or {})

    if normalized.get('stats'):
        normalized['stats'] = _limit_collection(
            normalized.get('stats'),
            max_items=PAGE_HERO_CONTENT_RULES['max_side_stats'],
        )

    if normalized.get('items'):
        normalized['items'] = _limit_collection(
            normalized.get('items'),
            max_items=PAGE_HERO_CONTENT_RULES['max_side_grid_items'],
        )

    return normalized


def build_page_hero(
    *,
    eyebrow,
    title,
    copy,
    actions=None,
    side=None,
    aria_label=None,
    classes=None,
    heading_level='h2',
    data_slot=None,
    data_panel=None,
    actions_slot=None,
    contract=None,
):
    return {
        'eyebrow': eyebrow,
        'title': title,
        'copy': copy,
        'actions': _limit_collection(actions, max_items=PAGE_HERO_CONTENT_RULES['max_primary_actions']),
        'side': _normalize_hero_side(side),
        'aria_label': aria_label or title,
        'classes': classes or [],
        'heading_level': heading_level,
        'data_slot': data_slot,
        'data_panel': data_panel,
        'actions_slot': actions_slot,
        'contract': contract or dict(PAGE_HERO_CONTENT_RULES),
    }


def attach_page_payload(context, *, payload_key, payload, include_sections=None):
    """Anexa o payload namespaced e aplica aliases legados em um ponto unico."""
    context[payload_key] = payload

    payload_assets = payload.get('assets') or {}
    current_page_assets = context.get('current_page_assets') or {'css': [], 'js': []}
    current_page_assets = {
        'css': _merge_asset_lists(current_page_assets.get('css'), payload_assets.get('css')),
        'js': _merge_asset_lists(current_page_assets.get('js'), payload_assets.get('js')),
    }
    context['current_page_assets'] = current_page_assets
    context['page_assets'] = current_page_assets

    payload_behavior = payload.get('behavior') or {}
    if payload_behavior:
        context['current_page_behavior'] = payload_behavior

    for section_name in include_sections or ('context', 'shell'):
        section = payload.get(section_name) or {}
        context.update(section)

    page_context = payload.get('context') or {}
    if page_context.get('title'):
        context.setdefault('page_title', page_context['title'])
    if page_context.get('subtitle'):
        context.setdefault('page_subtitle', page_context['subtitle'])

    shell = payload.get('shell') or {}
    if 'shell_action_buttons' in shell:
        context['shell_action_buttons'] = shell['shell_action_buttons']

    return context