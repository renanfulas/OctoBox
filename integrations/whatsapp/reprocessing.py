"""Tenant-aware retry sweep for encrypted WhatsApp poll inbox rows."""

from __future__ import annotations

from django.utils import timezone
from django_tenants.utils import schema_context

from control.models import Box
from integrations.whatsapp.contracts import WhatsAppInboundPollVote
from monitoring.alert_siren import get_alert_siren_defense_policy
from monitoring.signal_mesh_metrics import record_retry_sweep
from monitoring.signal_mesh_runtime import remember_signal_mesh_sweep

from .models import WebhookDeliveryStatus, WebhookEvent, WhatsAppPollWebhookIntent
from .services import process_poll_vote_webhook


def reprocess_due_webhook_events(*, limit: int = 25, now=None) -> dict[str, object]:
    current_time = now or timezone.now()
    safe_limit = max(0, int(limit))
    defense_policy = get_alert_siren_defense_policy()
    effective_limit = safe_limit
    if defense_policy.get('webhook_limit_cap') is not None:
        effective_limit = min(safe_limit, max(0, int(defense_policy['webhook_limit_cap'])))

    active_boxes = list(
        Box.objects.filter(status=Box.Status.ACTIVE).only('schema_name').order_by('schema_name')
    )
    due_by_schema = []
    due_backlog = 0
    for box in active_boxes:
        with schema_context(box.schema_name):
            queryset = WhatsAppPollWebhookIntent.objects.filter(
                status=WhatsAppPollWebhookIntent.Status.PENDING,
                next_retry_at__isnull=False,
                next_retry_at__lte=current_time,
            ).order_by('next_retry_at', 'created_at', 'pk')
            due_backlog += queryset.count()
            due_by_schema.append((box.schema_name, queryset))

    # Legacy public rows cannot be assigned to a Box reliably. Count them for
    # operator visibility but never retry them under an inferred search_path.
    with schema_context('public'):
        legacy_unrouted = WebhookEvent.objects.filter(
            status=WebhookDeliveryStatus.PENDING,
            next_retry_at__isnull=False,
            next_retry_at__lte=current_time,
        ).count()

    if defense_policy.get('pause_webhook_retries'):
        skipped_count = min(due_backlog, effective_limit) + min(legacy_unrouted, 1)
        skipped = [{'event_id': '', 'reason': 'alert-siren-contained'}] if skipped_count else []
        result = {
            'checked_at': current_time.isoformat(),
            'due_backlog': due_backlog,
            'legacy_unrouted_count': legacy_unrouted,
            'processed_count': 0,
            'skipped_count': skipped_count,
            'processed': [],
            'skipped': skipped,
            'alert_siren_level': defense_policy.get('level', ''),
            'effective_limit': 0,
        }
        record_retry_sweep(
            channel='webhooks',
            due_backlog=due_backlog + legacy_unrouted,
            dispatched_count=0,
            skipped=skipped,
        )
        remember_signal_mesh_sweep(channel='webhooks', result=result)
        return result

    processed = []
    skipped = []
    for schema_name, queryset in due_by_schema:
        remaining = effective_limit - len(processed)
        if remaining <= 0:
            break
        with schema_context(schema_name):
            intents = list(queryset[:remaining])
        for intent in intents:
            vote = WhatsAppInboundPollVote(
                phone=intent.phone,
                poll_title=intent.poll_title,
                option_voted=intent.option_voted,
                external_id=intent.event_id,
                event_id=intent.event_id,
            )
            result_item = process_poll_vote_webhook(
                poll_vote=vote,
                tenant_schema=schema_name,
                now=current_time,
            )
            processed.append(
                {
                    'tenant_schema': schema_name,
                    'event_id': intent.event_id,
                    'accepted': result_item.accepted,
                    'retry_action': result_item.retry_action,
                    'failure_kind': result_item.failure_kind,
                }
            )

    if legacy_unrouted:
        skipped.append({'event_id': '', 'reason': 'legacy-event-without-tenant-route'})
    result = {
        'checked_at': current_time.isoformat(),
        'due_backlog': due_backlog,
        'legacy_unrouted_count': legacy_unrouted,
        'processed_count': len(processed),
        'skipped_count': len(skipped),
        'processed': processed,
        'skipped': skipped,
        'alert_siren_level': defense_policy.get('level', ''),
        'effective_limit': effective_limit,
    }
    record_retry_sweep(
        channel='webhooks',
        due_backlog=due_backlog + legacy_unrouted,
        dispatched_count=len(processed),
        skipped=skipped,
    )
    remember_signal_mesh_sweep(channel='webhooks', result=result)
    return result


__all__ = ['reprocess_due_webhook_events']
