"""
ARQUIVO: metricas Prometheus do circuito realtime da ficha do aluno.

POR QUE ELE EXISTE:
- observa o trilho SSE e os conflitos de concorrencia sem poluir views e services.

O QUE ESTE ARQUIVO FAZ:
1. conta eventos publicados por tipo.
2. conta conexoes SSE abertas e erros.
3. mede streams ativos.
4. conta conflitos de save por superficie.

PONTOS CRITICOS:
- estas metricas sao operacionais; nunca participam da regra de negocio.
- falhar ao incrementar metrica nao pode quebrar request nem stream.
"""

from prometheus_client import Counter, Gauge


STUDENT_SSE_EVENTS_PUBLISHED = Counter(
    'octobox_student_sse_events_published_total',
    'Total de eventos SSE do aluno publicados',
    ['event_type'],
)

STUDENT_SSE_STREAM_CONNECTIONS = Counter(
    'octobox_student_sse_stream_connections_total',
    'Total de conexoes SSE da ficha do aluno',
    ['status'],
)

STUDENT_SSE_ACTIVE_STREAMS = Gauge(
    'octobox_student_sse_active_streams',
    'Numero de streams SSE ativos da ficha do aluno',
)

STUDENT_SAVE_CONFLICTS = Counter(
    'octobox_student_save_conflicts_total',
    'Total de conflitos de save na ficha do aluno',
    ['surface'],
)


KNOWN_STUDENT_EVENT_TYPES = (
    'student.lock.acquired',
    'student.lock.released',
    'student.lock.preempted',
    'student.payment.updated',
    'student.enrollment.updated',
    'student.profile.updated',
)

KNOWN_STREAM_STATUSES = (
    'opened',
    'closed',
    'error',
)

KNOWN_CONFLICT_SURFACES = (
    'student-form',
    'drawer-profile',
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


def record_student_sse_event_published(event_type: str) -> None:
    STUDENT_SSE_EVENTS_PUBLISHED.labels(event_type=event_type or 'unknown').inc()


def record_student_sse_stream_connection(status: str) -> None:
    STUDENT_SSE_STREAM_CONNECTIONS.labels(status=status or 'unknown').inc()


def inc_student_sse_active_streams() -> None:
    STUDENT_SSE_ACTIVE_STREAMS.inc()


def dec_student_sse_active_streams() -> None:
    try:
        STUDENT_SSE_ACTIVE_STREAMS.dec()
    except ValueError:
        pass


def record_student_save_conflict(surface: str) -> None:
    STUDENT_SAVE_CONFLICTS.labels(surface=surface or 'unknown').inc()


def build_student_realtime_metrics_snapshot() -> dict:
    event_counts = {
        event_type: _read_counter_value(STUDENT_SSE_EVENTS_PUBLISHED, event_type=event_type)
        for event_type in KNOWN_STUDENT_EVENT_TYPES
    }
    stream_status_counts = {
        status: _read_counter_value(STUDENT_SSE_STREAM_CONNECTIONS, status=status)
        for status in KNOWN_STREAM_STATUSES
    }
    conflict_counts = {
        surface: _read_counter_value(STUDENT_SAVE_CONFLICTS, surface=surface)
        for surface in KNOWN_CONFLICT_SURFACES
    }
    active_streams = _read_gauge_value(STUDENT_SSE_ACTIVE_STREAMS)
    return {
        'event_counts': event_counts,
        'stream_status_counts': stream_status_counts,
        'conflict_counts': conflict_counts,
        'active_streams': active_streams,
        'events_total': sum(event_counts.values()),
        'stream_connections_total': sum(stream_status_counts.values()),
        'conflicts_total': sum(conflict_counts.values()),
    }


__all__ = [
    'dec_student_sse_active_streams',
    'build_student_realtime_metrics_snapshot',
    'inc_student_sse_active_streams',
    'record_student_save_conflict',
    'record_student_sse_event_published',
    'record_student_sse_stream_connection',
]
