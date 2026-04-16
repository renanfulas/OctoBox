"""
ARQUIVO: testes das metricas minimas do runner da Signal Mesh.

POR QUE ELE EXISTE:
- garante que a observabilidade basica do corredor continue disponivel.
"""

from django.test import SimpleTestCase

from monitoring.signal_mesh_metrics import record_retry_sweep


class MonitoringSignalMeshMetricsTests(SimpleTestCase):
    def test_record_retry_sweep_accepts_backlog_dispatch_and_skips(self):
        record_retry_sweep(
            channel='jobs',
            due_backlog=5,
            dispatched_count=2,
            skipped=[{'reason': 'missing-dispatch-context'}],
        )
