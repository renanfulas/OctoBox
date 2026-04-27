"""
ARQUIVO: roteador de eventos Stripe para use cases do domínio finance.

POR QUE ELE EXISTE:
- Desacopla o envelope bruto do Stripe da lógica de negócio em finance/application/.
- A view cria o PaymentWebhookEvent; o router decide qual use case acionar.
- Segue a regra da Signal Mesh: payload externo não chega cru ao núcleo.

O QUE ESTE ARQUIVO FAZ:
1. Recebe um PaymentWebhookEvent já persistido.
2. Extrai o comando correto do payload normalizado.
3. Chama o use case correspondente.
4. Marca o evento como processado ou registra falha.

PONTOS CRITICOS:
- Nunca importar stripe diretamente aqui — o payload já está normalizado em JSON.
- Adicionar novos event_types como novas funções _handle_*, não como ifs crescentes.
"""

import logging

from integrations.mesh import FAILURE_KIND_NON_RETRYABLE, FAILURE_KIND_RETRYABLE

from .models import PaymentWebhookEvent

logger = logging.getLogger(__name__)


def route_payment_webhook_event(event: PaymentWebhookEvent) -> None:
    handler = _HANDLERS.get(event.event_type)
    if handler is None:
        event.mark_processed()
        return

    try:
        handler(event)
        event.mark_processed()
    except ValueError as exc:
        logger.error('route_payment_webhook_event: erro não reprocessável. event=%s err=%s', event.event_id, exc)
        event.register_failure(
            failure_kind=FAILURE_KIND_NON_RETRYABLE,
            error_message=str(exc),
        )
    except Exception as exc:
        logger.exception('route_payment_webhook_event: falha reprocessável. event=%s', event.event_id)
        event.register_failure(
            failure_kind=FAILURE_KIND_RETRYABLE,
            error_message=str(exc),
        )


def _handle_checkout_session_completed(event: PaymentWebhookEvent) -> None:
    from finance.application.commands import ReconcilePaymentCommand
    from finance.application.use_cases import execute_reconcile_payment_use_case

    session = event.payload.get('data', {}).get('object', {})
    metadata = session.get('metadata', {})

    payment_id = metadata.get('payment_id')
    version_locked = metadata.get('version_locked')
    amount_cents = session.get('amount_total')

    if not payment_id or version_locked is None or amount_cents is None:
        raise ValueError(f'Metadata incompleta no evento {event.event_id}: payment_id={payment_id}')

    command = ReconcilePaymentCommand(
        payment_id=int(payment_id),
        amount_cents=int(amount_cents),
        stripe_event_id=event.event_id,
        version_locked=int(version_locked),
    )
    execute_reconcile_payment_use_case(command)


_HANDLERS = {
    'checkout.session.completed': _handle_checkout_session_completed,
}

__all__ = ['route_payment_webhook_event']
