"""
ARQUIVO: handler + endpoint HTTP do webhook Stripe do corredor de treinos
(Onda B2, Fatia B do CORDA — S3/D.000).

POR QUE ELE EXISTE:
- endpoint PROPRIO (`/treinos/stripe/webhook/`, S3): `integrations/stripe/
  router.py` nao muda uma linha. P5 do CORDA ("webhook de aluno suspende o
  BOX") deixa de ser bug a testar e vira IMPOSSIVEL por construcao — o
  caminho de codigo que altera `Box.status` simplesmente nao e alcancavel
  a partir daqui.
- reusa `PaymentWebhookEvent` (integrations/stripe/models.py) pra dedup por
  event_id — decisao N1 do CORDA: persistir o envelope bruto e transporte,
  nao decisao de negocio, e a fronteira certa pra isso e integrations/
  (compartilhada por todos os produtos), nao um modelo novo por produto.

ACAO MANUAL PENDENTE (nao e codigo): configurar um SEGUNDO endpoint no
dashboard da Stripe apontando pra esta URL, assinando checkout.session.
completed / invoice.payment_succeeded / invoice.payment_failed / customer.
subscription.updated / customer.subscription.deleted. Gera um webhook secret PROPRIO — nunca o mesmo de
STRIPE_WEBHOOK_SECRET (esse e do endpoint do box).

PONTOS CRITICOS:
- Discriminador de rota: `checkout.session.completed` chega com
  `metadata.product == 'coaching'` (setado no create da Session,
  stripe_checkout.py) — evento sem esse valor e ignorado, nunca adivinhado.
  Para os eventos de invoice/subscription (que nem sempre propagam
  metadata), o discriminador e resolver `PublicWorkoutSubscription` por
  `stripe_subscription_id` — se nao existe assinatura do corredor com
  aquele id, o evento nao e nosso e o handler so marca processado sem
  fazer nada. Mesma conta Stripe, tabelas completamente diferentes: um
  evento de assinatura do box nunca bate com um `stripe_subscription_id`
  do corredor.
- Nunca importa nada de integrations.stripe.router ou .services (N2/D.00) —
  so verify_stripe_webhook seria leitura, mas nem essa e usada aqui: o
  secret e outro (endpoint proprio), entao a verificacao tambem e propria.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from integrations.mesh import FAILURE_KIND_NON_RETRYABLE, FAILURE_KIND_RETRYABLE
from integrations.stripe.models import PaymentWebhookEvent

from . import billing
from .models import PublicWorkoutSubscription, PublicWorkoutSubscriptionStatus
from .stripe_checkout import _TIER_PRICE_SETTINGS

logger = logging.getLogger(__name__)


class PublicWorkoutStripeWebhookAuthError(Exception):
    """Payload ou assinatura invalidos — mesmo contrato de StripeWebhookAuthError."""


def verify_public_workout_stripe_webhook(raw_body: bytes, sig_header: str) -> dict:
    """Verifica a assinatura HMAC do endpoint PROPRIO do corredor.

    Nao reusa integrations.stripe.auth.verify_stripe_webhook: aquele modulo
    verifica contra STRIPE_WEBHOOK_SECRET (o secret do endpoint do BOX).
    Endpoint diferente, secret diferente — copiar o padrao aqui (D.00) e a
    escolha certa, nao um import que aplicaria o secret errado.
    """
    import stripe

    secret = (getattr(settings, 'PUBLIC_WORKOUT_STRIPE_WEBHOOK_SECRET', '') or '').strip()
    try:
        event = stripe.Webhook.construct_event(raw_body, sig_header, secret)
        return event.to_dict()
    except ValueError as exc:
        raise PublicWorkoutStripeWebhookAuthError('Invalid payload') from exc
    except stripe.error.SignatureVerificationError as exc:
        raise PublicWorkoutStripeWebhookAuthError('Invalid signature') from exc


def _cents_to_decimal(cents) -> Decimal:
    return Decimal(int(cents or 0)) / Decimal(100)


def _unix_to_date(timestamp) -> date:
    if not timestamp:
        return date.today()
    return datetime.fromtimestamp(int(timestamp), tz=dt_timezone.utc).date()


def _resolve_subscription_by_stripe_id(stripe_subscription_id: str) -> PublicWorkoutSubscription | None:
    if not stripe_subscription_id:
        return None
    return PublicWorkoutSubscription.objects.filter(stripe_subscription_id=stripe_subscription_id).first()


def _resolve_subscription_from_invoice(invoice: dict) -> PublicWorkoutSubscription | None:
    """Resolve inclusive quando a fatura chega antes do checkout webhook.

    A Stripe nao garante ordem entre endpoints/eventos. O checkout grava a
    identidade local em ``subscription_data.metadata``; nas faturas ela pode
    aparecer em ``subscription_details.metadata`` (API anterior) ou em
    ``parent.subscription_details.metadata`` (API Basil+). So aceitamos o
    fallback quando o produto esta explicitamente marcado como coaching.
    """
    parent = invoice.get('parent') or {}
    subscription_details = invoice.get('subscription_details') or parent.get('subscription_details') or {}
    stripe_subscription_id = invoice.get('subscription') or subscription_details.get('subscription') or ''
    subscription = _resolve_subscription_by_stripe_id(stripe_subscription_id)
    if subscription is not None:
        return subscription

    metadata = subscription_details.get('metadata') or {}
    if metadata.get('product') != 'coaching':
        return None
    # custom_price='1' (start_custom_price_subscription_checkout): o Price
    # e' ad-hoc (price_data), nunca vai bater com nenhum dos 3 Price ID
    # fixos -- divergencia esperada, nao fraude. So' o RT3 normal (tier
    # fixo) precisa do cross-check de Price ID abaixo.
    if metadata.get('custom_price') != '1':
        tier = metadata.get('tier')
        setting_name = _TIER_PRICE_SETTINGS.get(tier)
        expected_price_id = (getattr(settings, setting_name, '') or '').strip() if setting_name else ''
        line_items = (invoice.get('lines') or {}).get('data') or []
        first_line = line_items[0] if line_items else {}
        actual_price_id = ((first_line.get('pricing') or {}).get('price_details') or {}).get('price')
        actual_price_id = actual_price_id or (first_line.get('price') or {}).get('id') or ''
        if not expected_price_id or actual_price_id != expected_price_id:
            logger.error(
                'invoice do corredor fora de ordem com tier/price divergente; pagamento exige revisao manual. '
                'invoice=%s tier_metadata=%r real_price_id=%r',
                invoice.get('id'), tier, actual_price_id,
            )
            return None
    local_id = metadata.get('public_workout_subscription_id')
    try:
        subscription = PublicWorkoutSubscription.objects.get(pk=int(local_id))
    except (PublicWorkoutSubscription.DoesNotExist, TypeError, ValueError):
        return None

    if stripe_subscription_id:
        billing.link_stripe_ids(
            subscription,
            customer_id=invoice.get('customer') or subscription.stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
        )
    return subscription


def _confirm_tier_price(
    subscription: PublicWorkoutSubscription, *, stripe_subscription_id: str, tier_from_metadata: str | None,
    event_id: str, custom_price: bool = False,
) -> None:
    """Cross-check de D.3/RT3 sem conceder acesso antecipadamente.

    O Price ID REAL da assinatura precisa bater com o tier da metadata.
    Divergencia fica pendente para revisao manual. Este evento apenas liga
    IDs e registra o periodo; `invoice.payment_succeeded` e a unica prova
    financeira que promove a assinatura para ACTIVE.

    `custom_price=True` (start_custom_price_subscription_checkout): pula o
    cross-check de Price ID fixo -- o real e' um Price ad-hoc de proposito,
    nunca vai bater com _TIER_PRICE_SETTINGS. Ainda assim grava
    current_period_end normalmente, so' nao valida contra o tier.
    """
    if not stripe_subscription_id:
        return

    import stripe

    secret_key = (getattr(settings, 'STRIPE_SECRET_KEY', '') or '').strip()
    if not secret_key:
        logger.error('checkout.session.completed do corredor: STRIPE_SECRET_KEY ausente, nao foi possivel confirmar tier/price. event=%s', event_id)
        return
    stripe.api_key = secret_key

    stripe_subscription = stripe.Subscription.retrieve(stripe_subscription_id)
    real_price_id = stripe_subscription['items']['data'][0]['price']['id']

    if not custom_price:
        setting_name = _TIER_PRICE_SETTINGS.get(tier_from_metadata)
        configured_price_id = (getattr(settings, setting_name, '') or '').strip() if setting_name else ''

        if not configured_price_id or real_price_id != configured_price_id:
            logger.error(
                'checkout.session.completed do corredor: tier/price nao confere, fica pendente pra revisao manual. '
                'event=%s subscription_id=%s tier_metadata=%r real_price_id=%r',
                event_id, subscription.pk, tier_from_metadata, real_price_id,
            )
            return

    period_end = stripe_subscription.get('current_period_end')
    if not period_end:
        period_end = (stripe_subscription.get('items', {}).get('data') or [{}])[0].get('current_period_end')
    update_fields = ['updated_at']
    if period_end:
        subscription.current_period_end = datetime.fromtimestamp(int(period_end), tz=dt_timezone.utc)
        update_fields.append('current_period_end')
    subscription.save(update_fields=update_fields)
    return True


def _handle_checkout_session_completed(event: PaymentWebhookEvent) -> None:
    session = event.payload.get('data', {}).get('object', {})
    metadata = session.get('metadata', {}) or {}
    if metadata.get('product') != 'coaching':
        return  # nao e evento do corredor — o discriminador e a metadata setada no create da Session.

    subscription_local_id = metadata.get('public_workout_subscription_id')
    if not subscription_local_id:
        raise ValueError(f'checkout.session.completed do corredor sem public_workout_subscription_id. event={event.event_id}')

    try:
        subscription = PublicWorkoutSubscription.objects.get(pk=int(subscription_local_id))
    except (PublicWorkoutSubscription.DoesNotExist, ValueError, TypeError) as exc:
        raise ValueError(
            f'public_workout_subscription_id={subscription_local_id!r} nao existe. event={event.event_id}'
        ) from exc

    stripe_customer_id = session.get('customer') or ''
    stripe_subscription_id = session.get('subscription') or ''
    if stripe_customer_id and stripe_subscription_id:
        billing.link_stripe_ids(
            subscription, customer_id=stripe_customer_id, stripe_subscription_id=stripe_subscription_id
        )

    _confirm_tier_price(
        subscription,
        stripe_subscription_id=stripe_subscription_id,
        tier_from_metadata=metadata.get('tier'),
        event_id=event.event_id,
        custom_price=metadata.get('custom_price') == '1',
    )
    from public_workouts.acquisition import bind_acquisition_session, record_funnel_event
    from public_workouts.models import PublicWorkoutAcquisitionSession

    acquisition_session = None
    acquisition_session_id = metadata.get('acquisition_session_id')
    if acquisition_session_id:
        acquisition_session = PublicWorkoutAcquisitionSession.objects.filter(pk=acquisition_session_id).first()
        acquisition_session = bind_acquisition_session(
            acquisition_session, account=subscription.account, subscription=subscription,
        )
    if acquisition_session is None:
        logger.warning(
            'curva_checkout_without_attribution event_id=%s subscription_id=%s',
            event.event_id, subscription.pk,
        )
    record_funnel_event(
        'checkout_authorized', acquisition_session=acquisition_session,
        account=subscription.account, subscription=subscription,
        tier=subscription.tier,
    )


def _handle_invoice_payment_succeeded(event: PaymentWebhookEvent) -> None:
    invoice = event.payload.get('data', {}).get('object', {})
    subscription = _resolve_subscription_from_invoice(invoice)
    if subscription is None:
        return  # nao e uma assinatura do corredor — mesma conta Stripe, tabela diferente.

    billing.record_successful_invoice_payment(
        subscription,
        stripe_invoice_id=invoice.get('id') or '',
        gross_amount=_cents_to_decimal(invoice.get('amount_paid')),
        due_date=_unix_to_date(invoice.get('period_start')),
    )
    from public_workouts.models import PublicWorkoutWaitlistEntry, PublicWorkoutWaitlistStatus
    PublicWorkoutWaitlistEntry.objects.filter(
        email__iexact=subscription.account.email,
        tier=subscription.tier,
        status__in=(PublicWorkoutWaitlistStatus.WAITING, PublicWorkoutWaitlistStatus.INVITED),
    ).update(
        status=PublicWorkoutWaitlistStatus.CONVERTED,
        converted_at=timezone.now(),
    )
    from public_workouts.acquisition import record_funnel_event
    from public_workouts.models import PublicWorkoutAcquisitionSession

    acquisition_session = PublicWorkoutAcquisitionSession.objects.filter(
        subscription=subscription,
    ).first()
    if acquisition_session is None:
        logger.warning(
            'curva_invoice_without_attribution event_id=%s subscription_id=%s',
            event.event_id, subscription.pk,
        )
    record_funnel_event(
        'invoice_paid',
        acquisition_session=acquisition_session,
        account=subscription.account,
        subscription=subscription,
        tier=subscription.tier,
    )


def _handle_invoice_payment_failed(event: PaymentWebhookEvent) -> None:
    invoice = event.payload.get('data', {}).get('object', {})
    subscription = _resolve_subscription_from_invoice(invoice)
    if subscription is None:
        return

    billing.handle_failed_invoice_payment(
        subscription,
        stripe_invoice_id=invoice.get('id') or '',
        gross_amount=_cents_to_decimal(invoice.get('amount_due')),
        due_date=_unix_to_date(invoice.get('due_date') or invoice.get('period_end')),
    )
    from public_workouts.acquisition import record_funnel_event
    from public_workouts.models import PublicWorkoutAcquisitionSession
    record_funnel_event(
        'payment_failed',
        acquisition_session=PublicWorkoutAcquisitionSession.objects.filter(subscription=subscription).first(),
        account=subscription.account, subscription=subscription,
    )


def _handle_subscription_deleted(event: PaymentWebhookEvent) -> None:
    stripe_subscription = event.payload.get('data', {}).get('object', {})
    subscription = _resolve_subscription_by_stripe_id(stripe_subscription.get('id') or '')
    if subscription is None:
        return

    billing.mark_subscription_canceled(subscription, reason=f'customer.subscription.deleted (event={event.event_id})')


def _handle_subscription_updated(event: PaymentWebhookEvent) -> None:
    """Reconcilia mudanca de tier/status feita no Customer Portal."""
    stripe_subscription = event.payload.get('data', {}).get('object', {})
    subscription = _resolve_subscription_by_stripe_id(stripe_subscription.get('id') or '')
    if subscription is None:
        return

    items = stripe_subscription.get('items', {}).get('data') or []
    price_id = ((items[0].get('price') or {}).get('id') if items else '') or ''
    tier = next(
        (
            candidate_tier for candidate_tier, setting_name in _TIER_PRICE_SETTINGS.items()
            if (getattr(settings, setting_name, '') or '').strip() == price_id
        ),
        None,
    )
    if tier is None:
        # custom_monthly_price preenchido (start_custom_price_subscription_
        # checkout): Price ad-hoc de proposito, nunca vai bater com os 3
        # fixos -- nao ha tier canonico pra reconciliar aqui, mantem o que
        # ja esta salvo. Sem isso ficaria cego pra status (past_due/paused/
        # canceled) de todo aluno com valor personalizado, nunca so' o
        # tier. Price REALMENTE desconhecido (nem custom) continua sendo
        # erro, pendente de revisao manual.
        if subscription.custom_monthly_price is None:
            logger.error(
                'customer.subscription.updated com Price ID desconhecido. event=%s subscription=%s price=%r',
                event.event_id, subscription.pk, price_id,
            )
            return
        tier = subscription.tier

    stripe_status = stripe_subscription.get('status') or ''
    has_confirmed_payment = subscription.payments.filter(
        status='paid', paid_at__isnull=False,
    ).exists()
    status_map = {
        # Evento de assinatura pode chegar antes de invoice.payment_succeeded.
        # Sem pagamento local confirmado, nao libera acesso nem trabalho.
        'active': (
            PublicWorkoutSubscriptionStatus.ACTIVE
            if has_confirmed_payment or subscription.status == PublicWorkoutSubscriptionStatus.ACTIVE
            else PublicWorkoutSubscriptionStatus.PENDING_PAYMENT
        ),
        'trialing': PublicWorkoutSubscriptionStatus.PENDING_PAYMENT,
        'past_due': PublicWorkoutSubscriptionStatus.PAST_DUE,
        'unpaid': PublicWorkoutSubscriptionStatus.PAST_DUE,
        'paused': PublicWorkoutSubscriptionStatus.SUSPENDED,
        'canceled': PublicWorkoutSubscriptionStatus.CANCELED,
    }
    new_status = status_map.get(stripe_status, subscription.status)
    previous_status = subscription.status
    update_fields = ['updated_at']
    if subscription.tier != tier:
        subscription.tier = tier
        update_fields.append('tier')
    if subscription.status != new_status:
        subscription.status = new_status
        update_fields.append('status')
    period_end = stripe_subscription.get('current_period_end')
    if period_end:
        subscription.current_period_end = datetime.fromtimestamp(int(period_end), tz=dt_timezone.utc)
        update_fields.append('current_period_end')
    subscription.save(update_fields=update_fields)
    if previous_status != new_status:
        from .models import PublicWorkoutSubscriptionEvent

        PublicWorkoutSubscriptionEvent.objects.create(
            subscription=subscription,
            from_status=previous_status,
            to_status=new_status,
            reason=f'customer.subscription.updated (event={event.event_id})',
        )


_HANDLERS = {
    'checkout.session.completed': _handle_checkout_session_completed,
    'invoice.payment_succeeded': _handle_invoice_payment_succeeded,
    'invoice.payment_failed': _handle_invoice_payment_failed,
    'customer.subscription.updated': _handle_subscription_updated,
    'customer.subscription.deleted': _handle_subscription_deleted,
}


def route_public_workout_stripe_event(event: PaymentWebhookEvent) -> None:
    """Despacha um PaymentWebhookEvent ja persistido para o handler certo.

    Mesmo contrato de integrations.stripe.router.route_payment_webhook_event
    (D.00 — copia o padrao): tipo sem handler so marca processado; ValueError
    e falha nao-reprocessavel (dado ruim, reenviar nao resolve); qualquer
    outra excecao e retentavel.
    """
    handler = _HANDLERS.get(event.event_type)
    if handler is None:
        event.mark_processed()
        return

    try:
        handler(event)
        event.mark_processed()
    except ValueError as exc:
        logger.error('route_public_workout_stripe_event: erro nao reprocessavel. event=%s err=%s', event.event_id, exc)
        event.register_failure(failure_kind=FAILURE_KIND_NON_RETRYABLE, error_message=str(exc))
    except Exception as exc:
        logger.exception('route_public_workout_stripe_event: falha reprocessavel. event=%s', event.event_id)
        event.register_failure(failure_kind=FAILURE_KIND_RETRYABLE, error_message=str(exc))


@csrf_exempt
@require_POST
def public_workout_stripe_webhook_receiver(request):
    """Endpoint proprio do corredor (`/treinos/stripe/webhook/`). Sem regra de
    negocio aqui — so autentica, persiste e despacha (mesmo contrato de
    finance/views/stripe_webhooks.py)."""
    sig_header = request.headers.get('Stripe-Signature', '')

    try:
        event = verify_public_workout_stripe_webhook(request.body, sig_header)
    except PublicWorkoutStripeWebhookAuthError as exc:
        logger.warning('Webhook Stripe (corredor) rejeitado: %s. IP=%s', exc, request.META.get('REMOTE_ADDR'))
        return HttpResponse(status=400, content=str(exc))

    try:
        webhook_event = PaymentWebhookEvent.objects.create(
            event_id=event['id'],
            event_type=event['type'],
            payload=event,
        )
    except IntegrityError:
        return HttpResponse(status=200, content='Duplicate event')

    route_public_workout_stripe_event(webhook_event)
    return HttpResponse(status=200)


__all__ = [
    'PublicWorkoutStripeWebhookAuthError',
    'public_workout_stripe_webhook_receiver',
    'route_public_workout_stripe_event',
    'verify_public_workout_stripe_webhook',
]
