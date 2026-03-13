"""
ARQUIVO: dispatcher operacional da grade de aulas.

POR QUE ELE EXISTE:
- evita strings soltas de form kind e action fora da fronteira operations.

O QUE ESTE ARQUIVO FAZ:
1. resolve o tipo de post enviado pela grade.
2. resolve a acao rapida da aula como chave estavel.

PONTOS CRITICOS:
- se esse mapeamento divergir da UI, a grade deixa de despachar corretamente.
"""

from . import class_grid_messages as grid_messages


FORM_KIND_PLANNER = 'planner'
FORM_KIND_SESSION_ACTION = 'session-action'
FORM_KIND_SESSION_EDIT = 'session-edit'

SESSION_ACTION_DELETE = 'delete-session'

CLASS_GRID_FORM_KIND_HANDLERS = {
    FORM_KIND_PLANNER: 'planner',
    FORM_KIND_SESSION_ACTION: 'session-action',
    FORM_KIND_SESSION_EDIT: 'session-edit',
}

CLASS_GRID_SESSION_ACTIONS = {
    SESSION_ACTION_DELETE,
}


def resolve_class_grid_form_kind(post_data):
    form_kind = (post_data.get('form_kind') or FORM_KIND_PLANNER).strip()
    if form_kind not in CLASS_GRID_FORM_KIND_HANDLERS:
        raise ValueError(grid_messages.UNKNOWN_FORM_KIND)
    return form_kind


def resolve_class_grid_session_action(post_data):
    action = (post_data.get('action') or '').strip()
    if action not in CLASS_GRID_SESSION_ACTIONS:
        raise ValueError(grid_messages.UNKNOWN_SESSION_ACTION)
    return action


__all__ = [
    'FORM_KIND_PLANNER',
    'FORM_KIND_SESSION_ACTION',
    'FORM_KIND_SESSION_EDIT',
    'SESSION_ACTION_DELETE',
    'resolve_class_grid_form_kind',
    'resolve_class_grid_session_action',
]