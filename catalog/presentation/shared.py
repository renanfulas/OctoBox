"""
ARQUIVO: helpers compartilhados da camada de presentation do catalogo.

POR QUE ELE EXISTE:
- reduz repeticao estrutural entre payloads de tela sem criar um mini framework visual.
"""

from shared_support.page_payloads import attach_page_payload, build_page_assets, build_page_payload


def build_catalog_page_payload(*, context, shell_context=None, data=None, actions=None, behavior=None, capabilities=None, assets=None):
    return build_page_payload(
        context=context,
        shell_context=shell_context,
        data=data,
        actions=actions,
        behavior=behavior,
        capabilities=capabilities,
        assets=assets,
    )


def build_catalog_assets(*, css=None, js=None, include_operations=True, operations_entry='css/design-system/catalog-operation-contract.css', include_catalog_shared=False):
    css_paths = []

    if include_operations:
        css_paths.append(operations_entry)
    if include_catalog_shared:
        css_paths.append('css/catalog/shared.css')

    for asset_path in css or []:
        if asset_path not in css_paths:
            css_paths.append(asset_path)

    return build_page_assets(css=css_paths, js=js)


def attach_catalog_page_payload(context, *, payload_key, payload, include_sections=None):
    return attach_page_payload(context, payload_key=payload_key, payload=payload, include_sections=include_sections)
