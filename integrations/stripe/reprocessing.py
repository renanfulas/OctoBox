"""
ARQUIVO: reprocessamento programado de eventos Stripe vencidos (dead-letter drain).

POR QUE ELE EXISTE:
- Fecha o lado simetrico da malha para `PaymentWebhookEvent.next_retry_at`.
- Antes deste sweep, um evento Stripe que falhasse de forma reprocessavel ficava
  PENDING para sempre — `run_signal_mesh_retry_sweep` so drenava jobs e webhooks
  do WhatsApp. Resultado: baixa de pagamento perdida em silencio (F3).

O QUE ESTE ARQUIVO FAZ:
1. Seleciona PaymentWebhookEvent PENDING com next_retry_at vencido.
2. Re-roteia cada um para o dominio correto; eventos do Curva usam seu
   roteador proprio e cobrancas do box continuam no roteador existente.
3. Respeita a defense policy do alert-siren (pausa/cap) igual ao corredor WhatsApp.
4. Emite as mesmas metricas da Signal Mesh com channel='stripe'.

PONTOS CRITICOS:
- Roda em schema public (PaymentWebhookEvent e SHARED); cada roteador resolve
  sua assinatura/tenant dentro do handler.
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


def _stripe_object_id(value) -> str:
    """Aceita tanto o ID normal quanto o objeto expandido da Stripe."""
    if isinstance(value, dict):
        return str(value.get('id') or '')
    return str(value or '')


def _is_public_workout_event(event: PaymentWebhookEvent) -> bool:
    """Reconhece eventos Curva antes do roteador genérico do OctoBox.

    O webhook do corredor compartilha a tabela de envelopes Stripe, mas tem
    roteador e regras de negócio próprios. Checkout e invoice carregam a
    marca `product=coaching`; alguns eventos de invoice/subscription podem
    chegar sem metadata, então também resolvemos pelo ID local da assinatura.
    """
    from public_workouts.models import PublicWorkoutSubscription

    obj = ((event.payload or {}).get('data') or {}).get('object') or {}
    metadata = obj.get('metadata') or {}
    parent_details = ((obj.get('parent') or {}).get('subscription_details') or {})
    subscription_details = obj.get('subscription_details') or parent_details
    subscription_metadata = subscription_details.get('metadata') or {}

    if metadata.get('product') == 'coaching' or subscription_metadata.get('product') == 'coaching':
        return True
    if metadata.get('public_workout_subscription_id') or subscription_metadata.get(
        'public_workout_subscription_id'
    ):
        return True

    subscription_id = (
        _stripe_object_id(obj.get('subscription'))
        or _stripe_object_id(subscription_details.get('subscription'))
        or _stripe_object_id(obj.get('id') if event.event_type.startswith('customer.subscription.') else '')
    )
    return bool(
        subscription_id
        and PublicWorkoutSubscription.objects.filter(stripe_subscription_id=subscription_id).exists()
    )


def _route_stripe_webhook_event(event: PaymentWebhookEvent) -> None:
    """Despacha cada corredor para seu roteador de domínio correspondente."""
    if _is_public_workout_event(event):
        from public_workouts.stripe_handlers import route_public_workout_stripe_event

        route_public_workout_stripe_event(event)
        return
    route_payment_webhook_event(event)


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
        _route_stripe_webhook_event(event)
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
