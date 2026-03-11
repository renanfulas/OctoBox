"""
ARQUIVO: dispatcher operacional da grade de aulas.

POR QUE ELE EXISTE:
- evita que a view conheca strings soltas de form_kind e action, deixando a resolucao do fluxo em um ponto unico.

O QUE ESTE ARQUIVO FAZ:
1. resolve o tipo de post enviado pela grade.
2. resolve o command de acao rapida da aula.
3. centraliza os defaults e erros de despacho da tela.

PONTOS CRITICOS:
- se o mapeamento aqui ficar inconsistente, a view perde a capacidade de despachar os fluxos corretos.
"""

from . import class_grid_messages as grid_messages
from .class_grid_commands import CLASS_GRID_ACTION_COMMANDS


FORM_KIND_PLANNER = 'planner'
FORM_KIND_SESSION_ACTION = 'session-action'
FORM_KIND_SESSION_EDIT = 'session-edit'

CLASS_GRID_FORM_KIND_HANDLERS = {
    FORM_KIND_PLANNER: 'planner',
    FORM_KIND_SESSION_ACTION: 'session-action',
    FORM_KIND_SESSION_EDIT: 'session-edit',
}


def resolve_class_grid_form_kind(post_data):
    form_kind = (post_data.get('form_kind') or FORM_KIND_PLANNER).strip()
    if form_kind not in CLASS_GRID_FORM_KIND_HANDLERS:
        raise ValueError(grid_messages.UNKNOWN_FORM_KIND)
    return form_kind


def resolve_class_grid_session_action(post_data):
    action = (post_data.get('action') or '').strip()
    handler = CLASS_GRID_ACTION_COMMANDS.get(action)
    if handler is None:
        raise ValueError(grid_messages.UNKNOWN_SESSION_ACTION)
    return handler