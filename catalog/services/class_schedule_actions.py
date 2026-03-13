"""Fachada publica das actions rapidas da grade do catalogo."""

from .class_grid_commands import run_class_session_delete_command, run_class_session_update_command


def handle_class_session_update_action(*, actor, session, form):
    return run_class_session_update_command(actor=actor, session=session, form=form).payload['session']


def handle_class_session_delete_action(*, actor, session):
    return run_class_session_delete_command(actor=actor, session=session).payload


__all__ = [
    'handle_class_session_delete_action',
    'handle_class_session_update_action',
]