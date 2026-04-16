"""
ARQUIVO: testes da Alert Siren minima.

POR QUE ELE EXISTE:
- garante que a sirene nasca de risco consolidado e devolva postura defensiva objetiva.
"""

from django.test import SimpleTestCase, override_settings

from monitoring.alert_siren import build_alert_siren_snapshot


class MonitoringAlertSirenTests(SimpleTestCase):
    def test_build_alert_siren_snapshot_is_silent_when_signal_mesh_is_clean(self):
        snapshot = build_alert_siren_snapshot(
            signal_mesh_snapshot={
                'total_due_backlog': 0,
                'channels': [
                    {'last_skipped_count': 0, 'skip_reasons': []},
                    {'last_skipped_count': 0, 'skip_reasons': []},
                ],
            }
        )

        self.assertEqual(snapshot['level'], 'silent')
        self.assertFalse(snapshot['defense_policy']['pause_webhook_retries'])

    @override_settings(ALERT_SIREN_HIGH_BACKLOG_THRESHOLD=3, ALERT_SIREN_HIGH_SKIP_THRESHOLD=2)
    def test_build_alert_siren_snapshot_enters_high_containment_under_heavy_pressure(self):
        snapshot = build_alert_siren_snapshot(
            signal_mesh_snapshot={
                'total_due_backlog': 4,
                'channels': [
                    {
                        'last_skipped_count': 2,
                        'skip_reasons': [{'reason': 'missing-dispatch-context', 'count': 2}],
                    },
                ],
            }
        )

        self.assertEqual(snapshot['level'], 'high')
        self.assertTrue(snapshot['defense_policy']['pause_webhook_retries'])
