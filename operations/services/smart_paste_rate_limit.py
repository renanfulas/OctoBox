"""
ARQUIVO: guard de taxa de submissao do Smart Paste (organizacao de texto via parser + LLM).

POR QUE ELE EXISTE:
- cada submissao que cai no parser (action != confirm_plan/preview_projection/etc.) pode
  disparar chamada ao Haiku (wod_slug_resolver.py) quando sobra nome nao reconhecido.
- sem limite, um usuario pode bater o endpoint repetidamente colando lixo e gastar
  tokens de API a cada tentativa, mesmo com os outros guards (limite de linhas,
  teto de nomes por chamada) ja reduzindo o dano por submissao.

O QUE ESTE ARQUIVO FAZ:
1. conta submissoes por usuario numa janela de tempo via cache (mesmo padrao de
   checkout_rate_limit_exceeded em shared_support/security/fintech_throttles.py).
2. retorna True quando o limite foi atingido — a view deve recusar sem tocar o parser/LLM.

PONTOS CRITICOS:
- usa o cache default (alias 'default', particionado por schema/tenant) — diferente do
  guard de Stripe (platform_cache): aqui cada box tem sua propria cota, faz sentido
  isolar por tenant (nao existe um recurso compartilhado unico como a conta Stripe).
"""

from django.core.cache import cache

SMART_PASTE_RATE_LIMIT_MAX = 12
SMART_PASTE_RATE_LIMIT_WINDOW_SECONDS = 300


def smart_paste_rate_limit_exceeded(request) -> bool:
    """True quando o usuario ja bateu o limite de submissoes do Smart Paste na janela."""
    user_id = getattr(getattr(request, 'user', None), 'id', None)
    if not user_id:
        return False
    key = f'octo_smart_paste_rl_{user_id}'
    attempts = cache.get(key, 0)
    if attempts >= SMART_PASTE_RATE_LIMIT_MAX:
        return True
    cache.set(key, attempts + 1, timeout=SMART_PASTE_RATE_LIMIT_WINDOW_SECONDS)
    return False


__all__ = ['smart_paste_rate_limit_exceeded']
