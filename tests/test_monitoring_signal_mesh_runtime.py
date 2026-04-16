"""
ARQUIVO: testes do snapshot runtime curado da Signal Mesh.

POR QUE ELE EXISTE:
- protege a leitura que o dashboard usa sem depender de Prometheus cru.
"""

from django.core.cache import cache
from django.test import SimpleTestCase

from monitoring.signal_mesh_runtime import (
    SIGNAL_MESH_RUNTIME_CACHE_KEY,
    get_signal_mesh_runtime_snapshot,
    remember_signal_mesh_sweep,
)


class MonitoringSignalMeshRuntimeTests(SimpleTestCase):
    def setUp(self):
        cache.delete(SIGNAL_MESH_RUNTIME_CACHE_KEY)

    def test_remember_signal_mesh_sweep_persists_curated_runtime_state(self):
        remember_signal_mesh_sweep(
            channel='jobs',
            result={
                'checked_at': '2026-04-16T12:00:00+00:00',
                'due_backlog': 3,
                'dispatched_count': 2,
                'skipped_count': 1,
                'skipped': [{'reason': 'missing-dispatch-context'}],
            },
        )

        snapshot = get_signal_mesh_runtime_snapshot()

        self.assertEqual(snapshot['jobs']['due_backlog'], 3)
        self.assertEqual(snapshot['jobs']['dispatched_count'], 2)
