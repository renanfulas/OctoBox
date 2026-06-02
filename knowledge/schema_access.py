"""
ARQUIVO: resolucao de schema do RAG interno no runtime multi-tenant.

POR QUE ELE EXISTE:
- `knowledge` e um app SHARED: o indice vive no schema public, indexado UMA vez (nao por
  box). No caminho normal os comandos rodam na conexao public, onde as tabelas knowledge_*
  agora existem -> a busca "bare" funciona direto, sem --schema/--box.
- ainda assim este modulo da aos comandos uma forma unica de escolher schema: respeita
  --schema/--box como escape hatch (consultar um tenant especifico) e mantem o fallback
  legado para quando `knowledge` era TENANT app e as tabelas so existiam em box_* (conexao
  public sem elas -> ProgrammingError "relation knowledge_knowledgechunk does not exist").

O QUE ESTE ARQUIVO FAZ:
1. `force_utf8_io()` — forca stdout/stderr para UTF-8 (console do Windows estoura com
   acentos no `json.dumps(ensure_ascii=False)`).
2. `knowledge_schema(...)` — context manager que entra no schema correto:
   - se ja estamos num schema de tenant com tabelas knowledge (ex.: via tenant_command), usa ele.
   - senao resolve por --schema / --box / env OCTOBOX_KNOWLEDGE_SCHEMA / auto (primeiro box com schema real).

PONTOS CRITICOS:
- o indice e conteudo do REPOSITORIO (igual para todo tenant); como knowledge e SHARED,
  ele vive no public e e lido de la por padrao.
- so cai no fallback legado (auto-resolver um box_*) quando as tabelas NAO estao na conexao
  atual; nesse caso, se nao houver schema valido, levanta erro claro (nunca silencioso).
"""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager

from django.db import connection
from django_tenants.utils import schema_context, schema_exists


class KnowledgeSchemaError(RuntimeError):
    """Levantado quando nao da para resolver um schema de tenant valido para o RAG."""


def force_utf8_io() -> None:
    """Reconfigura stdout/stderr para UTF-8 quando possivel (no-op se nao suportado)."""
    for stream_name in ('stdout', 'stderr'):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding='utf-8', errors='replace')
        except (ValueError, OSError):
            continue


def _knowledge_tables_present() -> bool:
    try:
        return 'knowledge_knowledgechunk' in connection.introspection.table_names()
    except Exception:
        return False


def _normalize_schema(schema: str | None, box: str | None) -> str | None:
    if schema:
        return schema.strip()
    if box:
        slug = box.strip()
        return slug if slug.startswith('box_') else f'box_{slug}'
    env_schema = (os.environ.get('OCTOBOX_KNOWLEDGE_SCHEMA') or '').strip()
    return env_schema or None


def _auto_pick_schema() -> str:
    """Escolhe o primeiro Box cujo schema realmente existe. Mensagem clara se nao houver."""
    try:
        from control.models import Box
    except Exception as exc:  # pragma: no cover - control sempre presente em runtime
        raise KnowledgeSchemaError(f'nao foi possivel importar control.Box: {exc}') from exc

    candidates = [box.schema_name for box in Box.objects.order_by('id') if schema_exists(box.schema_name)]
    if not candidates:
        raise KnowledgeSchemaError(
            'nenhum box provisionado com schema valido. '
            'Rode: python manage.py provision_box --slug=<slug> --owner-email=<email> '
            'e depois ingest dentro do schema.'
        )
    return candidates[0]


@contextmanager
def knowledge_schema(*, schema: str | None = None, box: str | None = None):
    """
    Garante que o bloco enxergue as tabelas do RAG. Yields o schema usado.

    Ordem de resolução:
    1. --schema/--box explícito sempre vence (entra nele).
    2. Se a conexão atual já enxerga as tabelas (knowledge é SHARED → public; ou
       estamos dentro de um tenant via `tenant_command`), usa a conexão como está.
    3. Legado: knowledge ainda como TENANT app e estamos no public sem as tabelas
       → auto-resolve o primeiro box provisionado.
    """
    requested = _normalize_schema(schema, box)
    if requested:
        if not schema_exists(requested):
            raise KnowledgeSchemaError(f'schema {requested!r} nao existe neste banco.')
        with schema_context(requested):
            yield requested
        return

    if _knowledge_tables_present():
        # Caminho normal pós-migração: tabelas no public (SHARED) ou tenant já setado.
        yield getattr(connection, 'schema_name', 'current')
        return

    # Fallback legado (knowledge ainda TENANT, conexão no public sem as tabelas).
    target = _auto_pick_schema()
    sys.stderr.write(f'[knowledge] usando schema auto-resolvido: {target}\n')
    with schema_context(target):
        yield target


__all__ = [
    'KnowledgeSchemaError',
    'force_utf8_io',
    'knowledge_schema',
]
