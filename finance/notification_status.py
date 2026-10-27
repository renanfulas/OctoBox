"""Safe operational read model for payment notification deliveries."""

import re

from django.db.models import Count, Q, Sum
from django.utils import timezone

from finance.models import PaymentNotificationDelivery, PaymentNotificationDeliveryStatus


_STATUS_LABELS = {
    PaymentNotificationDeliveryStatus.PENDING: 'Pendente',
    PaymentNotificationDeliveryStatus.LEASED: 'Em processamento',
    PaymentNotificationDeliveryStatus.PROVIDER_ACCEPTED: 'Aceito pelo provedor',
    PaymentNotificationDeliveryStatus.DELIVERED: 'Entrega confirmada',
    PaymentNotificationDeliveryStatus.RETRY_WAIT: 'Aguardando rechecagem',
    PaymentNotificationDeliveryStatus.UNKNOWN: 'Resultado desconhecido',
    PaymentNotificationDeliveryStatus.FAILED: 'Falha definitiva',
    PaymentNotificationDeliveryStatus.SKIPPED: 'Ignorado',
}
_CHANNEL_LABELS = {'email': 'E-mail', 'push': 'Push', 'whatsapp': 'WhatsApp'}
_SAFE_REASON = re.compile(r'^[a-z0-9_]{1,64}$')


def build_payment_notification_operations_snapshot(*, attention_limit=10):
    """Return state counts and a PII-free intervention queue for finance staff."""
    counts = {status: 0 for status, _label in PaymentNotificationDeliveryStatus.choices}
    for row in PaymentNotificationDelivery.objects.values('status').annotate(total=Count('pk')):
        if row['status'] in counts:
            counts[row['status']] = row['total']

    attention = PaymentNotificationDelivery.objects.filter(
        status__in=(PaymentNotificationDeliveryStatus.UNKNOWN, PaymentNotificationDeliveryStatus.FAILED),
    )
    attention_count = attention.count()
    attention_by_channel = {
        row['channel']: row['total']
        for row in attention.values('channel').annotate(total=Count('pk'))
    }
    queued = PaymentNotificationDelivery.objects.filter(
        status__in=(
            PaymentNotificationDeliveryStatus.PENDING,
            PaymentNotificationDeliveryStatus.LEASED,
            PaymentNotificationDeliveryStatus.RETRY_WAIT,
        ),
    )
    oldest_queued_at = queued.order_by('created_at').values_list('created_at', flat=True).first()
    duplicate_suppressed_total = PaymentNotificationDelivery.objects.aggregate(
        total=Count('pk', filter=Q(duplicate_suppressed_count__gt=0))
    )['total']
    duplicate_suppressed_attempts = PaymentNotificationDelivery.objects.aggregate(
        total=Sum('duplicate_suppressed_count')
    )['total']
    items = []
    for row in attention.order_by('updated_at', 'pk').values(
        'id', 'payment_id', 'channel', 'status', 'reason_code', 'updated_at',
    )[:max(1, int(attention_limit))]:
        reason_code = row['reason_code'] or ''
        if not _SAFE_REASON.fullmatch(reason_code):
            reason_code = 'unclassified_reason'
        status = row['status']
        channel = row['channel']
        items.append({
            'delivery_id': row['id'],
            'payment_id': row['payment_id'],
            'channel_label': _CHANNEL_LABELS.get(channel, 'Outro canal'),
            'status_label': _STATUS_LABELS.get(status, 'Estado desconhecido'),
            'reason_code': reason_code,
            'updated_at': row['updated_at'],
        })

    return {
        'status_counts': counts,
        'attention_count': attention_count,
        'attention_by_channel': attention_by_channel,
        'oldest_queued_at': oldest_queued_at,
        'oldest_queued_age_seconds': (
            max(0, int((timezone.now() - oldest_queued_at).total_seconds()))
            if oldest_queued_at else None
        ),
        'duplicate_suppressed_rows': duplicate_suppressed_total,
        'duplicate_suppressed_attempts': duplicate_suppressed_attempts or 0,
        'attention_items': items,
        'attention_truncated': attention_count > len(items),
    }


__all__ = ['build_payment_notification_operations_snapshot']
