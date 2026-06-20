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

    GUARDA apps.ready: acessar django.db.connection durante a inicializacao dos settings
    (antes de django.setup()) envenena o cache @cached_property de ConnectionHandler.settings
    com o backend dummy, pois DATABASES ainda nao esta disponivel no modulo de settings
    parcialmente carregado. Verificar apps.ready evita esse efeito colateral.
    """
    try:
        from django.apps import apps
        if apps.ready:
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


def box_scoped_filename(filename: str) -> str:
    """Prefixa o nome de um arquivo exportado com o slug do box ativo.

    Fecha a metade aberta do isolamento da Fase 1 (matriz operacional): os DADOS
    ja sao isolados por schema, mas o ARTEFATO de export nascia sem dono. Com o
    prefixo, o download de um box nunca se confunde com o de outro.

    Idempotente dentro do mesmo box (nao re-prefixa).
    """
    slug = get_box_runtime_slug()
    name = (filename or '').strip() or 'export'
    prefix = f'{slug}_'
    return name if name.startswith(prefix) else f'{prefix}{name}'


def box_scoped_export_dir(media_root: str) -> str:
    """Diretorio de exports isolado por box: ``<media_root>/exports/<slug>/``.

    Write (task assincrona) e read (download view) usam o MESMO helper com o slug
    do box ativo, entao um box so enxerga os proprios arquivos — isolamento por
    construcao, sem depender de checagem de ownership por arquivo.
    """
    return os.path.join(media_root, 'exports', get_box_runtime_slug())


__all__ = [
    'DEFAULT_BOX_RUNTIME_SLUG',
    'box_scoped_export_dir',
    'box_scoped_filename',
    'build_box_cache_key_prefix',
    'get_box_runtime_namespace',
    'get_box_runtime_slug',
    'normalize_box_runtime_slug',
]
