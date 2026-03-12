"""
ARQUIVO: commands explicitos dos workflows leves de plano.

POR QUE ELE EXISTE:
- Evita depender de cleaned_data solto e de ModelForm como contrato do fluxo comercial.

O QUE ESTE ARQUIVO FAZ:
1. Define o command de criacao e edicao leve de plano.
2. Traduz dados validados da UI para um contrato estavel.

PONTOS CRITICOS:
- O command precisa continuar pequeno e independente do framework.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class MembershipPlanCommand:
    actor_id: int | None
    name: str
    price: Decimal
    billing_cycle: str
    sessions_per_week: int | None
    description: str
    active: bool
    plan_id: int | None = None
    changed_fields: tuple[str, ...] = ()


def build_membership_plan_command(
    *,
    actor_id: int | None,
    cleaned_data: dict[str, Any],
    plan_id: int | None = None,
    changed_fields: tuple[str, ...] = (),
) -> MembershipPlanCommand:
    return MembershipPlanCommand(
        actor_id=actor_id,
        plan_id=plan_id,
        name=cleaned_data.get('name') or '',
        price=cleaned_data.get('price'),
        billing_cycle=cleaned_data.get('billing_cycle') or '',
        sessions_per_week=cleaned_data.get('sessions_per_week'),
        description=cleaned_data.get('description') or '',
        active=bool(cleaned_data.get('active')),
        changed_fields=changed_fields,
    )


__all__ = ['MembershipPlanCommand', 'build_membership_plan_command']