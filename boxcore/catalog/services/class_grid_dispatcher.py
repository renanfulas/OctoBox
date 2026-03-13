"""
ARQUIVO: dispatcher operacional legado da grade de aulas.

POR QUE ELE EXISTE:
- preserva imports antigos enquanto a superficie canonica vive em catalog.services.class_grid_dispatcher.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta o dispatcher publico atual da grade.

PONTOS CRITICOS:
- se esse mapeamento divergir da UI, a grade deixa de despachar corretamente.
"""

from catalog.services.class_grid_dispatcher import (
    FORM_KIND_PLANNER,
    FORM_KIND_SESSION_ACTION,
    FORM_KIND_SESSION_EDIT,
    SESSION_ACTION_DELETE,
    resolve_class_grid_form_kind,
    resolve_class_grid_session_action,
)


__all__ = [
    'FORM_KIND_PLANNER',
    'FORM_KIND_SESSION_ACTION',
    'FORM_KIND_SESSION_EDIT',
    'SESSION_ACTION_DELETE',
    'resolve_class_grid_form_kind',
    'resolve_class_grid_session_action',
]