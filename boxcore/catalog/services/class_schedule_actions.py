"""
ARQUIVO: compatibilidade das actions rapidas da grade de aulas.

POR QUE ELE EXISTE:
- preserva a API anterior enquanto a superficie canonica vive em catalog.services.class_schedule_actions.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta as actions publicas atuais da grade.

PONTOS CRITICOS:
- este arquivo deve permanecer fino para nao duplicar regra de negocio.
"""

from catalog.services.class_schedule_actions import (
    handle_class_session_delete_action,
    handle_class_session_update_action,
)


__all__ = [
    'handle_class_session_delete_action',
    'handle_class_session_update_action',
]