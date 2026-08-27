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

import hashlib

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.core.cache import cache
from django.db import connection

from shared_support.platform_cache import platform_cache

CHECKOUT_RATE_LIMIT_MAX = 10
CHECKOUT_RATE_LIMIT_WINDOW_SECONDS = 3600

# Janela curta do guard de duplo-submit do create-payment: pega o double-click /
# re-POST sem bloquear cobrancas legitimamente repetidas minutos depois.
CREATE_PAYMENT_IDEMPOTENCY_WINDOW_SECONDS = 15


def checkout_rate_limit_exceeded(request) -> bool:
    """Guard de card-testing para views Django (nao-DRF) que abrem checkout Stripe.

    StripeCheckoutRedirectView e PaymentLinkView sao django.views.View e NAO passam
    pelos throttles do DRF (AntiCardTesting*Throttle). Este helper aplica a mesma
    politica por IP+usuario via cache, compartilhando a mesma chave entre as duas
    views (um contador unico por operador). Retorna True quando o limite ja foi
    atingido — a view deve responder 429 sem tocar a Stripe nem o banco.

    Onda 4, Passo 3 (2026-08-26): usa platform_cache (alias 'platform', sem
    KEY_FUNCTION) de proposito — a conta Stripe e UNICA, compartilhada por
    todos os boxes. Particionar por schema (alias 'default') daria a um
    atacante de card-testing um jeito trivial de resetar a cota: bastaria
    trocar de box na URL do checkout.
    """
    ip = request.META.get('REMOTE_ADDR')
    user_id = getattr(getattr(request, 'user', None), 'id', None)
    key = f'octo_stripe_rl_{ip}_{user_id}'
    attempts = platform_cache.get(key, 0)
    if attempts >= CHECKOUT_RATE_LIMIT_MAX:
        return True
    platform_cache.set(key, attempts + 1, timeout=CHECKOUT_RATE_LIMIT_WINDOW_SECONDS)
    return False


def _create_payment_idempotency_key(request, student, cleaned_data) -> str:
    schema = getattr(connection, 'schema_name', '') or ''
    user_id = getattr(getattr(request, 'user', None), 'id', None)
    raw = '|'.join(str(part) for part in (
        schema,
        getattr(student, 'id', None),
        user_id,
        cleaned_data.get('amount'),
        cleaned_data.get('due_date'),
    ))
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()[:32]
    return f'octo_create_pay_idem_{digest}'


def claim_create_payment_idempotency(request, student, cleaned_data) -> str | None:
    """Reserva (atomicamente) a criacao de uma cobranca avulsa para evitar
    duplo-submit. Retorna a chave reservada se for um submit fresco, ou None se
    for uma duplicata na janela curta. cache.add e atomico: so o primeiro vence.

    Em caso de falha posterior na criacao, chame release_create_payment_idempotency
    para liberar a chave e permitir retry imediato.
    """
    key = _create_payment_idempotency_key(request, student, cleaned_data)
    claimed = cache.add(key, True, timeout=CREATE_PAYMENT_IDEMPOTENCY_WINDOW_SECONDS)
    return key if claimed else None


def release_create_payment_idempotency(key: str) -> None:
    """Libera a reserva (usar quando a criacao falhou, para permitir retry)."""
    if key:
        cache.delete(key)


class AntiCardTestingUserThrottle(UserRateThrottle):
    """
    Limita usuários logados a iniciarem sessões de pagamento um número seguro de vezes.
    Impede que contas comprometidas testem cartões roubados.

    Onda 4, Passo 3 (2026-08-26): `cache` sobrescrito para o alias 'platform'
    (mesmo motivo de checkout_rate_limit_exceeded acima — conta Stripe unica
    e compartilhada, nao deve particionar por box).
    """
    scope = 'fintech_checkout_user'
    rate = '5/hour'
    cache = platform_cache

class AntiCardTestingAnonThrottle(AnonRateThrottle):
    """
    Limita IPs não logados. Protege rotas sensíveis como webhooks
    ou endpoints públicos de pagamento contra scripts automatizados.

    Onda 4, Passo 3: mesmo motivo do throttle acima — `cache` no alias
    'platform', nao particionado por schema.
    """
    scope = 'fintech_checkout_anon'
    rate = '10/hour'
    cache = platform_cache

__all__ = [
    'AntiCardTestingUserThrottle',
    'AntiCardTestingAnonThrottle',
    'checkout_rate_limit_exceeded',
    'claim_create_payment_idempotency',
    'release_create_payment_idempotency',
]
