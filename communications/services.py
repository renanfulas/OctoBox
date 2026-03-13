"""
ARQUIVO: fachada dos fluxos operacionais de communications.

POR QUE ELE EXISTE:
- Mantem a interface publica atual enquanto o fluxo real saiu para command, use case e adapter Django.

O QUE ESTE ARQUIVO FAZ:
1. Traduz o toque operacional para um command explicito.
2. Chama o use case concreto do dominio.
3. Reexporta helpers legados de forma compativel.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar ORM, auditoria, transacao ou dependencia direta de tempo do framework.
"""

from django.utils import timezone

from communications.application.message_templates import build_operational_message_body
from communications.domain import should_mark_payment_overdue
from communications.facade import ensure_student_whatsapp_contact, run_register_operational_message
from communications.models import WhatsAppContact
from communications.models import WhatsAppMessageLog
from finance.models import PaymentStatus


def ensure_whatsapp_contact(student):
    result = ensure_student_whatsapp_contact(student_id=student.id)
    return WhatsAppContact.objects.get(pk=result.contact_id)


def build_message_body(*, action_kind, student, payment=None, enrollment=None):
    return build_operational_message_body(
        action_kind=action_kind,
        first_name=student.full_name.split()[0],
        payment_due_date=getattr(payment, 'due_date', None),
        payment_amount=getattr(payment, 'amount', None),
        plan_name=getattr(getattr(enrollment, 'plan', None), 'name', None),
    )


def register_operational_message(*, actor, action_kind, student, payment=None, enrollment=None):
    result = run_register_operational_message(
        actor_id=getattr(actor, 'id', None),
        action_kind=action_kind,
        student_id=student.id,
        payment_id=getattr(payment, 'id', None),
        enrollment_id=getattr(enrollment, 'id', None),
    )
    return WhatsAppMessageLog.objects.get(pk=result.message_log_id)


def normalize_payment_status(payment):
    if should_mark_payment_overdue(
        action_kind='overdue',
        payment_status=payment.status,
        payment_due_date=payment.due_date,
        reference_date=timezone.localdate(),
    ):
        payment.status = PaymentStatus.OVERDUE
    return payment
