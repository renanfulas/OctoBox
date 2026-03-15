"""
ARQUIVO: adapter Django de auditoria do dominio de communications.

POR QUE ELE EXISTE:
- Isola a escrita concreta de auditoria para que os adapters de fluxo nao dependam diretamente de log_audit_event.

O QUE ESTE ARQUIVO FAZ:
1. Reidrata actor e message log a partir do resultado do caso de uso.
2. Registra o evento operacional de WhatsApp na trilha de auditoria.

PONTOS CRITICOS:
- Esta camada pode usar ORM e a auditoria concreta livremente, mas nao deve concentrar o fluxo principal do caso de uso.
"""

from django.contrib.auth import get_user_model

from auditing import log_audit_event
from communications.application.commands import RegisterOperationalMessageCommand
from communications.application.ports import OperationalMessageAuditPort
from communications.application.results import OperationalMessageResult
from communications.models import WhatsAppMessageLog


class DjangoOperationalMessageAuditPort(OperationalMessageAuditPort):
    def __init__(self):
        self.user_model = get_user_model()

    def _get_actor(self, actor_id: int | None):
        if actor_id is None:
            return None
        return self.user_model.objects.filter(pk=actor_id).first()

    def record_registered(self, *, command: RegisterOperationalMessageCommand, result: OperationalMessageResult) -> None:
        actor = self._get_actor(command.actor_id)
        message = WhatsAppMessageLog.objects.get(pk=result.message_log_id)
        log_audit_event(
            actor=actor,
            action='operational_whatsapp_touch_registered',
            target=message,
            description='Contato operacional de WhatsApp registrado pela regua comercial.',
            metadata={
                'student_id': result.student_id,
                'payment_id': result.payment_id,
                'enrollment_id': result.enrollment_id,
                'contact_id': result.contact_id,
                'action_kind': result.action_kind,
                'contact_created': result.contact_created,
            },
        )

    def record_blocked(self, *, command: RegisterOperationalMessageCommand, result: OperationalMessageResult) -> None:
        actor = self._get_actor(command.actor_id)
        message = WhatsAppMessageLog.objects.get(pk=result.message_log_id)
        log_audit_event(
            actor=actor,
            action='operational_whatsapp_touch_blocked',
            target=message,
            description='Tentativa repetida de contato operacional no WhatsApp bloqueada no mesmo dia.',
            metadata={
                'student_id': result.student_id,
                'payment_id': result.payment_id,
                'enrollment_id': result.enrollment_id,
                'contact_id': result.contact_id,
                'action_kind': result.action_kind,
                'contact_created': result.contact_created,
                'blocked': True,
            },
        )


__all__ = ['DjangoOperationalMessageAuditPort']