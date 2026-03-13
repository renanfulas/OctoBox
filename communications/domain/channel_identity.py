"""
ARQUIVO: politicas puras de resolucao de identidade de canal.

POR QUE ELE EXISTE:
- Tira da integracao concreta a decisao sobre candidatos de telefone e precedencia logica da identidade de canal.

O QUE ESTE ARQUIVO FAZ:
1. Monta os candidatos de telefone a partir da entrada bruta.
2. Explicita o telefone normalizado preferencial.
3. Decide como derivar o aluno a partir do contato resolvido ou do fallback por telefone.

PONTOS CRITICOS:
- Esta camada nao conhece ORM, QuerySet nem models concretos.
"""

from dataclasses import dataclass

from shared_support.phone_numbers import normalize_phone_number


@dataclass(frozen=True, slots=True)
class ChannelIdentityLookupPlan:
    normalized_phone: str
    phone_candidates: tuple[str, ...]


def build_channel_identity_lookup_plan(*, phone: str):
    normalized_phone = normalize_phone_number(phone)
    raw_phone = (phone or '').strip()
    phone_candidates = tuple(
        candidate for candidate in dict.fromkeys([normalized_phone, raw_phone]) if candidate
    )
    return ChannelIdentityLookupPlan(
        normalized_phone=phone_candidates[0] if phone_candidates else '',
        phone_candidates=phone_candidates,
    )


def resolve_student_from_identity_sources(*, contact_linked_student=None, fallback_student=None):
    if contact_linked_student is not None:
        return contact_linked_student
    return fallback_student


__all__ = [
    'ChannelIdentityLookupPlan',
    'build_channel_identity_lookup_plan',
    'resolve_student_from_identity_sources',
]