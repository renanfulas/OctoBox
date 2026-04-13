"""
ARQUIVO: fronteira leve e canonica do runtime por box.

POR QUE ELE EXISTE:
- formaliza a identidade do runtime atual sem exigir multitenancy aberto.
- ajuda a manter cache, healthcheck e operacao falando a mesma lingua do box ativo.

PONTOS CRITICOS:
- esta camada prepara isolamento forte e barato; ela nao cria um tenant model completo.
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
