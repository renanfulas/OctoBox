"""
ARQUIVO: politicas puras de conversao de intake.

POR QUE ELE EXISTE:
- Remove do adapter Django a prioridade de lookup do lead e a decisao de mutacao comercial da conversao.

O QUE ESTE ARQUIVO FAZ:
1. Define a prioridade entre intake explicito e fallback por telefone.
2. Define a mutacao comercial do lead convertido.
3. Centraliza a nota padrao de conversao.

PONTOS CRITICOS:
- Esta camada deve permanecer pura; ORM, lock e consultas continuam em infrastructure.
"""

from dataclasses import dataclass

from shared_support.phone_numbers import build_phone_match_candidates, normalize_phone_number


DEFAULT_INTAKE_CONVERSION_NOTE = 'Convertido em aluno definitivo pela tela leve.'


@dataclass(frozen=True, slots=True)
class IntakeLookupDecision:
    explicit_intake_id: int | None
    fallback_phone_candidates: tuple[str, ...]
    should_try_phone_fallback: bool
    normalized_student_phone: str


@dataclass(frozen=True, slots=True)
class IntakeConversionDecision:
    normalized_phone: str
    status: str
    notes: str


def append_intake_note(existing_note: str | None, extra_note: str) -> str:
    current_note = (existing_note or '').strip()
    return '\n'.join(filter(None, [current_note, extra_note]))


def build_intake_lookup_decision(*, intake_record_id: int | None, student_phone: str) -> IntakeLookupDecision:
    normalized_student_phone = normalize_phone_number(student_phone)
    fallback_phone_candidates = tuple(build_phone_match_candidates(student_phone))
    return IntakeLookupDecision(
        explicit_intake_id=intake_record_id,
        fallback_phone_candidates=fallback_phone_candidates,
        should_try_phone_fallback=intake_record_id is None and bool(fallback_phone_candidates),
        normalized_student_phone=normalized_student_phone,
    )


def build_intake_conversion_decision(*, existing_phone: str | None, existing_notes: str | None, normalized_student_phone: str) -> IntakeConversionDecision:
    target_phone = normalized_student_phone or normalize_phone_number(existing_phone)
    return IntakeConversionDecision(
        normalized_phone=target_phone,
        status='approved',
        notes=append_intake_note(existing_notes, DEFAULT_INTAKE_CONVERSION_NOTE),
    )


__all__ = [
    'DEFAULT_INTAKE_CONVERSION_NOTE',
    'IntakeConversionDecision',
    'IntakeLookupDecision',
    'append_intake_note',
    'build_intake_conversion_decision',
    'build_intake_lookup_decision',
]