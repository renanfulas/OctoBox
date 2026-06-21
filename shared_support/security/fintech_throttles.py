"""
ARQUIVO: Camada de controle de tráfego financeiro (Anti-Fraude).

POR QUE ELE EXISTE:
- Prevenir ataques de exaustão e validação em massa (Card Testing).
- Bloquear atacantes antes que alcancem as instâncias do Django ou da Stripe.

O QUE ESTE ARQUIVO FAZ:
1. Limita requisições ao checkout por IP.
2. Limita requisições falsas a webhooks.

PONTOS CRITICOS:
- Se houver sobrecarga, deve retornar HTTP 429 sem consumir banco.
"""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.core.cache import cache

CHECKOUT_RATE_LIMIT_MAX = 10
CHECKOUT_RATE_LIMIT_WINDOW_SECONDS = 3600


def checkout_rate_limit_exceeded(request) -> bool:
    """Guard de card-testing para views Django (nao-DRF) que abrem checkout Stripe.

    StripeCheckoutRedirectView e PaymentLinkView sao django.views.View e NAO passam
    pelos throttles do DRF (AntiCardTesting*Throttle). Este helper aplica a mesma
    politica por IP+usuario via cache, compartilhando a mesma chave entre as duas
    views (um contador unico por operador). Retorna True quando o limite ja foi
    atingido — a view deve responder 429 sem tocar a Stripe nem o banco.
    """
    ip = request.META.get('REMOTE_ADDR')
    user_id = getattr(getattr(request, 'user', None), 'id', None)
    key = f'octo_stripe_rl_{ip}_{user_id}'
    attempts = cache.get(key, 0)
    if attempts >= CHECKOUT_RATE_LIMIT_MAX:
        return True
    cache.set(key, attempts + 1, timeout=CHECKOUT_RATE_LIMIT_WINDOW_SECONDS)
    return False


class AntiCardTestingUserThrottle(UserRateThrottle):
    """
    Limita usuários logados a iniciarem sessões de pagamento um número seguro de vezes.
    Impede que contas comprometidas testem cartões roubados.
    """
    scope = 'fintech_checkout_user'
    rate = '5/hour'

class AntiCardTestingAnonThrottle(AnonRateThrottle):
    """
    Limita IPs não logados. Protege rotas sensíveis como webhooks
    ou endpoints públicos de pagamento contra scripts automatizados.
    """
    scope = 'fintech_checkout_anon'
    rate = '10/hour'

__all__ = [
    'AntiCardTestingUserThrottle',
    'AntiCardTestingAnonThrottle',
    'checkout_rate_limit_exceeded',
]
