"""
ARQUIVO: acesso ao alias de cache 'platform' — chaves GLOBAIS por design.

POR QUE ELE EXISTE:
- Onda 4 (docs/plans/ondas-correcao-tenancy-billing-2026-08-25.md) deu ao
  alias 'default' de CACHES um KEY_FUNCTION que particiona TODA chave pelo
  schema ativo no momento da chamada. Correto para dado de tenant; errado
  para uma entidade que e global por natureza — auth_user so existe em
  public (nao ha "auth_user do box X"), e um IP marcado ou uma cota de
  anti-fraude nao pertencem a nenhum box.
- Usar o alias 'default' para essas chaves faria o MESMO valor logico virar
  N valores diferentes, um por schema onde foi escrito/lido — quebrando em
  silencio: invalidacao de papel (trocar Group no admin nao teria efeito
  imediato se o usuario estiver logado num box diferente do admin), o
  labirinto do honeypot (um atacante marcado escaparia so trocando de box) e
  o anti-card-testing de checkout (a conta Stripe e UNICA e compartilhada
  por todos os boxes — particionar por box daria ao atacante um jeito
  trivial de resetar a cota).

O QUE ESTE ARQUIVO FAZ:
- Expoe platform_cache = caches['platform'], import unico e facil de grepar
  para toda chave que precisa ficar fora da particao por schema.

USO:
    from shared_support.platform_cache import platform_cache
    platform_cache.set(key, value, timeout=300)

CONSUMIDORES ATUAIS (Onda 4, Passo 3):
- access/roles/__init__.py (shadow role cache, octobox:user_role_slug:uid_*)
- access/signals.py (invalidacao da mesma chave)
- shared_support/security/honeypot_service.py (GLOBAL_THREAT_BIT,
  shadow role, IP honeypot)
- shared_support/security/fintech_throttles.py (checkout_rate_limit_exceeded
  e os throttles DRF AntiCardTesting*)
"""

from django.core.cache import caches

platform_cache = caches['platform']

__all__ = ['platform_cache']
