"""
ARQUIVO: serializacao compartilhada de aulas para leituras visuais.

POR QUE ELE EXISTE:
- Mantem imports historicos funcionando enquanto a superficie canonica vive em operations.session_snapshots.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta a serializacao publica atual de aulas.

PONTOS CRITICOS:
- mudancas aqui devem permanecer apenas de compatibilidade.
"""

from operations.session_snapshots import (
    build_class_session_runtime_state,
    serialize_class_session,
    sync_runtime_statuses,
)


__all__ = [
    'build_class_session_runtime_state',
    'serialize_class_session',
    'sync_runtime_statuses',
]