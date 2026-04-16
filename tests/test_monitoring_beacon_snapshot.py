"""
ARQUIVO: testes do snapshot curado do Red Beacon.

POR QUE ELE EXISTE:
- garante que a emissao consolidada continue legivel para dashboard e workspaces.
"""

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from integrations.whatsapp.models import WebhookEvent
from monitoring.beacon_snapshot import build_red_beacon_snapshot
from monitoring.signal_mesh_runtime import SIGNAL_MESH_RUNTIME_CACHE_KEY, remember_signal_mesh_sweep


class MonitoringBeaconSnapshotTests(TestCase):
    def setUp(self):
        cache.delete(SIGNAL_MESH_RUNTIME_CACHE_KEY)

    def test_build_red_beacon_snapshot_exposes_signal_mesh_summary(self):
        now = timezone.now()
        WebhookEvent.objects.create(
            event_id='evt-beacon-1',
            provider='evolution',
            payload={'kind': 'poll_vote', 'raw_payload': {}},
            status='pending',
            next_retry_at=now,
        )
        remember_signal_mesh_sweep(
            channel='jobs',
            result={
                'checked_at': now.isoformat(),
                'due_backlog': 1,
                'dispatched_count': 1,
                'skipped_count': 0,
                'skipped': [],
            },
        )

        snapshot = build_red_beacon_snapshot()

        self.assertEqual(snapshot['label'], 'Red Beacon')
        self.assertEqual(snapshot['signal_mesh']['total_due_backlog'], 1)
        self.assertEqual(snapshot['tone'], 'warning')
        self.assertEqual(snapshot['alert_siren']['level'], 'low')
