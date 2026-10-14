"""
ARQUIVO: checkout Stripe do corredor de treinos (Onda B2, Fatia B do CORDA).

POR QUE ELE EXISTE:
- S3/D.000 do CORDA (docs/plans/public-workouts-produtizacao-corda.md): o
  corredor tem checkout PROPRIO — nunca chama create_checkout_session do
  box (signup/services.py) nem importa integrations/stripe/services.py
  (N2). Resolve a propria conta e nunca aciona o roteador do box.

DECISAO DO RENAN: reusar a MESMA conta Stripe do box, sem Connect Express.
C5 do CORDA e explicito — Connect so entra na Entrega 5, junto com o
multi-personal ("enquanto for um personal so, o repasse nao existe").
Consequencia direta: `application_fee_amount` fica sempre 0 e
`gross_amount == net_amount` em todo PublicWorkoutPayment criado por este
fluxo — os tres campos do modelo (C3) ja suportam isso sem migration nova.

PONTOS CRITICOS:
- `stripe.api_key` e global do processo (C1 do CORDA) — mutar em runtime e
  race condition SE houver mais de uma conta Stripe no processo. Hoje so
  existe uma (a do box, reusada aqui de proposito), entao e inofensivo.
  No dia em que o corredor ganhar Connect Express (multi-personal), este
  MESMO padrao vira o bug que C1 descreve — ai sim migrar pra
  `stripe.StripeClient(api_key=...)` por instancia. Ponteiro, nao trabalho
  desta onda.
- idempotency_key inclui o id da PublicWorkoutSubscription e o price_id
  (mesmo raciocinio de signup/services.py: trocar o price no .env sem
  mudar a chave faria a Stripe devolver a Session cacheada com o preco
  ANTIGO).
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import transaction

from .models import PublicWorkoutTier

# Entrega 5 (Escala, tier plumbing, D.3): um Price ID Stripe por tier — nunca
# um preco so decidido por dinheiro/intencao. Reusado por stripe_handlers.py
# pro cross-check de RT3 (tier errado por falha de metadata).
_TIER_PRICE_SETTINGS = {
    PublicWorkoutTier.ESSENCIAL: 'PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL',
    PublicWorkoutTier.COMPLETO: 'PUBLIC_WORKOUT_STRIPE_PRICE_ID_COMPLETO',
    PublicWorkoutTier.PREMIUM: 'PUBLIC_WORKOUT_STRIPE_PRICE_ID_PREMIUM',
}

class PublicWorkoutStripeNotConfiguredError(RuntimeError):
    """Levantada quando o Price ID do tier (ou PUBLIC_WORKOUT_STRIPE_PRICE_ID) nao esta configurado."""


class PublicWorkoutCheckoutSessionError(RuntimeError):
    """A Stripe could not safely expire a stale checkout before retry."""


def _resolve_price_id(tier: str) -> str:
    setting_name = _TIER_PRICE_SETTINGS.get(tier)
    if setting_name is None:
        raise PublicWorkoutStripeNotConfiguredError(f'tier {tier!r} desconhecido — sem Price ID associado.')
    price_id = (getattr(settings, setting_name, '') or '').strip()
    if not price_id:
        raise PublicWorkoutStripeNotConfiguredError(
            f'{setting_name} nao configurado. Defina no .env e reinicie o servidor.'
        )
    return price_id


def get_completed_lead_checkout(*, lead):
    """Return a completed Checkout Session before a repeated signup can mutate its lead."""
    if not lead.stripe_checkout_session_id:
        return None
    import stripe

    secret_key = (getattr(settings, 'STRIPE_SECRET_KEY', '') or '').strip()
    if not secret_key:
        raise PublicWorkoutStripeNotConfiguredError('STRIPE_SECRET_KEY nao definida.')
    stripe.api_key = secret_key
    try:
        session = stripe.checkout.Session.retrieve(lead.stripe_checkout_session_id)
    except Exception as exc:
        if getattr(exc, 'code', '') == 'resource_missing':
            return None
        raise PublicWorkoutCheckoutSessionError('Nao foi possivel verificar o checkout anterior.') from exc
    if session.status != 'complete':
        return None
    if session.payment_status != 'paid':
        raise PublicWorkoutCheckoutSessionError('O pagamento anterior ainda esta sendo processado.')
    return session


def start_subscription_checkout(
    *, subscription, success_url: str, cancel_url: str, acquisition_session_id=None
) -> str:
    """Cria stripe.checkout.Session(mode='subscription') pra assinatura do corredor.

    Devolve a URL hospedada da Stripe para redirect. `subscription` e a
    PublicWorkoutSubscription ja resolvida/criada por quem chama (ver
    billing.get_or_create_subscription) — este modulo nao decide identidade,
    so fala com a Stripe.
    """
    # Import tardio (mesmo padrao de signup/services.py): nao torna o app
    # dependente da lib stripe em ambiente de teste que nao precisa dela.
    import stripe

    secret_key = (getattr(settings, 'STRIPE_SECRET_KEY', '') or '').strip()
    if not secret_key:
        raise PublicWorkoutStripeNotConfiguredError('STRIPE_SECRET_KEY nao definida.')
    stripe.api_key = secret_key

    price_id = _resolve_price_id(subscription.tier)
    account = subscription.account
    metadata = {
        'product': 'coaching',
        'public_workout_subscription_id': str(subscription.pk),
        'plan_slug': subscription.plan_slug or '',
        'tier': subscription.tier,
        'offer_version': subscription.offer_version or '',
        'service_policy_version': subscription.service_policy_version or '',
        'terms_version': subscription.terms_version or '',
        'privacy_version': subscription.privacy_version or '',
        'guarantee_model': subscription.guarantee_model,
        'acquisition_session_id': str(acquisition_session_id or ''),
    }

    session = stripe.checkout.Session.create(
        mode='subscription',
        payment_method_types=['card'],
        line_items=[{'price': price_id, 'quantity': 1}],
        # Permite resgatar cupons no plano Completo. A elegibilidade do WILLY
        # fica limitada ao produto Curva — Completo na própria Stripe.
        allow_promotion_codes=(subscription.tier == PublicWorkoutTier.COMPLETO),
        customer_email=account.email,
        client_reference_id=str(subscription.pk),
        success_url=success_url,
        cancel_url=cancel_url,
        # metadata.product='coaching' e o discriminador (D.0 do CORDA): o
        # webhook do corredor so processa eventos com esse valor — nunca
        # resolve Box, nunca alcanca o roteador do box (S3). metadata.tier
        # e o que stripe_handlers.py cruza contra o Price ID real da
        # assinatura Stripe. A autorizacao do checkout nao ativa acesso:
        # apenas invoice.payment_succeeded pode fazer isso (D.3/RT3).
        metadata=metadata,
        subscription_data={'metadata': metadata},
        idempotency_key=(
            f'public-workout-subscription-{subscription.pk}-{price_id[-8:]}-'
            f'{(subscription.offer_version or "legacy")[-12:]}'
        ),
    )
    if subscription.contracted_price_id != price_id:
        subscription.contracted_price_id = price_id
        subscription.save(update_fields=['contracted_price_id', 'updated_at'])
    return session.url


@transaction.atomic
def start_checkout_lead_session(*, lead, success_url: str, cancel_url: str) -> str:
    """Start or resume checkout without creating a student account."""
    import stripe

    # Serialize parallel submit requests for one lead: both requests must not
    # create separate payable Stripe sessions for the same email.
    lead = type(lead).objects.select_for_update().get(pk=lead.pk)

    secret_key = (getattr(settings, 'STRIPE_SECRET_KEY', '') or '').strip()
    if not secret_key:
        raise PublicWorkoutStripeNotConfiguredError('STRIPE_SECRET_KEY nao definida.')
    stripe.api_key = secret_key
    price_id = _resolve_price_id(lead.tier)
    if lead.stripe_checkout_session_id:
        try:
            existing = stripe.checkout.Session.retrieve(lead.stripe_checkout_session_id)
        except Exception as exc:
            if getattr(exc, 'code', '') == 'resource_missing':
                existing = None
            else:
                raise PublicWorkoutCheckoutSessionError(
                    'Nao foi possivel verificar o checkout anterior.'
                ) from exc
        if existing is not None and existing.status == 'complete':
            if existing.payment_status == 'paid':
                return success_url.replace('{CHECKOUT_SESSION_ID}', existing.id)
            raise PublicWorkoutCheckoutSessionError('O pagamento anterior ainda esta sendo processado.')
        if existing is not None and existing.status == 'open':
            existing_metadata = existing.get('metadata', {}) or {}
            metadata_matches = all(
                existing_metadata.get(key, '') == value
                for key, value in {
                    'tier': lead.tier,
                    'offer_version': lead.offer_version,
                    'service_policy_version': lead.service_policy_version,
                    'terms_version': lead.terms_version,
                    'privacy_version': lead.privacy_version,
                    'guarantee_model': lead.guarantee_model,
                }.items()
            )
            if metadata_matches and existing.url:
                return existing.url
            try:
                stripe.checkout.Session.expire(lead.stripe_checkout_session_id)
            except Exception as exc:
                raise PublicWorkoutCheckoutSessionError(
                    'Nao foi possivel encerrar a sessao de checkout anterior.'
                ) from exc
    metadata = {
        'product': 'coaching',
        'public_workout_checkout_lead_id': str(lead.pk),
        'tier': lead.tier,
        'offer_version': lead.offer_version,
        'service_policy_version': lead.service_policy_version,
        'terms_version': lead.terms_version,
        'privacy_version': lead.privacy_version,
        'guarantee_model': lead.guarantee_model,
        'acquisition_session_id': str(lead.acquisition_session_id or ''),
    }
    session = stripe.checkout.Session.create(
        mode='subscription', payment_method_types=['card'],
        line_items=[{'price': price_id, 'quantity': 1}],
        allow_promotion_codes=(lead.tier == PublicWorkoutTier.COMPLETO),
        customer_email=lead.email, client_reference_id=f'lead-{lead.pk}',
        success_url=success_url, cancel_url=cancel_url,
        metadata=metadata, subscription_data={'metadata': metadata},
        idempotency_key=f'public-workout-lead-{lead.pk}-{price_id[-8:]}-{uuid.uuid4().hex}',
    )
    lead.stripe_checkout_session_id = session.id
    lead.save(update_fields=['stripe_checkout_session_id', 'updated_at'])
    return session.url


def start_custom_price_subscription_checkout(
    *, subscription, success_url: str, cancel_url: str, acquisition_session_id=None
) -> str:
    """Checkout de assinatura com valor negociado (sem Price ID fixo).

    Pros alunos legados que nunca passaram pelo checkout dos 3 planos
    (Essencial/Completo/Premium) e pagam um valor combinado individualmente
    fora da Stripe: em vez de resolver um Price ID pre-cadastrado
    (_resolve_price_id), usa `price_data` pra criar o Price ad-hoc na hora,
    com o valor de `subscription.custom_monthly_price`. Precisa desse campo
    preenchido -- e' o admin (PublicWorkoutSubscriptionAdmin) quem grava,
    nunca um valor vindo de request.

    metadata['custom_price']='1' avisa stripe_handlers._confirm_tier_price
    (RT3) pra pular o cross-check de Price ID fixo -- o real DIVERGE de
    proposito aqui, nao e fraude.
    """
    import stripe

    if subscription.custom_monthly_price is None:
        raise PublicWorkoutStripeNotConfiguredError(
            'custom_monthly_price nao definido nesta assinatura -- preencha no admin antes de gerar o link.'
        )

    secret_key = (getattr(settings, 'STRIPE_SECRET_KEY', '') or '').strip()
    if not secret_key:
        raise PublicWorkoutStripeNotConfiguredError('STRIPE_SECRET_KEY nao definida.')
    stripe.api_key = secret_key

    unit_amount = int((subscription.custom_monthly_price * 100).to_integral_value())
    account = subscription.account
    metadata = {
        'product': 'coaching',
        'public_workout_subscription_id': str(subscription.pk),
        'plan_slug': subscription.plan_slug or '',
        'tier': subscription.tier,
        'custom_price': '1',
        'offer_version': subscription.offer_version or '',
        'service_policy_version': subscription.service_policy_version or '',
        'terms_version': subscription.terms_version or '',
        'privacy_version': subscription.privacy_version or '',
        'guarantee_model': subscription.guarantee_model,
        'acquisition_session_id': str(acquisition_session_id or ''),
    }

    session = stripe.checkout.Session.create(
        mode='subscription',
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'brl',
                'unit_amount': unit_amount,
                'recurring': {'interval': 'month'},
                'product_data': {
                    'name': f'Consultoria Curva — {subscription.plan_slug or account.email}',
                },
            },
            'quantity': 1,
        }],
        customer_email=account.email,
        client_reference_id=str(subscription.pk),
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
        subscription_data={'metadata': metadata},
        # inclui unit_amount na chave: valor renegociado precisa de Session
        # nova, nunca reaproveitar a Session cacheada do valor antigo.
        idempotency_key=f'public-workout-subscription-custom-{subscription.pk}-{unit_amount}',
    )
    return session.url


def start_customer_portal_session(*, customer_id: str, return_url: str) -> str:
    """Cria stripe.billing_portal.Session pra o aluno gerenciar/cancelar a
    propria assinatura direto com a Stripe (Onda B2, item 6 — Customer
    Portal).

    So fala com a Stripe, mesmo padrao de start_subscription_checkout:
    quem decide SE o aluno pode acessar (precisa ja ter `stripe_customer_id`
    preenchido, ou seja, ja ter passado por 1 checkout completo) e quem
    chama esta funcao, nao ela. O cancelamento feito pelo aluno dentro do
    portal chega de volta como o MESMO webhook que ja existe
    (`customer.subscription.deleted` -> mark_subscription_canceled em
    billing.py) — nenhuma logica nova de estado nasce aqui.
    """
    import stripe

    secret_key = (getattr(settings, 'STRIPE_SECRET_KEY', '') or '').strip()
    if not secret_key:
        raise PublicWorkoutStripeNotConfiguredError('STRIPE_SECRET_KEY nao definida.')
    stripe.api_key = secret_key

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url


__all__ = [
    'PublicWorkoutStripeNotConfiguredError',
    'start_custom_price_subscription_checkout',
    'start_customer_portal_session',
    'start_subscription_checkout',
]
