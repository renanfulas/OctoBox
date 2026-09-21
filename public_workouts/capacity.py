"""Capacidade operacional do Curva expressa em minutos de trabalho."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from django.conf import settings
from django.db.models import Sum

from .models import (
    PublicWorkoutProfessional,
    PublicWorkoutProfessionalRole,
    PublicWorkoutSubscription,
    PublicWorkoutTier,
    PublicWorkoutWorkItem,
    PublicWorkoutWorkItemStatus,
    PublicWorkoutWorkItemType,
)
from .service_policy import get_tier_service_policy


@dataclass(frozen=True)
class RoleCapacity:
    role: str
    configured_minutes: int
    committed_minutes: int
    requested_minutes: int
    utilization_after: float | None
    alert_level: str
    available: bool


_TRAINING_TYPES = (
    PublicWorkoutWorkItemType.TRAINING_PROGRAM,
    PublicWorkoutWorkItemType.TRAINING_REVIEW,
)
_NUTRITION_TYPES = (
    PublicWorkoutWorkItemType.NUTRITION_PLAN,
    PublicWorkoutWorkItemType.NUTRITION_REVIEW,
)


def _alert_level(utilization: float | None) -> str:
    if utilization is None:
        return 'unconfigured'
    if utilization >= 1:
        return 'full'
    if utilization >= 0.85:
        return 'risk'
    if utilization >= 0.70:
        return 'attention'
    return 'healthy'


def capacity_mode() -> str:
    return str(getattr(settings, 'PUBLIC_WORKOUT_CAPACITY_MODE', 'observe') or 'observe').lower()


def _role_capacity(*, role: str, item_types: tuple[str, ...], requested_minutes: int) -> RoleCapacity:
    configured = PublicWorkoutProfessional.objects.filter(
        role=role, is_active=True,
    ).aggregate(total=Sum('weekly_capacity_minutes'))['total'] or 0
    committed = PublicWorkoutWorkItem.objects.filter(
        item_type__in=item_types,
        status__in=(
            PublicWorkoutWorkItemStatus.OPEN,
            PublicWorkoutWorkItemStatus.IN_PROGRESS,
            PublicWorkoutWorkItemStatus.BLOCKED,
        ),
    ).aggregate(total=Sum('estimated_effort_minutes'))['total'] or 0
    if not configured:
        return RoleCapacity(role, 0, committed, requested_minutes, None, 'unconfigured', True)
    utilization = (committed + requested_minutes) / configured
    threshold = float(getattr(settings, 'PUBLIC_WORKOUT_CAPACITY_MAX_UTILIZATION', 0.85))
    return RoleCapacity(
        role, configured, committed, requested_minutes, utilization,
        _alert_level(utilization), utilization <= threshold,
    )


def get_tier_capacity(tier: str) -> dict:
    policy = get_tier_service_policy(tier)
    roles = [
        _role_capacity(
            role=PublicWorkoutProfessionalRole.TREINO,
            item_types=_TRAINING_TYPES,
            requested_minutes=policy.training_initial_effort_minutes,
        )
    ]
    if tier in (PublicWorkoutTier.COMPLETO, PublicWorkoutTier.PREMIUM):
        roles.append(_role_capacity(
            role=PublicWorkoutProfessionalRole.NUTRICAO,
            item_types=_NUTRITION_TYPES,
            requested_minutes=policy.nutrition_initial_effort_minutes or 0,
        ))
    configured = all(role.configured_minutes > 0 for role in roles)
    raw_available = configured and all(role.available for role in roles)
    mode = capacity_mode()
    # Observe/warn medem sem interromper receita; enforce e o unico modo
    # que pode desviar o cliente para a lista de espera.
    checkout_allowed = mode != 'enforce' or raw_available
    return {
        'tier': tier,
        'mode': mode,
        'configured': configured,
        'raw_available': raw_available,
        'checkout_allowed': checkout_allowed,
        'roles': [asdict(role) for role in roles],
    }


def get_capacity_projection(*, days: int) -> dict:
    """Inclui fila atual e recorrencias Premium ainda nao materializadas."""
    if days not in (14, 28):
        raise ValueError('projecao suportada somente para 14 ou 28 dias')
    weeks = days // 7
    premium_count = PublicWorkoutSubscription.objects.filter(
        status='active', tier=PublicWorkoutTier.PREMIUM,
    ).count()
    policy = get_tier_service_policy(PublicWorkoutTier.PREMIUM)
    forecast = {
        PublicWorkoutProfessionalRole.TREINO: premium_count * weeks * (
            policy.training_review_effort_minutes or 0
        ),
        PublicWorkoutProfessionalRole.NUTRICAO: premium_count * weeks * (
            policy.nutrition_review_effort_minutes or 0
        ),
    }
    roles = {}
    for role, item_types in (
        (PublicWorkoutProfessionalRole.TREINO, _TRAINING_TYPES),
        (PublicWorkoutProfessionalRole.NUTRICAO, _NUTRITION_TYPES),
    ):
        current = _role_capacity(role=role, item_types=item_types, requested_minutes=0)
        projected = current.committed_minutes + forecast[role]
        roles[role] = {
            'configured_minutes': current.configured_minutes,
            'committed_minutes': current.committed_minutes,
            'forecast_minutes': forecast[role],
            'projected_minutes': projected,
            'utilization': projected / current.configured_minutes if current.configured_minutes else None,
            'alert_level': _alert_level(
                projected / current.configured_minutes if current.configured_minutes else None
            ),
        }
    return {'days': days, 'roles': roles}


__all__ = ['capacity_mode', 'get_capacity_projection', 'get_tier_capacity']
