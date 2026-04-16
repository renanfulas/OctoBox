"""
ARQUIVO: snapshot runtime curado da Signal Mesh.

POR QUE ELE EXISTE:
- guarda o ultimo sweep de retries em formato legivel para dashboard e Beacon futuro.
- evita que a borda precise ler Prometheus cru para entender a malha.
"""

from django.core.cache import cache


SIGNAL_MESH_RUNTIME_CACHE_KEY = 'signal_mesh_runtime:v1'
SIGNAL_MESH_RUNTIME_TTL_SECONDS = 60 * 60 * 6


def _read_runtime_state() -> dict:
    cached = cache.get(SIGNAL_MESH_RUNTIME_CACHE_KEY)
    return cached if isinstance(cached, dict) else {}


def remember_signal_mesh_sweep(*, channel: str, result: dict) -> dict:
    state = _read_runtime_state()
    state[channel] = {
        'checked_at': result.get('checked_at', ''),
        'due_backlog': result.get('due_backlog', 0),
        'dispatched_count': result.get('dispatched_count', result.get('processed_count', 0)),
        'skipped_count': result.get('skipped_count', 0),
        'skipped': result.get('skipped', []),
    }
    cache.set(SIGNAL_MESH_RUNTIME_CACHE_KEY, state, timeout=SIGNAL_MESH_RUNTIME_TTL_SECONDS)
    return state[channel]


def get_signal_mesh_runtime_snapshot() -> dict:
    return _read_runtime_state()


__all__ = [
    'SIGNAL_MESH_RUNTIME_CACHE_KEY',
    'SIGNAL_MESH_RUNTIME_TTL_SECONDS',
    'get_signal_mesh_runtime_snapshot',
    'remember_signal_mesh_sweep',
]
