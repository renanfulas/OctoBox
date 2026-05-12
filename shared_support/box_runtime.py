"""
ARQUIVO: fronteira leve e canonica do runtime por box.

POR QUE ELE EXISTE:
- formaliza a identidade do runtime atual sem exigir multitenancy aberto.
- ajuda a manter cache, healthcheck e operacao falando a mesma lingua do box ativo.

PONTOS CRITICOS:
- Sprint 4: get_box_runtime_slug() agora usa connection.schema_name como slug canonico
  quando um tenant esta ativo. Fallback para env var apenas em modo control (sem tenant).
- o slug precisa ser estavel por box para evitar mistura de cache entre runtimes.
"""

from __future__ import annotations

import os
import re


DEFAULT_BOX_RUNTIME_SLUG = 'control'


def normalize_box_runtime_slug(value: str | None) -> str:
    normalized = re.sub(r'[^a-z0-9]+', '-', (value or '').strip().lower()).strip('-')
    return normalized or DEFAULT_BOX_RUNTIME_SLUG


def get_box_runtime_slug() -> str:
    """Sprint 4: usa connection.schema_name como slug canonico quando tenant ativo.

    Quando django-tenants seta connection.schema_name para um schema de tenant
    (ex.: 'box_endorfina'), esse valor e o identificador canonico — nao o BOX_RUNTIME_SLUG
    do env (que seria o mesmo para todos os tenants na mesma instancia).

    Fallback para env var apenas quando schema_name == 'public' ou nao ha tenant ativo
    (ex.: management commands, jobs globais, modo control-plane).
    """
    try:
        from django.db import connection
        schema = getattr(connection, 'schema_name', None)
        if schema and schema not in ('public', DEFAULT_BOX_RUNTIME_SLUG):
            return schema  # tenant ativo — schema_name e o slug canonico
    except Exception:
        pass
    return normalize_box_runtime_slug(
        os.getenv('BOX_RUNTIME_SLUG')
        or os.getenv('RENDER_SERVICE_NAME')
        or os.getenv('RAILWAY_SERVICE_NAME')
        or DEFAULT_BOX_RUNTIME_SLUG
    )


def build_box_cache_key_prefix(base_prefix: str = 'octobox') -> str:
    normalized_base = (base_prefix or 'octobox').strip().strip(':') or 'octobox'
    return f'{normalized_base}:{get_box_runtime_slug()}'


def get_box_runtime_namespace(base_prefix: str = 'octobox') -> str:
    return build_box_cache_key_prefix(base_prefix)


__all__ = [
    'DEFAULT_BOX_RUNTIME_SLUG',
    'build_box_cache_key_prefix',
    'get_box_runtime_namespace',
    'get_box_runtime_slug',
    'normalize_box_runtime_slug',
]
