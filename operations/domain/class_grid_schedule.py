"""
ARQUIVO: regras puras de planejamento recorrente da grade de aulas.

POR QUE ELE EXISTE:
- Remove do adapter Django a logica de percorrer calendario e montar slots recorrentes da agenda.

O QUE ESTE ARQUIVO FAZ:
1. Gera os dias elegiveis pela combinacao de inicio, fim e weekdays.
2. Gera os horarios sequenciais de cada dia.
3. Devolve um plano puro de slots para a infraestrutura materializar.

PONTOS CRITICOS:
- Esta camada deve permanecer pura; timezone, duplicidade, limites e ORM ficam em infrastructure.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta


@dataclass(frozen=True, slots=True)
class PlannedClassGridSlot:
    scheduled_date: date
    start_at: datetime


def _resolve_weekday_anchor(*, anchor_date: date, target_weekday: int) -> date:
    day_offset = (target_weekday - anchor_date.weekday()) % 7
    return anchor_date + timedelta(days=day_offset)


def _iter_interval_schedule_dates(
    *,
    start_date: date,
    end_date: date,
    weekdays: tuple[int, ...],
    anchor_date: date,
    interval_days: int,
) -> tuple[date, ...]:
    dates: list[date] = []
    for weekday in sorted(set(weekdays)):
        cursor = _resolve_weekday_anchor(anchor_date=anchor_date, target_weekday=weekday)
        while cursor <= end_date:
            if cursor >= start_date:
                dates.append(cursor)
            cursor += timedelta(days=interval_days)
    return tuple(sorted(dates))


def iter_schedule_dates(
    *,
    start_date: date,
    end_date: date,
    weekdays: tuple[int, ...],
    anchor_date: date | None = None,
    interval_days: int | None = None,
) -> tuple[date, ...]:
    if anchor_date is not None and interval_days:
        return _iter_interval_schedule_dates(
            start_date=start_date,
            end_date=end_date,
            weekdays=weekdays,
            anchor_date=anchor_date,
            interval_days=interval_days,
        )

    dates: list[date] = []
    cursor = start_date
    while cursor <= end_date:
        if cursor.weekday() in weekdays:
            dates.append(cursor)
        cursor += timedelta(days=1)
    return tuple(dates)


def build_class_grid_schedule_plan(
    *,
    start_date: date,
    end_date: date,
    weekdays: tuple[int, ...],
    anchor_date: date | None = None,
    interval_days: int | None = None,
    start_time: time,
    duration_minutes: int,
    sequence_count: int,
) -> tuple[PlannedClassGridSlot, ...]:
    planned_slots: list[PlannedClassGridSlot] = []
    for scheduled_date in iter_schedule_dates(
        start_date=start_date,
        end_date=end_date,
        weekdays=weekdays,
        anchor_date=anchor_date,
        interval_days=interval_days,
    ):
        for sequence_offset in range(sequence_count + 1):
            slot_start = datetime.combine(scheduled_date, start_time) + timedelta(
                minutes=duration_minutes * sequence_offset
            )
            planned_slots.append(
                PlannedClassGridSlot(
                    scheduled_date=scheduled_date,
                    start_at=slot_start,
                )
            )
    return tuple(planned_slots)


__all__ = ['PlannedClassGridSlot', 'build_class_grid_schedule_plan', 'iter_schedule_dates']
