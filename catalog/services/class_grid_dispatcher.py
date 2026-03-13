"""Fachada publica do dispatcher da grade do catalogo."""

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