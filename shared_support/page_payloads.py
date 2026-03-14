"""
ARQUIVO: helpers compartilhados para contratos de tela entre backend e frontend.

POR QUE ELE EXISTE:
- centraliza o shape canonico de page payload fora de um app especifico.
- reduz duplicacao de bridge legado entre payload namespaced e templates ainda em migracao.
"""


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


def attach_page_payload(context, *, payload_key, payload, include_sections=None):
    """Anexa o payload namespaced e aplica aliases legados em um ponto unico."""
    context[payload_key] = payload

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