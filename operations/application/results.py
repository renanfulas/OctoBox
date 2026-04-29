"""
ARQUIVO: resultados estaveis da grade de aulas.

POR QUE ELE EXISTE:
- devolve saidas pequenas e previsiveis para as fachadas historicas e para a camada HTTP.

O QUE ESTE ARQUIVO FAZ:
1. representa a criacao recorrente da agenda.
2. representa a edicao e a exclusao de uma aula.

PONTOS CRITICOS:
- esses resultados nao devem carregar models ORM acoplados.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ClassScheduleCreateResult:
    created_session_ids: tuple[int, ...]
    skipped_slots: tuple[datetime, ...]


@dataclass(frozen=True, slots=True)
class ClassScheduleResetResult:
    deleted_session_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class UpdatedClassSessionRecord:
    id: int
    title: str


@dataclass(frozen=True, slots=True)
class DeletedClassSessionRecord:
    id: int
    title: str
    scheduled_at: datetime
    status: str


__all__ = ['ClassScheduleCreateResult', 'ClassScheduleResetResult', 'DeletedClassSessionRecord', 'UpdatedClassSessionRecord']
