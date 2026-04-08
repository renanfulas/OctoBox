"""
ARQUIVO: metricas Prometheus do circuito realtime nativo do Manager.

POR QUE ELE EXISTE:
- observa o barramento SSE do workspace do Manager sem poluir views e services.
"""

from prometheus_client import Counter, Gauge


MANAGER_SSE_EVENTS_PUBLISHED = Counter(
    'octobox_manager_sse_events_published_total',
    'Total de eventos SSE publicados para o workspace do manager',
    ['event_type'],
)

MANAGER_SSE_STREAM_CONNECTIONS = Counter(
    'octobox_manager_sse_stream_connections_total',
    'Total de conexoes SSE do workspace do manager',
    ['status'],
)

MANAGER_SSE_ACTIVE_STREAMS = Gauge(
    'octobox_manager_sse_active_streams',
    'Numero de streams SSE ativos do workspace do manager',
)


KNOWN_MANAGER_EVENT_TYPES = (
    'student.payment.updated',
    'student.enrollment.updated',
    'student.profile.updated',
    'intake.updated',
    'whatsapp_contact.updated',
)

KNOWN_MANAGER_STREAM_STATUSES = (
    'opened',
    'closed',
    'error',
    'redis_error',
)


def _read_counter_value(metric: Counter, **expected_labels) -> int:
    total = 0
    for family in metric.collect():
        for sample in family.samples:
            if not sample.name.endswith('_total'):
                continue
            if all(sample.labels.get(key) == value for key, value in expected_labels.items()):
                total += int(sample.value)
    return total


def _read_gauge_value(metric: Gauge) -> int:
    for family in metric.collect():
        for sample in family.samples:
            if sample.name == family.name:
                return int(sample.value)
    return 0


def record_manager_sse_event_published(event_type: str) -> None:
    MANAGER_SSE_EVENTS_PUBLISHED.labels(event_type=event_type or 'unknown').inc()


def record_manager_sse_stream_connection(status: str) -> None:
    MANAGER_SSE_STREAM_CONNECTIONS.labels(status=status or 'unknown').inc()


def inc_manager_sse_active_streams() -> None:
    MANAGER_SSE_ACTIVE_STREAMS.inc()


def dec_manager_sse_active_streams() -> None:
    try:
        MANAGER_SSE_ACTIVE_STREAMS.dec()
    except ValueError:
        pass


def build_manager_realtime_metrics_snapshot() -> dict:
    event_counts = {
        event_type: _read_counter_value(MANAGER_SSE_EVENTS_PUBLISHED, event_type=event_type)
        for event_type in KNOWN_MANAGER_EVENT_TYPES
    }
    stream_status_counts = {
        status: _read_counter_value(MANAGER_SSE_STREAM_CONNECTIONS, status=status)
        for status in KNOWN_MANAGER_STREAM_STATUSES
    }
    active_streams = _read_gauge_value(MANAGER_SSE_ACTIVE_STREAMS)
    return {
        'event_counts': event_counts,
        'stream_status_counts': stream_status_counts,
        'active_streams': active_streams,
        'events_total': sum(event_counts.values()),
        'stream_connections_total': sum(stream_status_counts.values()),
    }


__all__ = [
    'dec_manager_sse_active_streams',
    'build_manager_realtime_metrics_snapshot',
    'inc_manager_sse_active_streams',
    'record_manager_sse_event_published',
    'record_manager_sse_stream_connection',
]
