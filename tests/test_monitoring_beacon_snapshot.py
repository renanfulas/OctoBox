"""
ARQUIVO: testes do snapshot curado do Red Beacon.

POR QUE ELE EXISTE:
- garante que a emissao consolidada continue legivel para dashboard e workspaces.
"""

from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from monitoring.beacon_snapshot import build_red_beacon_snapshot
from monitoring.signal_mesh_runtime import remember_signal_mesh_sweep


class MonitoringBeaconSnapshotTests(TestCase):
    def setUp(self):
        # Sprint 3 mudou signal_mesh_runtime para cache per-tenant
        # (chave = 'signal_mesh_runtime:v1:{schema_name}'). Antes era
        # chave global SIGNAL_MESH_RUNTIME_CACHE_KEY. cache.delete dessa
        # constante (agora deprecated) deletava o lugar errado e estado
        # do test anterior vazava (sintoma: AssertionError 4 != 3 quando
        # o test esperado totalizava so 3, mas tinha 1 stale de outro
        # test no cache per-tenant).
        # cache.clear() e seguro em LocMemCache de teste e elimina
        # qualquer chave per-tenant herdada.
        cache.clear()

    def test_build_red_beacon_snapshot_exposes_signal_mesh_summary(self):
        now = timezone.now()
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
        remember_signal_mesh_sweep(
            channel='webhooks',
            result={
                'checked_at': now.isoformat(),
                'due_backlog': 0,
                'dispatched_count': 0,
                'skipped_count': 0,
                'skipped': [],
            },
        )

        with patch('monitoring.beacon_snapshot._model_table_exists', return_value=False):
            snapshot = build_red_beacon_snapshot()

        self.assertEqual(snapshot['label'], 'Red Beacon')
        self.assertEqual(snapshot['signal_mesh']['total_due_backlog'], 1)
        self.assertEqual(snapshot['tone'], 'warning')
        self.assertEqual(snapshot['alert_siren']['level'], 'low')

    def test_build_red_beacon_snapshot_falls_back_when_webhook_table_is_unavailable(self):
        now = timezone.now()
        remember_signal_mesh_sweep(
            channel='webhooks',
            result={
                'checked_at': now.isoformat(),
                'due_backlog': 3,
                'dispatched_count': 0,
                'skipped_count': 0,
                'skipped': [],
            },
        )

        with patch('monitoring.beacon_snapshot._model_table_exists', return_value=False):
            snapshot = build_red_beacon_snapshot()

        self.assertEqual(snapshot['signal_mesh']['total_due_backlog'], 3)
        self.assertEqual(snapshot['signal_mesh']['channels'][1]['due_backlog'], 3)
        self.assertEqual(snapshot['tone'], 'warning')
