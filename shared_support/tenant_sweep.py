"""
ARQUIVO: varredura institucional de tenants para trabalho agendado.

POR QUE ELE EXISTE:
- comando agendado roda a partir do schema `public`: `manage.py` nao passa pelo
  middleware de tenant, entao `connection.schema_name` fica em `public`.
- os models de dominio sao TENANT (`boxcore` esta em `TENANT_APPS`), logo suas
  tabelas so existem nos schemas `box_*`. Uma query disparada do `public` bate
  numa tabela inexistente e levanta `ProgrammingError`.
- o padrao correto ja existia isolado em `finance/reconciliation.py` e nunca foi
  reutilizado. Este modulo promove esse padrao a corredor unico.

O QUE ESTE ARQUIVO FAZ:
1. itera os boxes ativos e executa um handler dentro do schema de cada um.
2. isola falha por box para que um tenant quebrado nao aborte a varredura.
3. devolve um resultado agregado legivel para o comando reportar.

PONTOS CRITICOS:
- todo comando agendado que toque model TENANT deve passar por aqui.
- `sweep_active_tenants` NAO propaga schema para worker externo (Celery). Se o
  handler despachar `.delay()`, o worker roda em outro processo, de novo no
  `public` — nesse caso o schema precisa viajar no payload da task.
- falha de um box e contabilizada e seguida; use `raise_on_error=True` apenas em
  teste ou depuracao.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from django_tenants.utils import schema_context

logger = logging.getLogger('octobox.jobs')


@dataclass
class TenantSweepResult:
    """Resultado agregado de uma varredura por tenants."""

    schemas_touched: int = 0
    schemas_failed: int = 0
    results: list[tuple[str, object]] = field(default_factory=list)
    failures: list[tuple[str, str]] = field(default_factory=list)

    @property
    def schemas_total(self) -> int:
        return self.schemas_touched + self.schemas_failed

    def summary_line(self) -> str:
        parts = [f'{self.schemas_touched} schema(s) processado(s)']
        if self.schemas_failed:
            failed_names = ', '.join(schema for schema, _ in self.failures)
            parts.append(f'{self.schemas_failed} com falha ({failed_names})')
        return '; '.join(parts) + '.'


def iter_active_tenant_schemas(*, only_schema: str = ''):
    """Devolve os boxes ativos elegiveis para varredura, em ordem estavel."""
    from control.models import Box

    queryset = Box.objects.filter(status=Box.Status.ACTIVE).order_by('schema_name')
    if only_schema:
        queryset = queryset.filter(schema_name=only_schema)
    return queryset


def sweep_active_tenants(handler, *, only_schema: str = '', raise_on_error: bool = False) -> TenantSweepResult:
    """Executa `handler(box)` dentro do schema de cada box ativo.

    O handler roda ja dentro de `schema_context`, entao pode consultar models
    TENANT normalmente. O valor devolvido por ele e acumulado em `results` como
    `(schema_name, valor)`.

    Uma excecao em um box e registrada em `failures` e a varredura segue para o
    proximo, porque um tenant com dado corrompido nao pode impedir o trabalho
    agendado dos demais.
    """
    sweep = TenantSweepResult()

    for box in iter_active_tenant_schemas(only_schema=only_schema):
        try:
            with schema_context(box.schema_name):
                sweep.results.append((box.schema_name, handler(box)))
            sweep.schemas_touched += 1
        except Exception as exc:  # noqa: BLE001 — varredura nao pode morrer por um box
            sweep.schemas_failed += 1
            sweep.failures.append((box.schema_name, repr(exc)))
            logger.exception(
                'tenant_sweep falhou no schema %s',
                box.schema_name,
                extra={'schema_name': box.schema_name},
            )
            if raise_on_error:
                raise

    return sweep


def add_tenant_sweep_arguments(parser) -> None:
    """Registra os argumentos padrao de varredura em um comando de management."""
    parser.add_argument(
        '--schema',
        default='',
        help='Restringe a execucao a um unico schema de box (depuracao).',
    )


def write_tenant_sweep_summary(command, sweep: TenantSweepResult) -> None:
    """Escreve o sumario da varredura no stdout do comando, com estilo coerente."""
    style = command.style.WARNING if sweep.schemas_failed else command.style.SUCCESS
    command.stdout.write(style(sweep.summary_line()))


__all__ = [
    'TenantSweepResult',
    'add_tenant_sweep_arguments',
    'iter_active_tenant_schemas',
    'sweep_active_tenants',
    'write_tenant_sweep_summary',
]
