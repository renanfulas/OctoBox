"""
ARQUIVO: adapter Django de auditoria das actions do workspace operacional.

POR QUE ELE EXISTE:
- Isola a escrita concreta de auditoria para que o adapter principal do workspace nao dependa diretamente de log_audit_event.

O QUE ESTE ARQUIVO FAZ:
1. Reidrata actor e targets ORM para auditoria operacional.
2. Registra vinculo financeiro, ocorrencia tecnica e presenca.

PONTOS CRITICOS:
- Esta camada pode usar ORM e auditoria concreta livremente, mas nao deve concentrar a persistencia principal das actions.
"""

from django.contrib.auth import get_user_model

from auditing import log_audit_event
from finance.models import Payment
from operations.application.workspace_commands import (
    ApplyAttendanceActionCommand,
    CreateTechnicalBehaviorNoteCommand,
    LinkPaymentEnrollmentCommand,
)
from operations.application.workspace_ports import WorkspaceActionAuditPort
from operations.application.workspace_results import (
    AttendanceActionResult,
    LinkedPaymentEnrollmentResult,
    TechnicalBehaviorNoteResult,
)
from operations.models import Attendance, BehaviorNote


class DjangoWorkspaceActionAudit(WorkspaceActionAuditPort):
    def __init__(self):
        self.user_model = get_user_model()

    def _get_actor(self, actor_id: int | None):
        if actor_id is None:
            return None
        return self.user_model.objects.filter(pk=actor_id).first()

    def record_payment_enrollment_linked(
        self,
        *,
        command: LinkPaymentEnrollmentCommand,
        result: LinkedPaymentEnrollmentResult | None,
    ) -> None:
        if result is None:
            return
        actor = self._get_actor(command.actor_id)
        payment = Payment.objects.get(pk=result.payment_id)
        log_audit_event(
            actor=actor,
            action='payment_linked_to_active_enrollment',
            target=payment,
            description='Manager vinculou pagamento a matricula ativa.',
            metadata={'enrollment_id': result.enrollment_id},
        )

    def record_technical_behavior_note_created(
        self,
        *,
        command: CreateTechnicalBehaviorNoteCommand,
        result: TechnicalBehaviorNoteResult | None,
    ) -> None:
        if result is None:
            return
        actor = self._get_actor(command.actor_id)
        note = BehaviorNote.objects.get(pk=result.note_id)
        log_audit_event(
            actor=actor,
            action='technical_behavior_note_created',
            target=note,
            description='Coach registrou ocorrencia tecnica.',
            metadata={'student_id': command.student_id, 'category': command.category},
        )

    def record_attendance_action_applied(
        self,
        *,
        command: ApplyAttendanceActionCommand,
        result: AttendanceActionResult | None,
    ) -> None:
        if result is None:
            return
        actor = self._get_actor(command.actor_id)
        attendance = Attendance.objects.get(pk=result.attendance_id)
        log_audit_event(
            actor=actor,
            action=f'attendance_{command.action}',
            target=attendance,
            description='Coach alterou status operacional de presenca.',
            metadata={'status': result.status},
        )


__all__ = ['DjangoWorkspaceActionAudit']