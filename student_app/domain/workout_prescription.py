from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


ROUNDING_INCREMENT = Decimal('2.5')


@dataclass(frozen=True, slots=True)
class WorkoutPrescription:
    percentage: Decimal
    one_rep_max_kg: Decimal
    raw_load_kg: Decimal
    rounded_load_kg: Decimal
    observation: str


def round_to_increment(value: Decimal, increment: Decimal = ROUNDING_INCREMENT) -> Decimal:
    if increment <= 0:
        return value
    factor = (value / increment).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return (factor * increment).quantize(Decimal('0.01'))


def build_workout_prescription(*, one_rep_max_kg: Decimal, percentage: Decimal) -> WorkoutPrescription:
    ratio = (percentage / Decimal('100')).quantize(Decimal('0.0001'))
    raw_load_kg = (one_rep_max_kg * ratio).quantize(Decimal('0.01'))
    rounded_load_kg = round_to_increment(raw_load_kg)
    observation = f'{percentage.quantize(Decimal("0.01"))}% do RM com arredondamento para {ROUNDING_INCREMENT}kg.'
    return WorkoutPrescription(
        percentage=percentage,
        one_rep_max_kg=one_rep_max_kg,
        raw_load_kg=raw_load_kg,
        rounded_load_kg=rounded_load_kg,
        observation=observation,
    )
