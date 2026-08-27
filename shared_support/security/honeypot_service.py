"""
ARQUIVO: serviço de gatilho automático para o labirinto.

POR QUE ELE EXISTE:
- Centraliza a lógica de "decisão" de quem deve ser jogado no Honeypot.
- Permite automação 24/7 sem intervenção do mestre.

Onda 4, Passo 3 (2026-08-26): todas as chaves daqui são globais por design
(GLOBAL_THREAT_BIT é platform-wide; SHADOW_ROLE_CACHE_PREFIX é indexado por
user_id, que só existe em public; IP_HONEYPOT_CACHE_PREFIX marca um IP
independente de qual box ele está tentando acessar). Usam o alias
'platform' de CACHES — nunca o 'default' (particionado por schema desde a
Onda 4), senão um atacante marcado escaparia do labirinto trocando de box.
"""

from access.roles import ROLE_HONEYPOT
from shared_support.platform_cache import platform_cache as cache

SHADOW_ROLE_CACHE_PREFIX = "octobox:user_role_slug:uid_"
IP_HONEYPOT_CACHE_PREFIX = "octobox:ip_honeypot:addr_"
GLOBAL_THREAT_BIT = "octobox:honeypot:active_threats"

def trigger_honeypot_for_user(user_id):
    """
    Simplesmente sobrescreve o cache de papel do usuário para ROLE_HONEYPOT por 24 horas.
    O sistema AAA vai parar de ler o cargo real e ele entrará no labirinto no próximo clique.
    """
    cache.set(GLOBAL_THREAT_BIT, True, timeout=86400)
    cache_key = f"{SHADOW_ROLE_CACHE_PREFIX}{user_id}"
    cache.set(cache_key, ROLE_HONEYPOT, timeout=86400)

def trigger_honeypot_for_ip(ip_address):
    """
    Marca um IP específico para cair no Honeypot, mesmo deslogado.
    """
    cache.set(GLOBAL_THREAT_BIT, True, timeout=86400)
    cache_key = f"{IP_HONEYPOT_CACHE_PREFIX}{ip_address}"
    cache.set(cache_key, True, timeout=86400)

def is_honeypot_active_globally():
    """
    Retorna True se houver pelo menos um invasor sendo processado.
    Permite o 'Sleep Mode' dos middlewares.
    """
    return cache.get(GLOBAL_THREAT_BIT, False)

def is_ip_honeypotted(ip_address):
    cache_key = f"{IP_HONEYPOT_CACHE_PREFIX}{ip_address}"
    return cache.get(cache_key, False)
