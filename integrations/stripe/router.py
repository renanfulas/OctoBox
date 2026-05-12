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




def _handle_invoice_payment_failed(event: PaymentWebhookEvent) -> None:
    """Suspende o Box quando pagamento da subscription falha.

    Sprint 3: implementa o fluxo de suspensao automatica por inadimplencia.
    Box.status = SUSPENDED bloqueia acesso ao painel do Owner (verificado por
    TenantBySessionMiddleware) mas nao deleta dados nem arquiva o schema.

    Recovery: quando invoice.payment_succeeded chegar (retry Stripe), Box e reativado.
    """
    invoice = event.payload.get('data', {}).get('object', {})
    subscription_id = invoice.get('subscription', '')
    customer_id = invoice.get('customer', '')

    if not subscription_id and not customer_id:
        logger.warning(
            '_handle_invoice_payment_failed: sem subscription_id nem customer_id. event=%s',
            event.event_id,
        )
        return

    from control.models import Box
    from django.utils import timezone as dj_tz

    box = None
    if subscription_id:
        box = Box.objects.filter(stripe_subscription_id=subscription_id).first()
    if box is None and customer_id:
        box = Box.objects.filter(stripe_customer_id=customer_id).first()

    if box is None:
        logger.info(
            '_handle_invoice_payment_failed: nenhum Box encontrado. subscription=%s customer=%s event=%s',
            subscription_id, customer_id, event.event_id,
        )
        return

    if box.status == Box.Status.SUSPENDED:
        logger.info('_handle_invoice_payment_failed: Box %s ja esta SUSPENDED.', box.slug)
        return

    Box.objects.filter(pk=box.pk).update(
        status=Box.Status.SUSPENDED,
        suspended_at=dj_tz.now(),
    )
    logger.warning(
        '_handle_invoice_payment_failed: Box %s SUSPENSO por falha de pagamento. event=%s',
        box.slug, event.event_id,
    )

    from control.models import PlatformAuditEvent
    try:
        PlatformAuditEvent.objects.create(
            target_box=box,
            kind='box.suspended_payment_failed',
            payload={
                'stripe_event_id': event.event_id,
                'subscription_id': subscription_id,
                'customer_id': customer_id,
            },
        )
    except Exception:
        logger.exception('_handle_invoice_payment_failed: falha ao registrar PlatformAuditEvent')


def _handle_invoice_payment_succeeded(event: PaymentWebhookEvent) -> None:
    """Reativa o Box quando um pagamento anteriormente falho e bem sucedido (retry Stripe).

    Sprint 3: recovery automatico de Box SUSPENDED por falha de pagamento.
    Nao reativa Box ARCHIVED (requer intervencao manual).
    """
    invoice = event.payload.get('data', {}).get('object', {})
    subscription_id = invoice.get('subscription', '')
    customer_id = invoice.get('customer', '')

    from control.models import Box
    from django.utils import timezone as dj_tz

    box = None
    if subscription_id:
        box = Box.objects.filter(stripe_subscription_id=subscription_id).first()
    if box is None and customer_id:
        box = Box.objects.filter(stripe_customer_id=customer_id).first()

    if box is None:
        return  # nao e um box conhecido — ignorar silenciosamente

    if box.status != Box.Status.SUSPENDED:
        return  # nao estava suspenso — nada a fazer

    Box.objects.filter(pk=box.pk).update(
        status=Box.Status.ACTIVE,
        suspended_at=None,
    )
    logger.info(
        '_handle_invoice_payment_succeeded: Box %s REATIVADO apos pagamento. event=%s',
        box.slug, event.event_id,
    )

    from control.models import PlatformAuditEvent
    try:
        PlatformAuditEvent.objects.create(
            target_box=box,
            kind='box.reactivated_payment_recovered',
            payload={'stripe_event_id': event.event_id},
        )
    except Exception:
        logger.exception('_handle_invoice_payment_succeeded: falha ao registrar PlatformAuditEvent')


_HANDLERS = {
    'checkout.session.completed': _handle_checkout_session_completed,
    'invoice.payment_failed': _handle_invoice_payment_failed,       # Sprint 3: suspende Box
    'invoice.payment_succeeded': _handle_invoice_payment_succeeded, # Sprint 3: reativa Box
}

__all__ = ['route_payment_webhook_event']
