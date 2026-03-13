"""
ARQUIVO: fachada historica dos comandos da grade de aulas.

POR QUE ELE EXISTE:
- preserva a API antiga enquanto a entrada publica real passa a morar em operations.facade.class_grid.

O QUE ESTE ARQUIVO FAZ:
1. encaminha update para a facade publica da grade.
2. encaminha delete para a facade publica da grade.

PONTOS CRITICOS:
- novos entrypoints devem preferir operations.facade.class_grid diretamente.
"""

from operations.facade.class_grid import ClassGridCommandResult, run_class_session_delete, run_class_session_update


def run_class_session_update_command(*, actor, session, form):
    return run_class_session_update(actor=actor, session=session, form=form)


def run_class_session_delete_command(*, actor, session):
    return run_class_session_delete(actor=actor, session=session)


CLASS_GRID_ACTION_COMMANDS = {
    'delete-session': run_class_session_delete_command,
}