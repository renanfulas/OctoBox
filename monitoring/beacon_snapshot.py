"""
ARQUIVO: snapshot curado do Red Beacon.

POR QUE ELE EXISTE:
- consolida sinais operacionais em leitura confiavel para dashboard e workspaces.
- prepara a emissao superior sem vazar telemetria bruta.
"""

from django.db import DatabaseError
from django.utils import timezone

from integrations.whatsapp.models import WebhookDeliveryStatus, WebhookEvent
from jobs.models import AsyncJob, JobStatus
from monitoring.signal_mesh_runtime import get_signal_mesh_runtime_snapshot


def _summarize_skips(skipped_items):
    summary = {}
    for item in skipped_items or []:
        reason = item.get('reason', 'unknown')
        summary[reason] = summary.get(reason, 0) + 1
    return [
        {'reason': reason, 'count': count}
        for reason, count in sorted(summary.items())
    ]


def _count_due_async_jobs():
    try:
        return AsyncJob.objects.filter(
            status=JobStatus.PENDING,
            next_retry_at__isnull=False,
            next_retry_at__lte=timezone.now(),
        ).count()
    except DatabaseError:
        runtime_snapshot = get_signal_mesh_runtime_snapshot()
        return runtime_snapshot.get('jobs', {}).get('due_backlog', 0)


def _count_due_webhooks():
    try:
        return WebhookEvent.objects.filter(
            status=WebhookDeliveryStatus.PENDING,
            next_retry_at__isnull=False,
            next_retry_at__lte=timezone.now(),
        ).count()
    except DatabaseError:
        runtime_snapshot = get_signal_mesh_runtime_snapshot()
        return runtime_snapshot.get('webhooks', {}).get('due_backlog', 0)


def build_signal_mesh_beacon_snapshot():
    runtime_snapshot = get_signal_mesh_runtime_snapshot()
    jobs_runtime = runtime_snapshot.get('jobs', {})
    webhooks_runtime = runtime_snapshot.get('webhooks', {})
    jobs_due_backlog = _count_due_async_jobs()
    webhooks_due_backlog = _count_due_webhooks()
    total_due_backlog = jobs_due_backlog + webhooks_due_backlog

    return {
        'headline': 'Retry backlog pede olhar agora' if total_due_backlog > 0 else 'Signal Mesh sob controle',
        'summary': (
            'Existem itens vencidos aguardando sweep. Vale acompanhar o corredor antes que a fila endureca.'
            if total_due_backlog > 0 else
            'Nenhum retry vencido esta parado agora. O corredor da malha esta respirando bem.'
        ),
        'tone': 'warning' if total_due_backlog > 0 else 'success',
        'total_due_backlog': total_due_backlog,
        'channels': [
            {
                'label': 'Jobs',
                'channel': 'jobs',
                'due_backlog': jobs_due_backlog,
                'last_checked_at': jobs_runtime.get('checked_at', ''),
                'last_dispatched_count': jobs_runtime.get('dispatched_count', 0),
                'last_skipped_count': jobs_runtime.get('skipped_count', 0),
                'skip_reasons': _summarize_skips(jobs_runtime.get('skipped', [])),
            },
            {
                'label': 'Webhooks',
                'channel': 'webhooks',
                'due_backlog': webhooks_due_backlog,
                'last_checked_at': webhooks_runtime.get('checked_at', ''),
                'last_dispatched_count': webhooks_runtime.get('dispatched_count', 0),
                'last_skipped_count': webhooks_runtime.get('skipped_count', 0),
                'skip_reasons': _summarize_skips(webhooks_runtime.get('skipped', [])),
            },
        ],
    }


def build_red_beacon_snapshot():
    signal_mesh = build_signal_mesh_beacon_snapshot()
    from monitoring.alert_siren import build_alert_siren_snapshot

    alert_siren = build_alert_siren_snapshot(signal_mesh_snapshot=signal_mesh)
    tone = alert_siren['tone'] if alert_siren['tone'] != 'success' else signal_mesh['tone']
    mode = 'stable'
    if alert_siren['level'] == 'low':
        mode = 'watch'
    elif alert_siren['level'] == 'medium':
        mode = 'pulsing'
    elif alert_siren['level'] == 'high':
        mode = 'alarm'

    return {
        'mode': mode,
        'tone': tone,
        'headline': signal_mesh['headline'],
        'summary': signal_mesh['summary'],
        'label': 'Red Beacon',
        'signal_mesh': signal_mesh,
        'alert_siren': alert_siren,
    }


__all__ = [
    'build_red_beacon_snapshot',
    'build_signal_mesh_beacon_snapshot',
]
