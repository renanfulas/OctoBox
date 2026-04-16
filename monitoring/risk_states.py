"""
ARQUIVO: consolidacao minima de risco para Alert Siren.

POR QUE ELE EXISTE:
- traduz backlog e skips da Signal Mesh em um risco operacional pequeno e objetivo.
- evita que a sirene nasca de sensacao ou de telemetria crua.
"""

from django.conf import settings


ALERT_SIREN_LEVEL_SILENT = 'silent'
ALERT_SIREN_LEVEL_LOW = 'low'
ALERT_SIREN_LEVEL_MEDIUM = 'medium'
ALERT_SIREN_LEVEL_HIGH = 'high'

SEVERE_SKIP_REASONS = {
    'missing-dispatch-context',
    'unregistered-job-type',
    'unsupported-or-incomplete-payload',
    'alert-siren-contained',
}


def _count_severe_skips(channels):
    severe_skip_count = 0
    for channel in channels:
        for reason in channel.get('skip_reasons', []):
            if reason.get('reason') in SEVERE_SKIP_REASONS:
                severe_skip_count += reason.get('count', 0)
    return severe_skip_count


def build_signal_mesh_risk_state(signal_mesh_snapshot: dict | None) -> dict:
    snapshot = signal_mesh_snapshot or {}
    channels = snapshot.get('channels', [])
    total_due_backlog = snapshot.get('total_due_backlog', 0)
    total_skipped = sum(channel.get('last_skipped_count', 0) for channel in channels)
    severe_skip_count = _count_severe_skips(channels)

    low_backlog = getattr(settings, 'ALERT_SIREN_LOW_BACKLOG_THRESHOLD', 1)
    medium_backlog = getattr(settings, 'ALERT_SIREN_MEDIUM_BACKLOG_THRESHOLD', 5)
    high_backlog = getattr(settings, 'ALERT_SIREN_HIGH_BACKLOG_THRESHOLD', 12)
    high_skip_threshold = getattr(settings, 'ALERT_SIREN_HIGH_SKIP_THRESHOLD', 5)

    level = ALERT_SIREN_LEVEL_SILENT
    if total_due_backlog >= high_backlog or severe_skip_count >= high_skip_threshold:
        level = ALERT_SIREN_LEVEL_HIGH
    elif total_due_backlog >= medium_backlog or total_skipped >= medium_backlog:
        level = ALERT_SIREN_LEVEL_MEDIUM
    elif total_due_backlog >= low_backlog or total_skipped > 0:
        level = ALERT_SIREN_LEVEL_LOW

    tone_by_level = {
        ALERT_SIREN_LEVEL_SILENT: 'success',
        ALERT_SIREN_LEVEL_LOW: 'warning',
        ALERT_SIREN_LEVEL_MEDIUM: 'warning',
        ALERT_SIREN_LEVEL_HIGH: 'danger',
    }

    return {
        'level': level,
        'tone': tone_by_level[level],
        'total_due_backlog': total_due_backlog,
        'total_skipped': total_skipped,
        'severe_skip_count': severe_skip_count,
    }


__all__ = [
    'ALERT_SIREN_LEVEL_HIGH',
    'ALERT_SIREN_LEVEL_LOW',
    'ALERT_SIREN_LEVEL_MEDIUM',
    'ALERT_SIREN_LEVEL_SILENT',
    'SEVERE_SKIP_REASONS',
    'build_signal_mesh_risk_state',
]
