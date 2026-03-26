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

__all__ = ['AntiCardTestingUserThrottle', 'AntiCardTestingAnonThrottle']
