"""
ARQUIVO: regras puras de escrita da grade de aulas.

POR QUE ELE EXISTE:
- Remove do adapter Django as pequenas decisoes de fluxo da criacao recorrente e da edicao rapida.

O QUE ESTE ARQUIVO FAZ:
1. Decide quando um slot recorrente deve ser criado ou pulado.
2. Monta o plano puro de execucao do lote recorrente com pendencias remanescentes.
3. Decide quando a validacao de limite operacional precisa ser aplicada.
4. Calcula o diff puro entre estado atual e estado alvo dos campos editaveis.

PONTOS CRITICOS:
- Esta camada deve continuar livre de ORM; ela trabalha apenas com primitivas e mappings.
"""

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta


CANCELED_STATUS = 'canceled'


@dataclass(frozen=True, slots=True)
class ClassGridCreateSlotDecision:
    should_create: bool
    should_skip: bool


@dataclass(frozen=True, slots=True)
class ScheduledClassGridSlot:
    scheduled_date: date
    scheduled_at: datetime


@dataclass(frozen=True, slots=True)
class ClassGridPlannedCreationSlot:
    scheduled_date: date
    scheduled_at: datetime
    pending_day: int
    pending_week: int
    pending_month: int


@dataclass(frozen=True, slots=True)
class ClassGridCreateExecutionPlan:
    slots_to_create: tuple[ClassGridPlannedCreationSlot, ...]
    skipped_slots: tuple[datetime, ...]


def build_class_grid_create_slot_decision(*, has_existing: bool, skip_existing: bool) -> ClassGridCreateSlotDecision:
    if has_existing and skip_existing:
        return ClassGridCreateSlotDecision(should_create=False, should_skip=True)
    return ClassGridCreateSlotDecision(should_create=True, should_skip=False)


def get_month_bounds(reference_date: date) -> tuple[date, date]:
    month_start = reference_date.replace(day=1)
    month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return month_start, month_end


def get_week_bounds(reference_date: date) -> tuple[date, date]:
    week_start = reference_date - timedelta(days=reference_date.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def build_class_grid_create_execution_plan(
    *,
    scheduled_slots: tuple[ScheduledClassGridSlot, ...],
    existing_scheduled_ats: frozenset[datetime],
    skip_existing: bool,
) -> ClassGridCreateExecutionPlan:
    skipped_slots: list[datetime] = []
    slots_to_create_raw: list[ScheduledClassGridSlot] = []

    for scheduled_slot in scheduled_slots:
        slot_decision = build_class_grid_create_slot_decision(
            has_existing=scheduled_slot.scheduled_at in existing_scheduled_ats,
            skip_existing=skip_existing,
        )
        if slot_decision.should_skip:
            skipped_slots.append(scheduled_slot.scheduled_at)
            continue
        if slot_decision.should_create:
            slots_to_create_raw.append(scheduled_slot)

    day_counts = Counter(slot.scheduled_date for slot in slots_to_create_raw)
    week_counts = Counter(get_week_bounds(slot.scheduled_date) for slot in slots_to_create_raw)
    month_counts = Counter(get_month_bounds(slot.scheduled_date) for slot in slots_to_create_raw)

    planned_slots: list[ClassGridPlannedCreationSlot] = []
    for scheduled_slot in slots_to_create_raw:
        week_bounds = get_week_bounds(scheduled_slot.scheduled_date)
        month_bounds = get_month_bounds(scheduled_slot.scheduled_date)
        day_counts[scheduled_slot.scheduled_date] -= 1
        week_counts[week_bounds] -= 1
        month_counts[month_bounds] -= 1
        planned_slots.append(
            ClassGridPlannedCreationSlot(
                scheduled_date=scheduled_slot.scheduled_date,
                scheduled_at=scheduled_slot.scheduled_at,
                pending_day=day_counts[scheduled_slot.scheduled_date],
                pending_week=week_counts[week_bounds],
                pending_month=month_counts[month_bounds],
            )
        )

    return ClassGridCreateExecutionPlan(
        slots_to_create=tuple(planned_slots),
        skipped_slots=tuple(skipped_slots),
    )


def should_enforce_schedule_limits_for_status(status: str) -> bool:
    return status != CANCELED_STATUS


def collect_changed_field_names(
    *,
    current_values: Mapping[str, object],
    target_values: Mapping[str, object],
) -> tuple[str, ...]:
    changed_fields: list[str] = []
    for field_name, target_value in target_values.items():
        if current_values.get(field_name) != target_value:
            changed_fields.append(field_name)
    return tuple(changed_fields)


__all__ = [
    'CANCELED_STATUS',
    'ClassGridCreateExecutionPlan',
    'ClassGridPlannedCreationSlot',
    'ClassGridCreateSlotDecision',
    'ScheduledClassGridSlot',
    'build_class_grid_create_execution_plan',
    'build_class_grid_create_slot_decision',
    'collect_changed_field_names',
    'get_month_bounds',
    'get_week_bounds',
    'should_enforce_schedule_limits_for_status',
]