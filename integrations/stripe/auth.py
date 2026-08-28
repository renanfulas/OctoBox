"""
ARQUIVO: verificação de autenticidade de webhooks da Stripe.

POR QUE ELE EXISTE:
- Isola o SDK da Stripe dentro de integrations/stripe/.
- A view chama verify_stripe_webhook() sem precisar importar stripe diretamente.

O QUE ESTE ARQUIVO FAZ:
1. Verifica a assinatura HMAC do webhook usando o secret configurado.
2. Retorna o evento parseado ou levanta StripeWebhookAuthError.
"""

import stripe
from django.conf import settings

stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
_WEBHOOK_SECRET = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')


class StripeWebhookAuthError(Exception):
    """Levantada quando payload ou assinatura são inválidos."""
    pass


def verify_stripe_webhook(raw_body: bytes, sig_header: str) -> dict:
    """
    Verifica assinatura HMAC e retorna o evento como dict.
    Levanta StripeWebhookAuthError para qualquer falha de autenticidade.

    stripe.Webhook.construct_event() devolve um StripeObject, nao um dict
    puro. Na SDK 15.x, StripeObject nao implementa mais o protocolo de
    Mapping (sem keys()/__iter__ compativel) — dict(event) estoura
    KeyError: 0 (dict() cai no fallback de iterar pares por indice
    inteiro). Usar .to_dict() (metodo oficial da SDK) em vez do
    construtor dict() built-in.
    """
    try:
        event = stripe.Webhook.construct_event(raw_body, sig_header, _WEBHOOK_SECRET)
        return event.to_dict()
    except ValueError as exc:
        raise StripeWebhookAuthError('Invalid payload') from exc
    except stripe.error.SignatureVerificationError as exc:
        raise StripeWebhookAuthError('Invalid signature') from exc


__all__ = ['StripeWebhookAuthError', 'verify_stripe_webhook']
