"""
ARQUIVO: filtro de logging que carimba cada registro com o box ativo.

POR QUE ELE EXISTE:
- Fecha a metade aberta do isolamento da Fase 1 (matriz operacional, item
  "fronteira de logs/exports/storage por box"): os DADOS ja sao isolados por
  schema, mas os LOGS nasciam sem dono. Sem o box no registro, uma investigacao
  de incidente nao consegue separar o ruido de um box do de outro.
- E um concern transversal (corta todos os apps) -> resolvido com UM unico
  processador na malha de observabilidade, alinhado a filosofia da Signal Mesh
  (contrato unico transversal, nao `if` de box espalhado por cada logger).

O QUE ESTE ARQUIVO FAZ:
1. Injeta `record.runtime_slug = get_box_runtime_slug()` em cada LogRecord.
2. A prova de falha: nunca quebra a emissao do log (fallback para 'control').

PONTOS CRITICOS:
- O slug vem de `connection.schema_name` no momento da emissao (request/job com
  tenant resolvido) ou 'control' fora de tenant.
- Registrado no LOGGING (config/settings/base.py) no handler `console` via dotted
  path; o formatter `box_aware` consome o campo `[box=%(runtime_slug)s]`.
"""

from __future__ import annotations

import logging

from shared_support.box_runtime import DEFAULT_BOX_RUNTIME_SLUG, get_box_runtime_slug


class BoxRuntimeLogFilter(logging.Filter):
    """Carimba cada LogRecord com o slug do box ativo (campo ``runtime_slug``)."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.runtime_slug = get_box_runtime_slug()
        except Exception:  # pragma: no cover - defensivo: get_box_runtime_slug nunca levanta
            record.runtime_slug = DEFAULT_BOX_RUNTIME_SLUG
        return True


__all__ = ['BoxRuntimeLogFilter']
