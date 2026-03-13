"""
ARQUIVO: facade publica da grade de aulas.

POR QUE ELE EXISTE:
- cria um ponto de entrada estavel para a grade sem expor commands, use cases e wiring interno a views e services antigos.

O QUE ESTE ARQUIVO FAZ:
1. monta commands da grade a partir dos payloads validados.
2. chama os entrypoints concretos da aplicacao.
3. devolve resultados pequenos e previsiveis para a borda externa.

PONTOS CRITICOS:
- esta camada organiza entrada e saida; nao deve reimplementar regra de negocio.
"""

from dataclasses import dataclass, field

from operations.application import class_grid_messages as grid_messages
from operations.application.commands import (
    build_class_schedule_create_command,
    build_class_session_delete_command,
    build_class_session_update_command,
)
from operations.infrastructure import (
    execute_create_class_schedule_command,
    execute_delete_class_session_command,
    execute_update_class_session_command,
)
from operations.models import ClassSession


@dataclass(frozen=True)
class ClassGridCommandResult:
    message: str
    payload: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ClassGridPlannerResult:
    created_sessions: list
    skipped_slots: list


def run_class_schedule_create(*, actor, form) -> ClassGridPlannerResult:
    command = build_class_schedule_create_command(
        actor_id=getattr(actor, 'id', None),
        cleaned_data=form.cleaned_data,
    )
    result = execute_create_class_schedule_command(command)
    created_sessions = list(ClassSession.objects.filter(pk__in=result.created_session_ids))
    return ClassGridPlannerResult(
        created_sessions=created_sessions,
        skipped_slots=list(result.skipped_slots),
    )


def run_class_session_update(*, actor, session, form) -> ClassGridCommandResult:
    command = build_class_session_update_command(
        actor_id=getattr(actor, 'id', None),
        session_id=session.id,
        cleaned_data=form.cleaned_data,
    )
    result = execute_update_class_session_command(command)
    updated_session = ClassSession.objects.get(pk=result.id)
    return ClassGridCommandResult(
        message=grid_messages.session_updated_success(result.title),
        payload={'session': updated_session},
    )


def run_class_session_delete(*, actor, session) -> ClassGridCommandResult:
    command = build_class_session_delete_command(
        actor_id=getattr(actor, 'id', None),
        session_id=session.id,
    )
    result = execute_delete_class_session_command(command)
    session_snapshot = {
        'id': result.id,
        'title': result.title,
        'scheduled_at': result.scheduled_at.isoformat(),
        'status': result.status,
    }
    return ClassGridCommandResult(
        message=grid_messages.session_deleted_success(result.title),
        payload=session_snapshot,
    )


__all__ = [
    'ClassGridCommandResult',
    'ClassGridPlannerResult',
    'run_class_schedule_create',
    'run_class_session_delete',
    'run_class_session_update',
]