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

from django.conf import settings

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


def start_subscription_checkout(*, subscription, success_url: str, cancel_url: str) -> str:
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

    session = stripe.checkout.Session.create(
        mode='subscription',
        payment_method_types=['card'],
        line_items=[{'price': price_id, 'quantity': 1}],
        customer_email=account.email,
        client_reference_id=str(subscription.pk),
        success_url=success_url,
        cancel_url=cancel_url,
        # metadata.product='coaching' e o discriminador (D.0 do CORDA): o
        # webhook do corredor so processa eventos com esse valor — nunca
        # resolve Box, nunca alcanca o roteador do box (S3). metadata.tier
        # e o que stripe_handlers.py cruza contra o Price ID real da
        # assinatura Stripe antes de ativar (D.3/RT3) — nunca confiar so
        # nisto pra dinheiro, mas e o ponto de partida do cross-check.
        metadata={
            'product': 'coaching',
            'public_workout_subscription_id': str(subscription.pk),
            'plan_slug': subscription.plan_slug,
            'tier': subscription.tier,
        },
        subscription_data={
            'metadata': {
                'product': 'coaching',
                'public_workout_subscription_id': str(subscription.pk),
                'plan_slug': subscription.plan_slug,
                'tier': subscription.tier,
            },
        },
        idempotency_key=f'public-workout-subscription-{subscription.pk}-{price_id[-8:]}',
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
    'start_customer_portal_session',
    'start_subscription_checkout',
]
