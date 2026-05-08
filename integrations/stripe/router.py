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
    """Roteia checkout.session.completed para o handler correto.

    O OctoBox tem dois fluxos de checkout que reusam o mesmo evento Stripe:
    1. Pagamento de aluno em mensalidade (metadata.payment_id) — fluxo legado.
    2. Cadastro de Early Adopter (metadata.pending_signup_id) — fluxo novo.

    A escolha e feita pela metadata da Session. Outros tipos sao logados e ignorados,
    nao falham para nao bloquear o webhook.
    """
    session = event.payload.get('data', {}).get('object', {})
    metadata = session.get('metadata', {}) or {}

    if metadata.get('pending_signup_id'):
        _handle_early_adopter_signup(event, session, metadata)
        return

    if metadata.get('payment_id'):
        _handle_student_payment(event, session, metadata)
        return

    logger.info(
        'route_payment_webhook_event: session sem metadata reconhecivel. event=%s',
        event.event_id,
    )


def _handle_student_payment(event, session, metadata):
    from finance.application.commands import ReconcilePaymentCommand
    from finance.application.use_cases import execute_reconcile_payment_use_case

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


def _handle_early_adopter_signup(event, session, metadata):
    """Marca o PendingSignup como pago e dispara email de ativacao.

    Falhas no envio do email sao logadas, mas nao falham o webhook — o
    operador pode reenviar manualmente pelo Django admin.
    """
    from signup.services import (
        generate_magic_token,
        mark_pending_signup_paid,
        send_onboarding_email,
    )

    pending_id = metadata.get('pending_signup_id')
    try:
        pending_id_int = int(pending_id)
    except (TypeError, ValueError):
        raise ValueError(f'pending_signup_id invalido no evento {event.event_id}: {pending_id!r}')

    pending = mark_pending_signup_paid(
        pending_signup_id=pending_id_int,
        stripe_session_id=session.get('id', ''),
        stripe_customer_id=session.get('customer', '') or '',
        stripe_subscription_id=session.get('subscription', '') or '',
    )
    if pending is None:
        return  # ja logado em mark_pending_signup_paid

    token = generate_magic_token(pending)
    activation_path = f'/onboarding/{token}/'
    site_url = _resolve_marketing_site_url()
    activation_url = f'{site_url}{activation_path}'

    sent = send_onboarding_email(pending, activation_url=activation_url)
    if not sent:
        logger.warning(
            '_handle_early_adopter_signup: email nao enviado para pending=%s. '
            'Operador pode reenviar pelo Django admin.',
            pending.pk,
        )


def _resolve_marketing_site_url() -> str:
    from django.conf import settings

    explicit = getattr(settings, 'MARKETING_SITE_URL', '').strip()
    if explicit:
        return explicit.rstrip('/')

    trusted = getattr(settings, 'CSRF_TRUSTED_ORIGINS', []) or []
    for origin in trusted:
        if 'octoboxfit' in origin and 'app.' not in origin:
            return origin.rstrip('/')

    return 'https://octoboxfit.com.br'


_HANDLERS = {
    'checkout.session.completed': _handle_checkout_session_completed,
}

__all__ = ['route_payment_webhook_event']
