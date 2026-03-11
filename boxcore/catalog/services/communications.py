"""
ARQUIVO: services de comunicação operacional do catálogo.

POR QUE ELE EXISTE:
- Transforma a base preparada de WhatsApp em recurso operacional útil para cobrança e retenção.

O QUE ESTE ARQUIVO FAZ:
1. Garante vínculo entre aluno e contato de WhatsApp.
2. Gera mensagens sugeridas para cobrança, atraso e reativação.
3. Registra logs de saída para trilha operacional e auditoria.

PONTOS CRITICOS:
- Registra intenção operacional, mas não dispara envio real para provedores externos.
- As mensagens precisam preservar contexto comercial sem prometer automação inexistente.
"""

from django.utils import timezone

from boxcore.auditing import log_audit_event
from boxcore.models import (
    MessageDirection,
    MessageKind,
    Payment,
    PaymentStatus,
    WhatsAppContact,
    WhatsAppContactStatus,
    WhatsAppMessageLog,
)


def ensure_whatsapp_contact(student):
    contact, created = WhatsAppContact.objects.get_or_create(
        phone=student.phone,
        defaults={
            'display_name': student.full_name,
            'linked_student': student,
            'status': WhatsAppContactStatus.LINKED,
        },
    )
    update_fields = []
    if contact.linked_student_id != student.id:
        contact.linked_student = student
        update_fields.append('linked_student')
    if contact.display_name != student.full_name:
        contact.display_name = student.full_name
        update_fields.append('display_name')
    if contact.status != WhatsAppContactStatus.LINKED:
        contact.status = WhatsAppContactStatus.LINKED
        update_fields.append('status')
    if update_fields:
        update_fields.append('updated_at')
        contact.save(update_fields=update_fields)
    return contact, created


def build_message_body(*, action_kind, student, payment=None, enrollment=None):
    first_name = student.full_name.split()[0]
    if action_kind == 'upcoming':
        return (
            f'Oi, {first_name}. Passando para lembrar que sua cobranca do box vence em '
            f'{payment.due_date:%d/%m/%Y} no valor de R$ {payment.amount}. Se precisar, respondemos por aqui.'
        )
    if action_kind == 'overdue':
        return (
            f'Oi, {first_name}. Identificamos uma cobranca em aberto do box com vencimento em '
            f'{payment.due_date:%d/%m/%Y}, no valor de R$ {payment.amount}. Se quiser regularizar ou renegociar, nos responda.'
        )
    return (
        f'Oi, {first_name}. Sentimos sua falta no box. Se fizer sentido retomar, conseguimos te ajudar '
        f'a reativar o plano {enrollment.plan.name} com a melhor configuração para voltar ao ritmo.'
    )


def register_operational_message(*, actor, action_kind, student, payment=None, enrollment=None):
    contact, created = ensure_whatsapp_contact(student)
    body = build_message_body(action_kind=action_kind, student=student, payment=payment, enrollment=enrollment)
    message = WhatsAppMessageLog.objects.create(
        contact=contact,
        direction=MessageDirection.OUTBOUND,
        kind=MessageKind.SYSTEM,
        body=body,
        delivered_at=timezone.now(),
    )
    contact.last_outbound_at = message.delivered_at
    contact.save(update_fields=['last_outbound_at', 'updated_at'])

    if payment is not None and action_kind == 'overdue' and payment.status == PaymentStatus.PENDING and payment.due_date < timezone.localdate():
        payment.status = PaymentStatus.OVERDUE
        payment.save(update_fields=['status', 'updated_at'])

    log_audit_event(
        actor=actor,
        action='operational_whatsapp_touch_registered',
        target=message,
        description='Contato operacional de WhatsApp registrado pela régua comercial.',
        metadata={
            'student_id': student.id,
            'payment_id': payment.id if payment else None,
            'enrollment_id': enrollment.id if enrollment else None,
            'contact_id': contact.id,
            'action_kind': action_kind,
            'contact_created': created,
        },
    )
    return message


def normalize_payment_status(payment):
    if payment.status == PaymentStatus.PENDING and payment.due_date < timezone.localdate():
        payment.status = PaymentStatus.OVERDUE
    return payment