"""
ARQUIVO: adaptador de compatibilidade dos fluxos operacionais de communications.

POR QUE ELE EXISTE:
- Mantem a interface publica atual enquanto o fluxo real saiu para facade, command e use case.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta helpers legados de forma compativel.
2. Encaminha chamadas para a facade publica do dominio.
3. Concentra apenas adaptacao leve de entrada e retorno.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar ORM, auditoria, transacao ou regra central.
- Qualquer logica nova deve preferir facade, application ou domain.
"""

from django.utils import timezone

from communications.application.message_templates import build_operational_message_body
from communications.domain import should_mark_payment_overdue
from communications.facade import ensure_student_whatsapp_contact, run_register_operational_message
from communications.models import WhatsAppContact
from communications.models import WhatsAppMessageLog
from finance.models import PaymentStatus


def _resolve_student_id(student):
    return getattr(student, 'id', None)


def _resolve_optional_id(instance):
    return getattr(instance, 'id', None)


def _resolve_first_name(student):
    full_name = (getattr(student, 'full_name', '') or '').strip()
    if not full_name:
        return 'aluno'
    return full_name.split()[0]


def _resolve_plan_name(enrollment):
    return getattr(getattr(enrollment, 'plan', None), 'name', None)


def ensure_whatsapp_contact(student):
    result = ensure_student_whatsapp_contact(student_id=_resolve_student_id(student))
    return WhatsAppContact.objects.get(pk=result.contact_id)


def build_message_body(*, action_kind, student, payment=None, enrollment=None):
    return build_operational_message_body(
        action_kind=action_kind,
        first_name=_resolve_first_name(student),
        payment_due_date=getattr(payment, 'due_date', None),
        payment_amount=getattr(payment, 'amount', None),
        plan_name=_resolve_plan_name(enrollment),
    )


def register_operational_message(*, actor, action_kind, student, payment=None, enrollment=None):
    result = run_register_operational_message(
        actor_id=getattr(actor, 'id', None),
        action_kind=action_kind,
        student_id=_resolve_student_id(student),
        payment_id=_resolve_optional_id(payment),
        enrollment_id=_resolve_optional_id(enrollment),
    )
    # Preserve the historical return contract while the facade remains the
    # official behavioral entrypoint.
    return WhatsAppMessageLog.objects.get(pk=result.message_log_id)


def normalize_payment_status(payment, *, reference_date=None):
    if should_mark_payment_overdue(
        action_kind='overdue',
        payment_status=payment.status,
        payment_due_date=payment.due_date,
        reference_date=reference_date or timezone.localdate(),
    ):
        payment.status = PaymentStatus.OVERDUE
    return payment


__all__ = [
    'build_message_body',
    'ensure_whatsapp_contact',
    'normalize_payment_status',
    'register_operational_message',
]
