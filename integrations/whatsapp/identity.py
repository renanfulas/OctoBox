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
from shared_support.crypto_fields import generate_blind_index
from students.models import Student
import logging

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WhatsAppChannelIdentity:
    normalized_phone: str
    contact: WhatsAppContact | None
    student: Student | None
    intake: StudentIntake | None


def resolve_whatsapp_channel_identity(*, phone: str, external_contact_id: str = '') -> WhatsAppChannelIdentity:
    lookup_plan = build_channel_identity_lookup_plan(phone=phone)
    contact_queryset = WhatsAppContact.objects.select_related('linked_student')

    # 🚀 Coração da Identidade: Blind Index determinístico
    phone_index = generate_blind_index(phone)

    contact = None
    if external_contact_id:
        contact = contact_queryset.filter(external_contact_id=external_contact_id).first()

    if contact is None and phone_index:
        # Busca controlada para detectar ambiguidade
        contact_candidates = list(contact_queryset.filter(phone_lookup_index=phone_index)[:2])
        if len(contact_candidates) > 1:
            logger.critical(
                f"AMBIGUIDADE: Multiplos WhatsAppContact para o mesmo blind index: {phone_index}. "
                f"IDs envolvidos: {[c.id for c in contact_candidates]}"
            )
            # Nao auto-resolve por indice quando ambigulo
            contact = None
        elif contact_candidates:
            contact = contact_candidates[0]

    fallback_student = None
    if phone_index:
        # Busca controlada de Student para detectar duplicidade
        student_candidates = list(Student.objects.filter(phone_lookup_index=phone_index)[:2])
        if len(student_candidates) > 1:
            logger.critical(
                f"AMBIGUIDADE: Multiplos Student para o mesmo blind index: {phone_index}. "
                f"IDs envolvidos: {[s.id for s in student_candidates]}"
            )
            fallback_student = None
        elif student_candidates:
            fallback_student = student_candidates[0]

    student = resolve_student_from_identity_sources(
        contact_linked_student=contact.linked_student if contact is not None and contact.linked_student_id else None,
        fallback_student=fallback_student,
    )

    if contact is None and student is not None:
        # Fallback transitório de segurança: reaproveitamos vínculo manual se o índice ainda não existir (pré-backfill)
        contact = (
            contact_queryset.filter(linked_student=student)
            .order_by('-last_outbound_at', '-last_inbound_at', '-id')
            .first()
        )

    intake = None
    if phone_index:
        # Intake resolvido via Blind Index
        intake = StudentIntake.objects.filter(
            phone_lookup_index=phone_index,
            linked_student__isnull=True,
        ).order_by('-created_at').first()

    return WhatsAppChannelIdentity(
        normalized_phone=lookup_plan.normalized_phone,
        contact=contact,
        student=student,
        intake=intake,
    )
