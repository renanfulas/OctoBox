"""
ARQUIVO: helpers de cache com isolamento por tenant.

POR QUE ELE EXISTE:
- O cache Redis é compartilhado entre todos os tenants.
- Cache keys sem prefixo de tenant vazam dados entre boxes.

O QUE ESTE ARQUIVO FAZ:
- tenant_cache_key(key): adiciona prefixo octobox:<schema_name>: ao key.
- tcache_get/set/delete: wrappers que usam tenant_cache_key automaticamente.

USO:
    from control.cache import tcache_get, tcache_set
    tcache_set('student:42:home', payload, timeout=300)
    data = tcache_get('student:42:home')

MIGRAÇÃO GRADUAL:
- Sprint 3: substituir cache.get/set em apps TENANT pelos helpers tcache_*.
- Sprint 4: boundary test B3 verifica isolamento.
"""

from __future__ import annotations

from django.core.cache import cache


def tenant_cache_key(key: str) -> str:
    """
    Retorna cache key com prefixo do tenant ativo.

    Em contexto public (login, signup, webhook): prefixo = 'public'.
    Em contexto de tenant: prefixo = schema_name (ex.: 'box_001').
    """
    from django.db import connection
    schema = getattr(connection, 'schema_name', None) or 'public'
    return f'octobox:{schema}:{key}'


def tcache_get(key: str, default=None):
    """cache.get com prefixo de tenant."""
    return cache.get(tenant_cache_key(key), default)


def tcache_set(key: str, value, timeout=None):
    """cache.set com prefixo de tenant."""
    cache.set(tenant_cache_key(key), value, timeout)


def tcache_delete(key: str):
    """cache.delete com prefixo de tenant."""
    cache.delete(tenant_cache_key(key))


def tcache_get_or_set(key: str, default_fn, timeout=None):
    """cache.get_or_set com prefixo de tenant."""
    full_key = tenant_cache_key(key)
    result = cache.get(full_key)
    if result is None:
        result = default_fn()
        cache.set(full_key, result, timeout)
    return result
