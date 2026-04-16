"""
ARQUIVO: metricas minimas do runner da Signal Mesh.

POR QUE ELE EXISTE:
- da visibilidade operacional para sweeps de retry sem misturar isso com Beacon.
- ajuda a medir backlog, reenfileiramento e skips por corredor.
"""

from prometheus_client import Counter, Gauge


SIGNAL_MESH_RETRY_SWEEPS_TOTAL = Counter(
    'signal_mesh_retry_sweeps_total',
    'Total de sweeps de retry executados pela Signal Mesh.',
    ['channel'],
)

SIGNAL_MESH_RETRY_DISPATCHED_TOTAL = Counter(
    'signal_mesh_retry_dispatched_total',
    'Total de itens reenfileirados ou reprocessados pela Signal Mesh.',
    ['channel'],
)

SIGNAL_MESH_RETRY_SKIPPED_TOTAL = Counter(
    'signal_mesh_retry_skipped_total',
    'Total de itens ignorados durante sweep da Signal Mesh.',
    ['channel', 'reason'],
)

SIGNAL_MESH_RETRY_DUE_BACKLOG = Gauge(
    'signal_mesh_retry_due_backlog',
    'Quantidade de itens vencidos aguardando sweep por corredor.',
    ['channel'],
)


def record_retry_sweep(*, channel: str, due_backlog: int, dispatched_count: int, skipped: list[dict]):
    SIGNAL_MESH_RETRY_SWEEPS_TOTAL.labels(channel=channel).inc()
    SIGNAL_MESH_RETRY_DUE_BACKLOG.labels(channel=channel).set(max(due_backlog, 0))
    if dispatched_count > 0:
        SIGNAL_MESH_RETRY_DISPATCHED_TOTAL.labels(channel=channel).inc(dispatched_count)
    for item in skipped:
        SIGNAL_MESH_RETRY_SKIPPED_TOTAL.labels(
            channel=channel,
            reason=item.get('reason', 'unknown'),
        ).inc()


__all__ = [
    'SIGNAL_MESH_RETRY_DISPATCHED_TOTAL',
    'SIGNAL_MESH_RETRY_DUE_BACKLOG',
    'SIGNAL_MESH_RETRY_SKIPPED_TOTAL',
    'SIGNAL_MESH_RETRY_SWEEPS_TOTAL',
    'record_retry_sweep',
]
