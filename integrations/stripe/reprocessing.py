"""
ARQUIVO: reprocessamento programado de eventos Stripe vencidos (dead-letter drain).

POR QUE ELE EXISTE:
- Fecha o lado simetrico da malha para `PaymentWebhookEvent.next_retry_at`.
- Antes deste sweep, um evento Stripe que falhasse de forma reprocessavel ficava
  PENDING para sempre — `run_signal_mesh_retry_sweep` so drenava jobs e webhooks
  do WhatsApp. Resultado: baixa de pagamento perdida em silencio (F3).

O QUE ESTE ARQUIVO FAZ:
1. Seleciona PaymentWebhookEvent PENDING com next_retry_at vencido.
2. Re-roteia cada um via route_payment_webhook_event (que ja faz schema_context,
   mark_processed e register_failure com backoff da mesh).
3. Respeita a defense policy do alert-siren (pausa/cap) igual ao corredor WhatsApp.
4. Emite as mesmas metricas da Signal Mesh com channel='stripe'.

PONTOS CRITICOS:
- Roda em schema public (PaymentWebhookEvent e SHARED); a resolucao de tenant da
  baixa acontece dentro do handler (metadata.box_schema), nao aqui.
- A lista de eventos e materializada ANTES do loop: re-rotear muda o status e nao
  deve afetar a iteracao.
"""

from django.utils import timezone

from monitoring.alert_siren import get_alert_siren_defense_policy
from monitoring.signal_mesh_metrics import record_retry_sweep
from monitoring.signal_mesh_runtime import remember_signal_mesh_sweep

from .models import PaymentWebhookEvent, PaymentWebhookStatus
from .router import route_payment_webhook_event

_CHANNEL = 'stripe'


def reprocess_due_stripe_webhook_events(*, limit: int = 25, now=None) -> dict[str, object]:
    current_time = now or timezone.now()
    defense_policy = get_alert_siren_defense_policy()

    due_queryset = PaymentWebhookEvent.objects.filter(
        status=PaymentWebhookStatus.PENDING,
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
        record_retry_sweep(channel=_CHANNEL, due_backlog=due_backlog, dispatched_count=0, skipped=skipped)
        remember_signal_mesh_sweep(channel=_CHANNEL, result=result)
        return result

    effective_limit = limit
    if defense_policy.get('webhook_limit_cap') is not None:
        effective_limit = min(limit, defense_policy['webhook_limit_cap'])
    due_events = list(due_queryset.order_by('next_retry_at', 'created_at')[:effective_limit])

    processed = []
    for event in due_events:
        route_payment_webhook_event(event)
        event.refresh_from_db(fields=['status'])
        processed.append({'event_id': event.event_id or '', 'status': event.status})

    result = {
        'checked_at': current_time.isoformat(),
        'due_backlog': due_backlog,
        'processed_count': len(processed),
        'skipped_count': 0,
        'processed': processed,
        'skipped': [],
        'alert_siren_level': defense_policy.get('level', ''),
        'effective_limit': effective_limit,
    }
    record_retry_sweep(channel=_CHANNEL, due_backlog=due_backlog, dispatched_count=len(processed), skipped=[])
    remember_signal_mesh_sweep(channel=_CHANNEL, result=result)
    return result


__all__ = ['reprocess_due_stripe_webhook_events']
