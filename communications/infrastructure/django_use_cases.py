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

from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction

from communications.application.commands import RegisterInboundWhatsAppMessageCommand, RegisterOperationalMessageCommand
from communications.application.message_templates import build_operational_message_body
from communications.application.ports import ClockPort, InboundWhatsAppMessagePort, OperationalMessagePort
from communications.application.results import InboundWhatsAppMessageResult, OperationalMessageResult
from communications.application.use_cases import (
    execute_register_inbound_whatsapp_message_use_case,
    execute_register_operational_message_use_case,
)
from communications.domain import should_mark_payment_overdue
from communications.domain import (
    build_inbound_contact_notes,
    plan_inbound_contact_mutation,
    plan_outbound_contact_mutation,
    resolve_contact_status,
)
from communications.infrastructure.django_inbound_idempotency import (
    build_duplicate_inbound_result,
    calculate_webhook_fingerprint,
    create_inbound_message_with_idempotency,
    find_existing_inbound_message,
)
from communications.infrastructure.django_audit import DjangoOperationalMessageAuditPort
from communications.infrastructure.django_clock import DjangoClockPort
from communications.models import (
    MessageDirection,
    MessageKind,
    WhatsAppContact,
    WhatsAppMessageLog,
)
from finance.models import Enrollment, Payment, PaymentStatus
from integrations.whatsapp.identity import resolve_whatsapp_channel_identity
from integrations.whatsapp.payloads import sanitize_whatsapp_payload
from shared_support.phone_numbers import normalize_phone_number
from students.models import Student


def _lock_contact(contact):
    if contact is None:
        return None
    return WhatsAppContact.objects.select_for_update().get(pk=contact.pk)


class DjangoInboundWhatsAppMessagePort(InboundWhatsAppMessagePort):
    def __init__(self, *, clock: ClockPort):
        self.clock = clock

    def _get_or_create_contact(self, *, normalized_phone, display_name, external_contact_id, student, fallback_intake):
        identity = resolve_whatsapp_channel_identity(phone=normalized_phone, external_contact_id=external_contact_id)
        contact = _lock_contact(identity.contact)
        if contact is None:
            linked_student_id = getattr(student, 'id', None)
            notes = build_inbound_contact_notes(
                has_fallback_intake=fallback_intake is not None,
                linked_student_id=linked_student_id,
            )
            try:
                contact = WhatsAppContact.objects.create(
                    phone=normalized_phone,
                    external_contact_id=external_contact_id,
                    display_name=display_name,
                    linked_student=student,
                    status=resolve_contact_status(linked_student_id=linked_student_id),
                    last_inbound_at=self.clock.now(),
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

        webhook_fingerprint = calculate_webhook_fingerprint(command.raw_payload or {})
        existing_message = find_existing_inbound_message(
            external_message_id=command.external_message_id,
            webhook_fingerprint=webhook_fingerprint
        )
        if existing_message is not None:
            return build_duplicate_inbound_result(existing_message)

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

        mutation_plan = plan_inbound_contact_mutation(
            current_display_name=contact.display_name,
            current_external_contact_id=contact.external_contact_id,
            current_linked_student_id=contact.linked_student_id,
            current_status=contact.status,
            incoming_display_name=command.display_name,
            incoming_external_contact_id=command.external_contact_id,
            incoming_linked_student_id=getattr(student, 'id', None),
        )
        update_fields = list(mutation_plan.update_fields)
        contact.display_name = mutation_plan.display_name
        contact.external_contact_id = mutation_plan.external_contact_id
        contact.linked_student_id = mutation_plan.linked_student_id
        contact.status = mutation_plan.status
        contact.last_inbound_at = self.clock.now()
        update_fields.append('last_inbound_at')
        if update_fields:
            update_fields.append('updated_at')
            contact.save(update_fields=update_fields)

        message_log, duplicate_result = create_inbound_message_with_idempotency(
            external_message_id=command.external_message_id,
            webhook_fingerprint=webhook_fingerprint,
            create_message=lambda: WhatsAppMessageLog.objects.create(
                contact=contact,
                direction=MessageDirection.INBOUND,
                kind=command.message_kind,
                body=command.body,
                external_message_id=command.external_message_id,
                webhook_fingerprint=webhook_fingerprint,
                raw_payload=sanitize_whatsapp_payload(command.raw_payload or {}),
            ),
        )
        if duplicate_result is not None:
            return duplicate_result

        return InboundWhatsAppMessageResult(
            accepted=True,
            reason='registered',
            contact_id=contact.id,
            message_log_id=message_log.id,
        )


class DjangoOperationalMessagePort(OperationalMessagePort):
    def __init__(self, *, clock: ClockPort):
        self.clock = clock

    def _repeat_block_threshold(self):
        repeat_block_hours = max(0, int(getattr(settings, 'OPERATIONAL_WHATSAPP_REPEAT_BLOCK_HOURS', 24)))
        if repeat_block_hours == 0:
            return None
        return self.clock.now() - timedelta(hours=repeat_block_hours)

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
                status=resolve_contact_status(linked_student_id=student.id),
            )
            created = True

        mutation_plan = plan_outbound_contact_mutation(
            current_display_name=contact.display_name,
            current_linked_student_id=contact.linked_student_id,
            current_status=contact.status,
            student_full_name=student.full_name,
            student_id=student.id,
        )
        update_fields = list(mutation_plan.update_fields)
        contact.display_name = mutation_plan.display_name
        contact.linked_student_id = mutation_plan.linked_student_id
        contact.status = mutation_plan.status
        if update_fields:
            update_fields.append('updated_at')
            contact.save(update_fields=update_fields)
        return contact, created

    @transaction.atomic
    def register(self, command: RegisterOperationalMessageCommand) -> OperationalMessageResult:
        student = Student.objects.get(pk=command.student_id)
        payment = Payment.objects.filter(pk=command.payment_id, student=student).first() if command.payment_id else None
        enrollment = Enrollment.objects.filter(pk=command.enrollment_id, student=student).first() if command.enrollment_id else None

        contact, created = self._ensure_whatsapp_contact(student)
        body = build_operational_message_body(
            action_kind=command.action_kind,
            first_name=student.full_name.split()[0],
            payment_due_date=getattr(payment, 'due_date', None),
            payment_amount=getattr(payment, 'amount', None),
            plan_name=getattr(getattr(enrollment, 'plan', None), 'name', None),
        )
        duplicate_message = None
        repeat_block_threshold = self._repeat_block_threshold()
        if repeat_block_threshold is not None:
            duplicate_message = (
                WhatsAppMessageLog.objects.filter(
                    contact=contact,
                    direction=MessageDirection.OUTBOUND,
                    kind=MessageKind.SYSTEM,
                    delivered_at__gte=repeat_block_threshold,
                    body=body,
                )
                .order_by('-delivered_at', '-id')
                .first()
            )
        if duplicate_message is not None:
            return OperationalMessageResult(
                student_id=student.id,
                contact_id=contact.id,
                message_log_id=duplicate_message.id,
                action_kind=command.action_kind,
                payment_id=payment.id if payment else None,
                enrollment_id=enrollment.id if enrollment else None,
                contact_created=created,
                blocked=True,
            )

        message = WhatsAppMessageLog.objects.create(
            contact=contact,
            direction=MessageDirection.OUTBOUND,
            kind=MessageKind.SYSTEM,
            body=body,
            delivered_at=self.clock.now(),
            raw_payload={
                'source': 'operational-message',
                'action_kind': command.action_kind,
                'student_id': student.id,
                'payment_id': getattr(payment, 'id', None),
                'enrollment_id': getattr(enrollment, 'id', None),
            },
        )
        contact.last_outbound_at = message.delivered_at
        contact.save(update_fields=['last_outbound_at', 'updated_at'])

        if payment is not None and should_mark_payment_overdue(
            action_kind=command.action_kind,
            payment_status=payment.status,
            payment_due_date=payment.due_date,
            reference_date=self.clock.today(),
        ):
            payment.status = PaymentStatus.OVERDUE
            payment.save(update_fields=['status', 'updated_at'])

        return OperationalMessageResult(
            student_id=student.id,
            contact_id=contact.id,
            message_log_id=message.id,
            action_kind=command.action_kind,
            payment_id=payment.id if payment else None,
            enrollment_id=enrollment.id if enrollment else None,
            contact_created=created,
            blocked=False,
        )


def execute_register_inbound_whatsapp_message_command(command: RegisterInboundWhatsAppMessageCommand):
    clock = DjangoClockPort()
    return execute_register_inbound_whatsapp_message_use_case(
        command,
        inbound_port=DjangoInboundWhatsAppMessagePort(clock=clock),
    )


def execute_register_operational_message_command(command: RegisterOperationalMessageCommand):
    clock = DjangoClockPort()
    return execute_register_operational_message_use_case(
        command,
        operational_port=DjangoOperationalMessagePort(clock=clock),
        audit_port=DjangoOperationalMessageAuditPort(),
    )


@transaction.atomic
def ensure_whatsapp_contact_for_student(*, student_id: int):
    student = Student.objects.get(pk=student_id)
    return DjangoOperationalMessagePort(clock=DjangoClockPort())._ensure_whatsapp_contact(student)


__all__ = [
    'ensure_whatsapp_contact_for_student',
    'execute_register_inbound_whatsapp_message_command',
    'execute_register_operational_message_command',
]
