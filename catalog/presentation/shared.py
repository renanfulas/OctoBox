"""
ARQUIVO: helpers compartilhados da camada de presentation do catalogo.

POR QUE ELE EXISTE:
- reduz repeticao estrutural entre payloads de tela sem criar um mini framework visual.
"""

from shared_support.page_payloads import attach_page_payload, build_page_assets, build_page_payload


def build_catalog_page_payload(*, context, shell, data, actions, behavior=None, capabilities=None, assets=None):
    return build_page_payload(
        context=context,
        shell=shell,
        data=data,
        actions=actions,
        behavior=behavior,
        capabilities=capabilities,
        assets=assets,
    )


def attach_catalog_page_payload(context, *, payload_key, payload, include_sections=None):
    return attach_page_payload(context, payload_key=payload_key, payload=payload, include_sections=include_sections)