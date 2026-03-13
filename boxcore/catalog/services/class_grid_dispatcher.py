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

from operations.application.class_grid_dispatcher import (
    FORM_KIND_PLANNER,
    FORM_KIND_SESSION_ACTION,
    FORM_KIND_SESSION_EDIT,
    SESSION_ACTION_DELETE,
    resolve_class_grid_form_kind,
    resolve_class_grid_session_action as resolve_class_grid_session_action_name,
)

from .class_grid_commands import CLASS_GRID_ACTION_COMMANDS


def resolve_class_grid_session_action(post_data):
    action = resolve_class_grid_session_action_name(post_data)
    return CLASS_GRID_ACTION_COMMANDS[action]


__all__ = [
    'FORM_KIND_PLANNER',
    'FORM_KIND_SESSION_ACTION',
    'FORM_KIND_SESSION_EDIT',
    'SESSION_ACTION_DELETE',
    'resolve_class_grid_form_kind',
    'resolve_class_grid_session_action',
]