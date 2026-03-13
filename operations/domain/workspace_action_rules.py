"""
ARQUIVO: regras puras das actions do workspace operacional.

POR QUE ELE EXISTE:
- Remove dos adapters Django as decisoes operacionais de presenca, vinculo financeiro e ocorrencia tecnica.

O QUE ESTE ARQUIVO FAZ:
1. Define a nota padrao de vinculo operacional do pagamento.
2. Valida e normaliza a criacao de ocorrencia tecnica.
3. Define a mudanca pura de status operacional de presenca.

PONTOS CRITICOS:
- Estas regras devem continuar puras para web, API e jobs reutilizarem o mesmo criterio.
"""

from dataclasses import dataclass


LINK_PAYMENT_ENROLLMENT_NOTE = 'Vinculo operacional aplicado pela area do manager.'


def build_payment_enrollment_note(existing_note: str | None) -> str:
    note = (existing_note or '').strip()
    return note or LINK_PAYMENT_ENROLLMENT_NOTE


@dataclass(frozen=True, slots=True)
class TechnicalBehaviorNoteDecision:
    description: str


def build_technical_behavior_note_decision(*, category: str, description: str, valid_categories: set[str]) -> TechnicalBehaviorNoteDecision | None:
    normalized_description = description.strip()
    if not normalized_description or category not in valid_categories:
        return None
    return TechnicalBehaviorNoteDecision(description=normalized_description)


@dataclass(frozen=True, slots=True)
class AttendanceActionDecision:
    status: str
    set_check_in_now: bool
    set_check_out_now: bool
    ensure_check_in_when_missing: bool


def build_attendance_action_decision(action: str) -> AttendanceActionDecision | None:
    decisions = {
        'check-in': AttendanceActionDecision(
            status='checked_in',
            set_check_in_now=True,
            set_check_out_now=False,
            ensure_check_in_when_missing=False,
        ),
        'check-out': AttendanceActionDecision(
            status='checked_out',
            set_check_in_now=False,
            set_check_out_now=True,
            ensure_check_in_when_missing=True,
        ),
        'absent': AttendanceActionDecision(
            status='absent',
            set_check_in_now=False,
            set_check_out_now=False,
            ensure_check_in_when_missing=False,
        ),
    }
    return decisions.get(action)


__all__ = [
    'AttendanceActionDecision',
    'LINK_PAYMENT_ENROLLMENT_NOTE',
    'TechnicalBehaviorNoteDecision',
    'build_attendance_action_decision',
    'build_payment_enrollment_note',
    'build_technical_behavior_note_decision',
]