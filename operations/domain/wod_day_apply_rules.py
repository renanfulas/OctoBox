"""
ARQUIVO: regras puras de aplicação de template por dia.

POR QUE ELE EXISTE:
- isola a tomada de decisão sobre quais sessões recebem WOD e em qual modo,
  sem tocar em banco, request ou messages.

O QUE ESTE ARQUIVO FAZ:
1. define os modos de aplicação (replace_empty, overwrite).
2. avalia se uma sessão é elegível dado o modo e o estado atual do WOD.
3. retorna resultado tipado por sessão — zero efeito colateral.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ApplyMode = Literal['replace_empty', 'overwrite']


@dataclass(frozen=True, slots=True)
class SessionEligibility:
    session_id: int
    eligible: bool
    skip_reason: str


def evaluate_session_eligibility(
    *,
    session_id: int,
    has_existing_workout: bool,
    mode: ApplyMode,
) -> SessionEligibility:
    if mode == 'replace_empty':
        if has_existing_workout:
            return SessionEligibility(
                session_id=session_id,
                eligible=False,
                skip_reason='Aula já possui WOD (modo: apenas vazias).',
            )
    return SessionEligibility(session_id=session_id, eligible=True, skip_reason='')


def filter_eligible_sessions(
    *,
    sessions: list[dict],
    mode: ApplyMode,
) -> tuple[list[dict], list[SessionEligibility]]:
    """
    sessions: lista de dicts com keys session_id, has_existing_workout.
    Retorna (elegíveis, puladas).
    """
    eligible = []
    skipped = []
    for s in sessions:
        result = evaluate_session_eligibility(
            session_id=s['session_id'],
            has_existing_workout=s['has_existing_workout'],
            mode=mode,
        )
        if result.eligible:
            eligible.append(s)
        else:
            skipped.append(result)
    return eligible, skipped


__all__ = [
    'ApplyMode',
    'SessionEligibility',
    'evaluate_session_eligibility',
    'filter_eligible_sessions',
]
