"""
ARQUIVO: commands explicitos da grade de aulas.

POR QUE ELE EXISTE:
- evita que a orquestracao operacional dependa diretamente de form.cleaned_data ou de models Django.

O QUE ESTE ARQUIVO FAZ:
1. define os commands de criacao recorrente, edicao rapida e exclusao.
2. traduz dados validados da UI para contratos pequenos e estaveis.

PONTOS CRITICOS:
- qualquer campo novo da grade precisa entrar aqui para o contrato continuar explicito.
"""

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any


@dataclass(frozen=True, slots=True)
class ClassScheduleCreateCommand:
    actor_id: int | None
    title: str
    coach_id: int | None
    start_date: date
    end_date: date
    anchor_date: date | None
    interval_days: int | None
    weekdays: tuple[int, ...]
    start_time: time
    sequence_count: int
    duration_minutes: int
    capacity: int
    status: str
    notes: str
    skip_existing: bool


@dataclass(frozen=True, slots=True)
class ClassSessionUpdateCommand:
    actor_id: int | None
    session_id: int
    title: str
    coach_id: int | None
    scheduled_at: datetime
    duration_minutes: int
    capacity: int
    status: str
    notes: str


@dataclass(frozen=True, slots=True)
class ClassSessionDeleteCommand:
    actor_id: int | None
    session_id: int


@dataclass(frozen=True, slots=True)
class ClassScheduleResetCommand:
    actor_id: int | None


def build_class_schedule_create_command(*, actor_id: int | None, cleaned_data: dict[str, Any]) -> ClassScheduleCreateCommand:
    coach = cleaned_data.get('coach')
    weekdays = tuple(sorted(cleaned_data.get('weekdays') or ()))
    return ClassScheduleCreateCommand(
        actor_id=actor_id,
        title=cleaned_data.get('title') or '',
        coach_id=getattr(coach, 'id', None),
        start_date=cleaned_data.get('start_date'),
        end_date=cleaned_data.get('end_date'),
        anchor_date=cleaned_data.get('anchor_date'),
        interval_days=cleaned_data.get('interval_days'),
        weekdays=weekdays,
        start_time=cleaned_data.get('start_time'),
        sequence_count=cleaned_data.get('sequence_count') or 0,
        duration_minutes=cleaned_data.get('duration_minutes'),
        capacity=cleaned_data.get('capacity'),
        status=cleaned_data.get('status') or '',
        notes=cleaned_data.get('notes') or '',
        skip_existing=bool(cleaned_data.get('skip_existing')),
    )


def build_class_session_update_command(
    *,
    actor_id: int | None,
    session_id: int,
    cleaned_data: dict[str, Any],
) -> ClassSessionUpdateCommand:
    coach = cleaned_data.get('coach')
    return ClassSessionUpdateCommand(
        actor_id=actor_id,
        session_id=session_id,
        title=cleaned_data.get('title') or '',
        coach_id=getattr(coach, 'id', None),
        scheduled_at=cleaned_data.get('scheduled_at'),
        duration_minutes=cleaned_data.get('duration_minutes'),
        capacity=cleaned_data.get('capacity'),
        status=cleaned_data.get('status') or '',
        notes=cleaned_data.get('notes') or '',
    )


def build_class_session_delete_command(*, actor_id: int | None, session_id: int) -> ClassSessionDeleteCommand:
    return ClassSessionDeleteCommand(actor_id=actor_id, session_id=session_id)


def build_class_schedule_reset_command(*, actor_id: int | None) -> ClassScheduleResetCommand:
    return ClassScheduleResetCommand(actor_id=actor_id)


__all__ = [
    'ClassScheduleCreateCommand',
    'ClassScheduleResetCommand',
    'ClassSessionDeleteCommand',
    'ClassSessionUpdateCommand',
    'build_class_schedule_create_command',
    'build_class_schedule_reset_command',
    'build_class_session_delete_command',
    'build_class_session_update_command',
]
