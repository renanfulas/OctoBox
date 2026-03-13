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

from communications.domain import build_channel_identity_lookup_plan, resolve_student_from_identity_sources
from communications.models import StudentIntake, WhatsAppContact
from students.models import Student


@dataclass(slots=True)
class WhatsAppChannelIdentity:
    normalized_phone: str
    contact: WhatsAppContact | None
    student: Student | None
    intake: StudentIntake | None


def resolve_whatsapp_channel_identity(*, phone: str, external_contact_id: str = '') -> WhatsAppChannelIdentity:
    lookup_plan = build_channel_identity_lookup_plan(phone=phone)
    contact_queryset = WhatsAppContact.objects.select_related('linked_student')

    contact = None
    if external_contact_id:
        contact = contact_queryset.filter(external_contact_id=external_contact_id).first()
    if contact is None and lookup_plan.normalized_phone:
        contact = contact_queryset.filter(phone=lookup_plan.normalized_phone).first()

    fallback_student = None
    if lookup_plan.phone_candidates:
        fallback_student = Student.objects.filter(phone__in=lookup_plan.phone_candidates).order_by('id').first()
    student = resolve_student_from_identity_sources(
        contact_linked_student=contact.linked_student if contact is not None and contact.linked_student_id else None,
        fallback_student=fallback_student,
    )

    intake = None
    if lookup_plan.phone_candidates:
        intake = StudentIntake.objects.filter(
            phone__in=lookup_plan.phone_candidates,
            linked_student__isnull=True,
        ).order_by('-created_at').first()

    return WhatsAppChannelIdentity(
        normalized_phone=lookup_plan.normalized_phone,
        contact=contact,
        student=student,
        intake=intake,
    )
