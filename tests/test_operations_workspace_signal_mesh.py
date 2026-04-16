"""
ARQUIVO: testes do resumo do Red Beacon nos workspaces operacionais.

POR QUE ELE EXISTE:
- garante que owner e manager enxerguem o resumo curado da malha.
"""

from django.test import TestCase
from django.utils import timezone

from operations.queries import build_manager_workspace_snapshot, build_owner_workspace_snapshot


class OperationsWorkspaceSignalMeshTests(TestCase):
    def test_build_owner_workspace_snapshot_includes_red_beacon_card(self):
        snapshot = build_owner_workspace_snapshot(today=timezone.localdate())

        self.assertIn('red_beacon_snapshot', snapshot)
        self.assertEqual(snapshot['metric_cards'][-1]['eyebrow'], 'Red Beacon')
        self.assertIn('alert_siren', snapshot['red_beacon_snapshot'])

    def test_build_manager_workspace_snapshot_includes_red_beacon_card(self):
        snapshot = build_manager_workspace_snapshot(actor=None)

        self.assertIn('red_beacon_snapshot', snapshot)
        self.assertEqual(snapshot['metric_cards'][-1]['eyebrow'], 'Red Beacon')
        self.assertIn('alert_siren', snapshot['red_beacon_snapshot'])
