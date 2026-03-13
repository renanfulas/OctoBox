"""
ARQUIVO: politicas puras de reconciliacao de contato do dominio de communications.

POR QUE ELE EXISTE:
- Tira do adapter Django as decisoes sobre criacao e atualizacao do estado logico de um contato de WhatsApp.

O QUE ESTE ARQUIVO FAZ:
1. Decide status esperado do contato a partir do vinculo com aluno.
2. Decide notas iniciais de reconciliacao inbound.
3. Calcula os campos que precisam ser atualizados em contatos inbound e outbound.

PONTOS CRITICOS:
- Esta camada nao conhece ORM, transacao nem models concretos.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContactMutationPlan:
    display_name: str
    external_contact_id: str
    linked_student_id: int | None
    status: str
    update_fields: tuple[str, ...]


def resolve_contact_status(*, linked_student_id: int | None):
    return 'linked' if linked_student_id is not None else 'new'


def build_inbound_contact_notes(*, has_fallback_intake: bool, linked_student_id: int | None):
    if has_fallback_intake and linked_student_id is None:
        return 'Contato preparado para reconciliacao automatica de canal.'
    return ''


def plan_inbound_contact_mutation(
    *,
    current_display_name: str,
    current_external_contact_id: str,
    current_linked_student_id: int | None,
    current_status: str,
    incoming_display_name: str,
    incoming_external_contact_id: str,
    incoming_linked_student_id: int | None,
):
    update_fields = []
    display_name = current_display_name
    external_contact_id = current_external_contact_id
    linked_student_id = current_linked_student_id
    status = current_status

    if incoming_display_name and current_display_name != incoming_display_name:
        display_name = incoming_display_name
        update_fields.append('display_name')
    if incoming_external_contact_id and current_external_contact_id != incoming_external_contact_id:
        external_contact_id = incoming_external_contact_id
        update_fields.append('external_contact_id')
    if incoming_linked_student_id is not None and current_linked_student_id != incoming_linked_student_id:
        linked_student_id = incoming_linked_student_id
        update_fields.append('linked_student')

    expected_status = resolve_contact_status(linked_student_id=linked_student_id)
    if current_status != expected_status:
        status = expected_status
        update_fields.append('status')

    return ContactMutationPlan(
        display_name=display_name,
        external_contact_id=external_contact_id,
        linked_student_id=linked_student_id,
        status=status,
        update_fields=tuple(update_fields),
    )


def plan_outbound_contact_mutation(
    *,
    current_display_name: str,
    current_linked_student_id: int | None,
    current_status: str,
    student_full_name: str,
    student_id: int,
):
    return plan_inbound_contact_mutation(
        current_display_name=current_display_name,
        current_external_contact_id='',
        current_linked_student_id=current_linked_student_id,
        current_status=current_status,
        incoming_display_name=student_full_name,
        incoming_external_contact_id='',
        incoming_linked_student_id=student_id,
    )


__all__ = [
    'ContactMutationPlan',
    'build_inbound_contact_notes',
    'plan_inbound_contact_mutation',
    'plan_outbound_contact_mutation',
    'resolve_contact_status',
]