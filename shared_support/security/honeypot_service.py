"""
ARQUIVO: serviço de gatilho automático para o labirinto.

POR QUE ELE EXISTE:
- Centraliza a lógica de "decisão" de quem deve ser jogado no Honeypot.
- Permite automação 24/7 sem intervenção do mestre.
"""

from django.core.cache import cache
from access.roles import ROLE_HONEYPOT

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
