"""Fachada publica dos comandos de grade do catalogo."""

from operations.facade.class_grid import ClassGridCommandResult, run_class_session_delete, run_class_session_update


def run_class_session_update_command(*, actor, session, form):
	return run_class_session_update(actor=actor, session=session, form=form)


def run_class_session_delete_command(*, actor, session):
	return run_class_session_delete(actor=actor, session=session)


CLASS_GRID_ACTION_COMMANDS = {
	'delete-session': run_class_session_delete_command,
}


__all__ = [
	'CLASS_GRID_ACTION_COMMANDS',
	'ClassGridCommandResult',
	'run_class_session_delete_command',
	'run_class_session_update_command',
]