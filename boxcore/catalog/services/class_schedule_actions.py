"""
ARQUIVO: compatibilidade das actions rapidas da grade de aulas.

POR QUE ELE EXISTE:
- preserva a API anterior enquanto a grade passa a usar comandos dedicados por acao.

O QUE ESTE ARQUIVO FAZ:
1. encaminha update para o command correspondente.
2. encaminha delete para o command correspondente.

PONTOS CRITICOS:
- este arquivo deve permanecer fino para nao duplicar regra de negocio.
"""

from .class_grid_commands import (
    run_class_session_delete_command,
    run_class_session_update_command,
)


def handle_class_session_update_action(*, actor, session, form):
    return run_class_session_update_command(actor=actor, session=session, form=form).payload['session']


def handle_class_session_delete_action(*, actor, session):
    return run_class_session_delete_command(actor=actor, session=session).payload