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
    1. Pagamento de aluno em mensalidade (metadata.payment_id) — reconcilia o
       Payment no schema do box (metadata.box_schema resolve o tenant).
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
    from django_tenants.utils import schema_context

    from finance.application.commands import ReconcilePaymentCommand
    from finance.application.use_cases import execute_reconcile_payment_use_case

    payment_id = metadata.get('payment_id')
    version_locked = metadata.get('version_locked')
    amount_cents = session.get('amount_total')

    if not payment_id or version_locked is None or amount_cents is None:
        raise ValueError(f'Metadata incompleta no evento {event.event_id}: payment_id={payment_id}')

    box_schema = _resolve_box_schema(metadata.get('box_schema'), event)

    payment_intent_id = session.get('payment_intent') or ''
    session_id = session.get('id') or ''
    currency = session.get('currency') or 'brl'

    command = ReconcilePaymentCommand(
        payment_id=int(payment_id),
        amount_cents=int(amount_cents),
        stripe_event_id=event.event_id,
        version_locked=int(version_locked),
        stripe_session_id=session_id,
        stripe_payment_intent_id=payment_intent_id,
        currency=currency,
    )

    # Mapa public payment_intent -> box: fonte de verdade do roteamento de tenant
    # para eventos charge.* (refund/dispute) que NAO carregam nossa metadata.
    # Gravado em public (o router roda em public), antes do reconcile.
    _record_stripe_payment_ref(
        payment_intent_id=payment_intent_id,
        session_id=session_id,
        box_schema=box_schema,
        payment_id=int(payment_id),
    )

    # O webhook chega no schema public (esta em PUBLIC_SCHEMA_PATHS), mas Payment
    # vive no schema do box (TENANT_APP). Sem este schema_context, o reconcile
    # faz SELECT em public e estoura 'relation does not exist'. O box e resolvido
    # pela metadata gravada no checkout (em contexto de tenant) e validado abaixo.
    with schema_context(box_schema):
        execute_reconcile_payment_use_case(command)


def _record_stripe_payment_ref(*, payment_intent_id, session_id, box_schema, payment_id) -> None:
    """Grava/atualiza o mapa public payment_intent -> box (StripePaymentRef).

    Sem payment_intent nao da pra mapear (ex.: Sessions antigas ou metodos sem PI):
    nesse caso o evento charge.* correspondente cairia no fallback de operador.
    """
    if not payment_intent_id:
        return
    from integrations.stripe.models import StripePaymentRef

    StripePaymentRef.objects.update_or_create(
        payment_intent_id=payment_intent_id,
        defaults={
            'session_id': session_id,
            'box_schema': box_schema,
            'payment_id': payment_id,
        },
    )


def _resolve_box_schema(box_schema, event) -> str:
    """Valida o schema do box vindo da metadata contra um Box real.

    Defesa em profundidade: nunca abrir schema_context para um valor arbitrario.
    box_schema ausente/publico => Session criada antes do fix multi-tenant ou
    metadata adulterada. Falha NAO reprocessavel (ValueError) — o operador
    reconcilia manualmente e o evento fica no dead-letter com mensagem clara,
    em vez de falhar em silencio no schema public.
    """
    from django_tenants.utils import get_public_schema_name

    from control.models import Box

    if not box_schema or box_schema == get_public_schema_name():
        raise ValueError(
            f'Evento {event.event_id} sem box_schema valido na metadata — '
            f'impossivel reconciliar pagamento de aluno em multi-tenant '
            f'(box_schema={box_schema!r}).'
        )
    if not Box.objects.filter(schema_name=box_schema).exists():
        raise ValueError(
            f'Evento {event.event_id}: box_schema {box_schema!r} nao corresponde '
            f'a nenhum Box conhecido.'
        )
    return box_schema


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


def _lookup_payment_ref(payment_intent_id):
    """Resolve o StripePaymentRef (mapa public payment_intent -> box) ou None."""
    if not payment_intent_id:
        return None
    from integrations.stripe.models import StripePaymentRef

    return StripePaymentRef.objects.filter(payment_intent_id=payment_intent_id).first()


def _handle_charge_refunded(event: PaymentWebhookEvent) -> None:
    """charge.refunded: reflete no OctoBox um estorno feito do lado da Stripe.

    O evento traz um charge com payment_intent; resolvemos o box pelo
    StripePaymentRef (gravado na reconciliacao do checkout) e marcamos o Payment
    como REFUNDED no schema do box. Charge sem ref conhecido (ex.: checkout de
    early adopter) e ignorado (no-op) para nao poluir o dead-letter.
    """
    from django_tenants.utils import schema_context
    from finance.application.use_cases import execute_refund_payment_from_stripe_use_case

    charge = event.payload.get('data', {}).get('object', {})
    payment_intent_id = charge.get('payment_intent') or ''
    ref = _lookup_payment_ref(payment_intent_id)
    if ref is None:
        logger.info(
            '_handle_charge_refunded: sem StripePaymentRef para pi=%s. event=%s (ignorado).',
            payment_intent_id, event.event_id,
        )
        return

    with schema_context(ref.box_schema):
        execute_refund_payment_from_stripe_use_case(
            payment_id=ref.payment_id,
            stripe_charge_id=charge.get('id') or '',
            stripe_event_id=event.event_id,
        )


def _handle_charge_dispute(event: PaymentWebhookEvent) -> None:
    """charge.dispute.created/closed: registra a disputa (chargeback) para
    observabilidade. Resolve o box via StripePaymentRef e grava audit event no
    schema do box. Nao muda o status do Payment — o desfecho financeiro chega
    como charge.refunded (perdida) ou nada (ganha).
    """
    from django_tenants.utils import schema_context

    dispute = event.payload.get('data', {}).get('object', {})
    payment_intent_id = dispute.get('payment_intent') or ''
    ref = _lookup_payment_ref(payment_intent_id)
    if ref is None:
        logger.info(
            '_handle_charge_dispute: sem StripePaymentRef para pi=%s. event=%s',
            payment_intent_id, event.event_id,
        )
        return

    logger.warning(
        '_handle_charge_dispute: DISPUTA box=%s payment=%s status=%s event=%s',
        ref.box_schema, ref.payment_id, dispute.get('status', ''), event.event_id,
    )
    with schema_context(ref.box_schema):
        _record_dispute_audit(ref.payment_id, dispute, event)


def _record_dispute_audit(payment_id, dispute, event) -> None:
    from auditing import log_audit_event
    from finance.models import Payment

    payment = Payment.objects.filter(pk=payment_id).first()
    if payment is None:
        return
    log_audit_event(
        actor=None,
        action='payment_dispute_via_stripe',
        target=payment,
        description=f'Disputa/chargeback Stripe ({event.event_type}) status={dispute.get("status", "")}',
        metadata={
            'stripe_event_id': event.event_id,
            'event_type': event.event_type,
            'dispute_status': dispute.get('status', ''),
            'dispute_reason': dispute.get('reason', ''),
        },
    )


_HANDLERS = {
    'checkout.session.completed': _handle_checkout_session_completed,
    'invoice.payment_failed': _handle_invoice_payment_failed,       # Sprint 3: suspende Box
    'invoice.payment_succeeded': _handle_invoice_payment_succeeded, # Sprint 3: reativa Box
    'charge.refunded': _handle_charge_refunded,                     # P2.2: estorno do lado Stripe
    'charge.dispute.created': _handle_charge_dispute,               # P2.2: chargeback (observabilidade)
    'charge.dispute.closed': _handle_charge_dispute,
}

__all__ = ['route_payment_webhook_event']
