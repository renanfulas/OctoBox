"""
ARQUIVO: adapters Django dos use cases de communications.

POR QUE ELE EXISTE:
- Implementa os fluxos reais de WhatsApp e toque operacional usando ORM, transação e auditoria concretos.

O QUE ESTE ARQUIVO FAZ:
1. Registra mensagens inbound de WhatsApp com idempotência.
2. Registra toque operacional outbound com vínculo de contato e auditoria.
3. Mantém a camada de infraestrutura isolada da aplicação.

PONTOS CRITICOS:
- Este arquivo concentra o uso concreto de ORM e deve permanecer abaixo da camada de aplicação.
"""

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from auditing import log_audit_event
from boxcore.models import Payment, PaymentStatus, Student, Enrollment
from boxcore.shared.phone_numbers import normalize_phone_number
from communications.application.commands import RegisterInboundWhatsAppMessageCommand, RegisterOperationalMessageCommand
from communications.application.ports import InboundWhatsAppMessagePort, OperationalMessagePort
from communications.application.results import InboundWhatsAppMessageResult, OperationalMessageResult
from communications.application.use_cases import (
    execute_register_inbound_whatsapp_message_use_case,
    execute_register_operational_message_use_case,
)
from communications.models import (
    MessageDirection,
    MessageKind,
    StudentIntake,
    WhatsAppContact,
    WhatsAppContactStatus,
    WhatsAppMessageLog,
)
from integrations.whatsapp.identity import resolve_whatsapp_channel_identity
from integrations.whatsapp.payloads import sanitize_whatsapp_payload


def _build_operational_message_body(*, action_kind, student, payment=None, enrollment=None):
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


def _lock_contact(contact):
    if contact is None:
        return None
    return WhatsAppContact.objects.select_for_update().get(pk=contact.pk)


class DjangoInboundWhatsAppMessagePort(InboundWhatsAppMessagePort):
    def _get_or_create_contact(self, *, normalized_phone, display_name, external_contact_id, student, fallback_intake):
        identity = resolve_whatsapp_channel_identity(phone=normalized_phone, external_contact_id=external_contact_id)
        contact = _lock_contact(identity.contact)
        if contact is None:
            notes = ''
            if fallback_intake is not None and student is None:
                notes = 'Contato preparado para reconciliacao automatica de canal.'
            try:
                contact = WhatsAppContact.objects.create(
                    phone=normalized_phone,
                    external_contact_id=external_contact_id,
                    display_name=display_name,
                    linked_student=student,
                    status=WhatsAppContactStatus.LINKED if student is not None else WhatsAppContactStatus.NEW,
                    last_inbound_at=timezone.now(),
                    notes=notes,
                )
            except IntegrityError:
                contact = WhatsAppContact.objects.select_for_update().get(phone=normalized_phone)
        return contact

    @transaction.atomic
    def register(self, command: RegisterInboundWhatsAppMessageCommand) -> InboundWhatsAppMessageResult:
        normalized_phone = normalize_phone_number(command.phone)
        if not normalized_phone:
            return InboundWhatsAppMessageResult(accepted=False, reason='missing-phone')

        existing_message = None
        if command.external_message_id:
            existing_message = WhatsAppMessageLog.objects.filter(
                external_message_id=command.external_message_id
            ).select_related('contact').first()
        if existing_message is not None:
            return InboundWhatsAppMessageResult(
                accepted=True,
                reason='duplicate-message-id',
                contact_id=existing_message.contact_id,
                message_log_id=existing_message.id,
            )

        identity = resolve_whatsapp_channel_identity(
            phone=command.phone,
            external_contact_id=command.external_contact_id,
        )
        student = identity.student
        fallback_intake = identity.intake
        if fallback_intake is not None and fallback_intake.phone != normalized_phone:
            fallback_intake.phone = normalized_phone
            fallback_intake.save(update_fields=['phone', 'updated_at'])

        contact = self._get_or_create_contact(
            normalized_phone=normalized_phone,
            display_name=command.display_name,
            external_contact_id=command.external_contact_id,
            student=student,
            fallback_intake=fallback_intake,
        )

        update_fields = []
        if command.display_name and contact.display_name != command.display_name:
            contact.display_name = command.display_name
            update_fields.append('display_name')
        if command.external_contact_id and contact.external_contact_id != command.external_contact_id:
            contact.external_contact_id = command.external_contact_id
            update_fields.append('external_contact_id')
        if student is not None and contact.linked_student_id != student.id:
            contact.linked_student = student
            update_fields.append('linked_student')
        expected_status = WhatsAppContactStatus.LINKED if student is not None else WhatsAppContactStatus.NEW
        if contact.status != expected_status:
            contact.status = expected_status
            update_fields.append('status')
        contact.last_inbound_at = timezone.now()
        update_fields.append('last_inbound_at')
        if update_fields:
            update_fields.append('updated_at')
            contact.save(update_fields=update_fields)

        try:
            message_log = WhatsAppMessageLog.objects.create(
                contact=contact,
                direction=MessageDirection.INBOUND,
                kind=command.message_kind,
                body=command.body,
                external_message_id=command.external_message_id,
                raw_payload=sanitize_whatsapp_payload(command.raw_payload or {}),
            )
        except IntegrityError:
            if command.external_message_id:
                existing_message = WhatsAppMessageLog.objects.filter(
                    external_message_id=command.external_message_id
                ).select_related('contact').first()
                if existing_message is not None:
                    return InboundWhatsAppMessageResult(
                        accepted=True,
                        reason='duplicate-message-id',
                        contact_id=existing_message.contact_id,
                        message_log_id=existing_message.id,
                    )
            raise

        return InboundWhatsAppMessageResult(
            accepted=True,
            reason='registered',
            contact_id=contact.id,
            message_log_id=message_log.id,
        )


class DjangoOperationalMessagePort(OperationalMessagePort):
    def __init__(self):
        self.user_model = get_user_model()

    def _get_actor(self, actor_id: int | None):
        if actor_id is None:
            return None
        return self.user_model.objects.filter(pk=actor_id).first()

    def _ensure_whatsapp_contact(self, student):
        normalized_phone = normalize_phone_number(student.phone)
        identity = resolve_whatsapp_channel_identity(phone=normalized_phone)
        contact = identity.contact
        created = False
        if contact is not None:
            contact = WhatsAppContact.objects.select_for_update().get(pk=contact.pk)
        else:
            contact = WhatsAppContact.objects.create(
                phone=normalized_phone,
                display_name=student.full_name,
                linked_student=student,
                status=WhatsAppContactStatus.LINKED,
            )
            created = True

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

    @transaction.atomic
    def register(self, command: RegisterOperationalMessageCommand) -> OperationalMessageResult:
        actor = self._get_actor(command.actor_id)
        student = Student.objects.get(pk=command.student_id)
        payment = Payment.objects.filter(pk=command.payment_id, student=student).first() if command.payment_id else None
        enrollment = Enrollment.objects.filter(pk=command.enrollment_id, student=student).first() if command.enrollment_id else None

        contact, created = self._ensure_whatsapp_contact(student)
        body = _build_operational_message_body(
            action_kind=command.action_kind,
            student=student,
            payment=payment,
            enrollment=enrollment,
        )
        message = WhatsAppMessageLog.objects.create(
            contact=contact,
            direction=MessageDirection.OUTBOUND,
            kind=MessageKind.SYSTEM,
            body=body,
            delivered_at=timezone.now(),
        )
        contact.last_outbound_at = message.delivered_at
        contact.save(update_fields=['last_outbound_at', 'updated_at'])

        if payment is not None and command.action_kind == 'overdue' and payment.status == PaymentStatus.PENDING and payment.due_date < timezone.localdate():
            payment.status = PaymentStatus.OVERDUE
            payment.save(update_fields=['status', 'updated_at'])

        log_audit_event(
            actor=actor,
            action='operational_whatsapp_touch_registered',
            target=message,
            description='Contato operacional de WhatsApp registrado pela regua comercial.',
            metadata={
                'student_id': student.id,
                'payment_id': payment.id if payment else None,
                'enrollment_id': enrollment.id if enrollment else None,
                'contact_id': contact.id,
                'action_kind': command.action_kind,
                'contact_created': created,
            },
        )
        return OperationalMessageResult(
            student_id=student.id,
            contact_id=contact.id,
            message_log_id=message.id,
            action_kind=command.action_kind,
        )


def execute_register_inbound_whatsapp_message_command(command: RegisterInboundWhatsAppMessageCommand):
    return execute_register_inbound_whatsapp_message_use_case(
        command,
        inbound_port=DjangoInboundWhatsAppMessagePort(),
    )


def execute_register_operational_message_command(command: RegisterOperationalMessageCommand):
    return execute_register_operational_message_use_case(
        command,
        operational_port=DjangoOperationalMessagePort(),
    )


@transaction.atomic
def ensure_whatsapp_contact_for_student(*, student_id: int):
    student = Student.objects.get(pk=student_id)
    return DjangoOperationalMessagePort()._ensure_whatsapp_contact(student)


__all__ = [
    'ensure_whatsapp_contact_for_student',
    'execute_register_inbound_whatsapp_message_command',
    'execute_register_operational_message_command',
]
