"""Contrato operacional por tier, versionado em codigo/settings."""

from dataclasses import dataclass

from django.conf import settings

from .models import PublicWorkoutTier


@dataclass(frozen=True)
class TierServicePolicy:
    training_initial_slo_hours: int
    nutrition_initial_slo_hours: int | None
    priority: int
    training_review_cadence_days: int | None
    nutrition_review_cadence_days: int | None
    training_initial_effort_minutes: int
    nutrition_initial_effort_minutes: int | None
    training_review_effort_minutes: int | None
    nutrition_review_effort_minutes: int | None


_DEFAULTS = {
    PublicWorkoutTier.ESSENCIAL: TierServicePolicy(72, None, 100, None, None, 45, None, None, None),
    PublicWorkoutTier.COMPLETO: TierServicePolicy(72, 96, 70, None, None, 60, 75, None, None),
    PublicWorkoutTier.PREMIUM: TierServicePolicy(48, 48, 30, 7, 7, 75, 90, 30, 30),
}


def operations_enabled() -> bool:
    return bool(getattr(settings, 'PUBLIC_WORKOUT_OPERATIONS_ENABLED', False))


def get_tier_service_policy(tier: str) -> TierServicePolicy:
    try:
        base = _DEFAULTS[tier]
    except KeyError as exc:
        raise ValueError(f'tier Curva desconhecido: {tier!r}') from exc
    prefix = f'PUBLIC_WORKOUT_{tier.upper()}_'
    return TierServicePolicy(
        training_initial_slo_hours=int(getattr(settings, prefix + 'TRAINING_SLO_HOURS', base.training_initial_slo_hours)),
        nutrition_initial_slo_hours=(
            int(getattr(settings, prefix + 'NUTRITION_SLO_HOURS', base.nutrition_initial_slo_hours))
            if base.nutrition_initial_slo_hours is not None else None
        ),
        priority=int(getattr(settings, prefix + 'PRIORITY', base.priority)),
        training_review_cadence_days=base.training_review_cadence_days,
        nutrition_review_cadence_days=base.nutrition_review_cadence_days,
        training_initial_effort_minutes=int(getattr(settings, prefix + 'TRAINING_EFFORT_MINUTES', base.training_initial_effort_minutes)),
        nutrition_initial_effort_minutes=(
            int(getattr(settings, prefix + 'NUTRITION_EFFORT_MINUTES', base.nutrition_initial_effort_minutes))
            if base.nutrition_initial_effort_minutes is not None else None
        ),
        training_review_effort_minutes=base.training_review_effort_minutes,
        nutrition_review_effort_minutes=base.nutrition_review_effort_minutes,
    )


__all__ = ['TierServicePolicy', 'get_tier_service_policy', 'operations_enabled']
