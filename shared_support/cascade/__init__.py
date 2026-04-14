"""
ARQUIVO: namespace tecnico da futura cascata por unidade.

POR QUE ELE EXISTE:
- reserva um corredor unico para contratos e ownership da cascata.
- evita espalhar logica preliminar da arquitetura alvo em varios modulos soltos.
"""

from .contracts import (
    CASCADE_INTENT_FIELDS,
    CASCADE_RESOLUTION_FIELDS,
    build_cascade_intent,
    build_cascade_resolution,
    merge_cascade_metadata,
)
from .ownership import resolve_actor_box_id, resolve_box_owner_user_id

__all__ = [
    'CASCADE_INTENT_FIELDS',
    'CASCADE_RESOLUTION_FIELDS',
    'build_cascade_intent',
    'build_cascade_resolution',
    'merge_cascade_metadata',
    'resolve_actor_box_id',
    'resolve_box_owner_user_id',
]
