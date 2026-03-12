"""
ARQUIVO: resolucao de identidade de canal do WhatsApp.

POR QUE ELE EXISTE:
- Comeca a separar a identidade de canal da identidade do aluno sem quebrar o fluxo atual.

O QUE ESTE ARQUIVO FAZ:
1. Resolve contato de canal por id externo ou telefone normalizado.
2. Prefere vinculo explicito do contato antes do fallback legado por telefone do aluno.
3. Localiza intake pendente compativel para reconciliacao futura.

PONTOS CRITICOS:
- O fallback por telefone existe por compatibilidade e deve encolher com a evolucao do modelo.
"""

from dataclasses import dataclass

from boxcore.models import Student
from boxcore.shared.phone_numbers import normalize_phone_number
from communications.models import StudentIntake, WhatsAppContact


@dataclass(slots=True)
class WhatsAppChannelIdentity:
    normalized_phone: str
    contact: WhatsAppContact | None
    student: Student | None
    intake: StudentIntake | None


def _build_phone_candidates(phone: str) -> list[str]:
    normalized_phone = normalize_phone_number(phone)
    raw_phone = (phone or '').strip()
    return [candidate for candidate in dict.fromkeys([normalized_phone, raw_phone]) if candidate]


def resolve_whatsapp_channel_identity(*, phone: str, external_contact_id: str = '') -> WhatsAppChannelIdentity:
    phone_candidates = _build_phone_candidates(phone)
    normalized_phone = phone_candidates[0] if phone_candidates else ''
    contact_queryset = WhatsAppContact.objects.select_related('linked_student')

    contact = None
    if external_contact_id:
        contact = contact_queryset.filter(external_contact_id=external_contact_id).first()
    if contact is None and normalized_phone:
        contact = contact_queryset.filter(phone=normalized_phone).first()

    student = None
    if contact is not None and contact.linked_student_id:
        student = contact.linked_student
    elif phone_candidates:
        student = Student.objects.filter(phone__in=phone_candidates).order_by('id').first()

    intake = None
    if phone_candidates:
        intake = StudentIntake.objects.filter(
            phone__in=phone_candidates,
            linked_student__isnull=True,
        ).order_by('-created_at').first()

    return WhatsAppChannelIdentity(
        normalized_phone=normalized_phone,
        contact=contact,
        student=student,
        intake=intake,
    )
