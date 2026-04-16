"""
ARQUIVO: reprocessamento programado de webhooks vencidos.

POR QUE ELE EXISTE:
- fecha o lado simetrico da malha para `WebhookEvent.next_retry_at`.
- permite cron institucional para webhooks sem criar scheduler novo.
"""

from django.utils import timezone

from integrations.whatsapp.contracts import WhatsAppInboundPollVote
from monitoring.alert_siren import get_alert_siren_defense_policy
from monitoring.signal_mesh_metrics import record_retry_sweep
from monitoring.signal_mesh_runtime import remember_signal_mesh_sweep

from .models import WebhookDeliveryStatus, WebhookEvent
from .services import process_poll_vote_webhook


def _build_poll_vote_from_event(webhook_event: WebhookEvent) -> WhatsAppInboundPollVote | None:
    payload = webhook_event.payload or {}
    if payload.get('kind') != 'poll_vote':
        return None

    raw_payload = payload.get('raw_payload') or {}
    voter_phone = raw_payload.get('voter_phone') or raw_payload.get('phone') or ''
    poll_name = raw_payload.get('poll_name') or raw_payload.get('poll_title') or ''
    option_text = raw_payload.get('option_text') or raw_payload.get('option_voted') or ''
    event_id = raw_payload.get('event_id') or webhook_event.event_id or ''

    if not all([voter_phone, poll_name, option_text]):
        return None

    return WhatsAppInboundPollVote(
        phone=voter_phone,
        poll_title=poll_name,
        option_voted=option_text,
        external_id=event_id,
        event_id=event_id,
        raw_payload=raw_payload,
    )


def reprocess_due_webhook_events(*, limit: int = 25, now=None) -> dict[str, object]:
    current_time = now or timezone.now()
    defense_policy = get_alert_siren_defense_policy()
    due_queryset = WebhookEvent.objects.filter(
        status=WebhookDeliveryStatus.PENDING,
        next_retry_at__isnull=False,
        next_retry_at__lte=current_time,
    )
    due_backlog = due_queryset.count()
    if defense_policy.get('pause_webhook_retries'):
        skipped = [
            {'event_id': '', 'reason': 'alert-siren-contained'}
            for _ in range(min(due_backlog, 1))
        ]
        result = {
            'checked_at': current_time.isoformat(),
            'due_backlog': due_backlog,
            'processed_count': 0,
            'skipped_count': len(skipped),
            'processed': [],
            'skipped': skipped,
            'alert_siren_level': defense_policy.get('level', ''),
            'effective_limit': 0,
        }
        record_retry_sweep(
            channel='webhooks',
            due_backlog=due_backlog,
            dispatched_count=0,
            skipped=skipped,
        )
        remember_signal_mesh_sweep(channel='webhooks', result=result)
        return result

    effective_limit = limit
    if defense_policy.get('webhook_limit_cap') is not None:
        effective_limit = min(limit, defense_policy['webhook_limit_cap'])
    due_events = list(due_queryset.order_by('next_retry_at', 'created_at')[:effective_limit])

    processed = []
    skipped = []

    for webhook_event in due_events:
        poll_vote = _build_poll_vote_from_event(webhook_event)
        if poll_vote is None:
            skipped.append({'event_id': webhook_event.event_id or '', 'reason': 'unsupported-or-incomplete-payload'})
            continue

        result = process_poll_vote_webhook(poll_vote=poll_vote)
        processed.append(
            {
                'event_id': webhook_event.event_id or '',
                'accepted': result.accepted,
                'retry_action': result.retry_action,
                'failure_kind': result.failure_kind,
            }
        )

    result = {
        'checked_at': current_time.isoformat(),
        'due_backlog': due_backlog,
        'processed_count': len(processed),
        'skipped_count': len(skipped),
        'processed': processed,
        'skipped': skipped,
        'alert_siren_level': defense_policy.get('level', ''),
        'effective_limit': effective_limit,
    }
    record_retry_sweep(
        channel='webhooks',
        due_backlog=due_backlog,
        dispatched_count=len(processed),
        skipped=skipped,
    )
    remember_signal_mesh_sweep(channel='webhooks', result=result)
    return result


__all__ = ['reprocess_due_webhook_events']
