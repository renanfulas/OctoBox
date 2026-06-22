"""
ARQUIVO: reconciliacao Stripe<->DB (rede de seguranca de fidelidade).

POR QUE ELE EXISTE:
- O webhook + o dead-letter sweep cobrem o fluxo normal, mas um evento que a
  Stripe nunca enviou (ou que o sweep esgotou) deixaria o Payment divergente em
  silencio. Este job le o estado real na Stripe e REPORTA divergencias para o
  operador agir — read-only na v1 (nao muta status automaticamente).

O QUE ELE FAZ:
1. Itera os boxes ativos (Payment e TENANT_APP) via schema_context.
2. Para cada Payment com vinculo Stripe atualizado na janela, le o PaymentIntent
   na Stripe e compara com o status local.
3. Registra cada divergencia como audit event (payment_stripe_drift) e devolve um
   relatorio agregado.

PONTOS CRITICOS:
- Roda a partir do schema public (cron); Box e SHARED.
- Read-only: nenhuma baixa/estorno e aplicado aqui — so deteccao e trilha.
"""

from datetime import timedelta

from django.utils import timezone
from django_tenants.utils import schema_context


def _detect_drift(local_status, state) -> str | None:
    from finance.models import PaymentStatus

    pi_status = state.get('pi_status', '') or ''
    refunded = bool(state.get('refunded', False))

    if refunded and local_status != PaymentStatus.REFUNDED:
        return 'stripe_refunded_local_not'
    if local_status == PaymentStatus.REFUNDED and not refunded:
        return 'local_refunded_stripe_not'
    if local_status == PaymentStatus.PAID and pi_status and pi_status != 'succeeded':
        return 'local_paid_pi_not_succeeded'
    return None


def reconcile_stripe_payments(*, days: int = 7, limit: int = 100, now=None) -> dict:
    from auditing import log_audit_event
    from control.models import Box
    from finance.models import Payment
    from integrations.stripe.services import get_stripe_payment_state

    current = now or timezone.now()
    since = current - timedelta(days=days)
    checked = 0
    drift: list[dict] = []

    for box in Box.objects.filter(status=Box.Status.ACTIVE):
        with schema_context(box.schema_name):
            payments = (
                Payment.objects
                .exclude(stripe_payment_intent_id='')
                .filter(updated_at__gte=since)
                .order_by('-updated_at')[:limit]
            )
            for payment in payments:
                checked += 1
                state = get_stripe_payment_state(payment.stripe_payment_intent_id)
                if state is None:
                    continue
                reason = _detect_drift(payment.status, state)
                if reason is None:
                    continue
                entry = {
                    'box': box.schema_name,
                    'payment_id': payment.id,
                    'reason': reason,
                    'local_status': payment.status,
                    'pi_status': state.get('pi_status', ''),
                    'refunded': bool(state.get('refunded', False)),
                }
                drift.append(entry)
                log_audit_event(
                    actor=None,
                    action='payment_stripe_drift',
                    target=payment,
                    description=f'Divergencia Stripe<->DB: {reason}',
                    metadata=entry,
                )

    return {
        'checked_at': current.isoformat(),
        'checked': checked,
        'drift_count': len(drift),
        'drift': drift,
    }


__all__ = ['reconcile_stripe_payments']
