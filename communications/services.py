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

from communications.application.message_templates import build_operational_message_body
from communications.application.commands import RegisterOperationalMessageCommand
from communications.domain import should_mark_payment_overdue
from communications.infrastructure import DjangoClockPort, ensure_whatsapp_contact_for_student, execute_register_operational_message_command
from communications.models import WhatsAppMessageLog
from finance.models import PaymentStatus


_clock = DjangoClockPort()


def ensure_whatsapp_contact(student):
    return ensure_whatsapp_contact_for_student(student_id=student.id)


def build_message_body(*, action_kind, student, payment=None, enrollment=None):
    return build_operational_message_body(
        action_kind=action_kind,
        first_name=student.full_name.split()[0],
        payment_due_date=getattr(payment, 'due_date', None),
        payment_amount=getattr(payment, 'amount', None),
        plan_name=getattr(getattr(enrollment, 'plan', None), 'name', None),
    )


def register_operational_message(*, actor, action_kind, student, payment=None, enrollment=None):
    command = RegisterOperationalMessageCommand(
        actor_id=getattr(actor, 'id', None),
        action_kind=action_kind,
        student_id=student.id,
        payment_id=getattr(payment, 'id', None),
        enrollment_id=getattr(enrollment, 'id', None),
    )
    result = execute_register_operational_message_command(command)
    return WhatsAppMessageLog.objects.get(pk=result.message_log_id)


def normalize_payment_status(payment):
    if should_mark_payment_overdue(
        action_kind='overdue',
        payment_status=payment.status,
        payment_due_date=payment.due_date,
        reference_date=_clock.today(),
    ):
        payment.status = PaymentStatus.OVERDUE
    return payment
