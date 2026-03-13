"""
ARQUIVO: fachada da fila operacional do financeiro.

POR QUE ELE EXISTE:
- Mantém a interface histórica do catálogo enquanto a superfície canônica vive em catalog.services.operational_queue.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta a fila operacional pública atual.

PONTOS CRITICOS:
- Este arquivo não deve voltar a concentrar query e priorização operacional.
"""

from catalog.services.operational_queue import (
    build_operational_queue,
    build_operational_queue_metrics,
    build_operational_queue_snapshot,
    summarize_operational_queue,
)


__all__ = [
    'build_operational_queue',
    'build_operational_queue_metrics',
    'build_operational_queue_snapshot',
    'summarize_operational_queue',
]