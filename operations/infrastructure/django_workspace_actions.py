"""
ARQUIVO: adapters Django das acoes do workspace operacional.

POR QUE ELE EXISTE:
- executa escrita e auditoria concretas das rotinas de manager e coach fora do modulo historico.

O QUE ESTE ARQUIVO FAZ:
1. vincula pagamentos a matricula ativa.
2. cria ocorrencias tecnicas.
3. aplica mudancas de presenca com auditoria.

PONTOS CRITICOS:
- essas acoes alteram estado real da operacao e precisam preservar side effects e trilha de auditoria.
"""

from django.contrib.auth import get_user_model
from django.db import transaction

from operations.application.workspace_commands import (
    ApplyAttendanceActionCommand,
    CreateTechnicalBehaviorNoteCommand,
    LinkPaymentEnrollmentCommand,
)
from operations.application.workspace_ports import (
    WorkspaceActionAuditPort,
    WorkspaceClockPort,
    WorkspaceActionWriterPort,
    WorkspaceUnitOfWorkPort,
)
from operations.application.workspace_results import (
    AttendanceActionResult,
    LinkedPaymentEnrollmentResult,
    TechnicalBehaviorNoteResult,
)
from operations.application.workspace_use_cases import (
    execute_apply_attendance_action_use_case,
    execute_create_technical_behavior_note_use_case,
    execute_link_payment_enrollment_use_case,
)
from operations.domain import (
    build_attendance_action_decision,
    build_payment_enrollment_note,
    build_technical_behavior_note_decision,
)
from operations.infrastructure.django_clock import DjangoWorkspaceClockPort
from operations.infrastructure.django_workspace_audit import DjangoWorkspaceActionAudit
from operations.infrastructure.django_workspace_store import DjangoWorkspaceStore
from operations.models import BehaviorCategory


class DjangoWorkspaceAtomicUnitOfWork(WorkspaceUnitOfWorkPort):
    def run(self, operation):
        with transaction.atomic():
            return operation()


class DjangoWorkspaceActionWriter(WorkspaceActionWriterPort):
    def __init__(self, *, clock: WorkspaceClockPort, store: DjangoWorkspaceStore):
        self.clock = clock
        self.store = store

    def link_payment_enrollment(self, command: LinkPaymentEnrollmentCommand) -> LinkedPaymentEnrollmentResult | None:
        payment = self.store.get_payment_for_update(payment_id=command.payment_id)
        active_enrollment = self.store.get_active_enrollment_for_student(student=payment.student)

        if active_enrollment is None:
            return None

        self.store.save_payment_enrollment_link(
            payment=payment,
            enrollment=active_enrollment,
            note=build_payment_enrollment_note(payment.notes),
        )
        return LinkedPaymentEnrollmentResult(payment_id=payment.id, enrollment_id=active_enrollment.id)

    def create_technical_behavior_note(
        self,
        command: CreateTechnicalBehaviorNoteCommand,
    ) -> TechnicalBehaviorNoteResult | None:
        valid_categories = {choice for choice, _ in BehaviorCategory.choices}
        decision = build_technical_behavior_note_decision(
            category=command.category,
            description=command.description,
            valid_categories=valid_categories,
        )
        if decision is None:
            return None

        note_id = self.store.create_behavior_note(
            student_id=command.student_id,
            author_id=command.actor_id,
            category=command.category,
            description=decision.description,
        )
        return TechnicalBehaviorNoteResult(note_id=note_id)

    def apply_attendance_action(self, command: ApplyAttendanceActionCommand) -> AttendanceActionResult | None:
        attendance = self.store.get_attendance_for_update(attendance_id=command.attendance_id)
        decision = build_attendance_action_decision(command.action)
        if decision is None:
            return None

        now = self.clock.now()
        check_in_at = attendance.check_in_at
        check_out_at = attendance.check_out_at
        if decision.set_check_in_now:
            check_in_at = now
        if decision.set_check_out_now:
            check_out_at = now
        if decision.ensure_check_in_when_missing and check_in_at is None:
            check_in_at = now

        self.store.save_attendance_action(
            attendance=attendance,
            status=decision.status,
            check_in_at=check_in_at,
            check_out_at=check_out_at,
        )
        return AttendanceActionResult(attendance_id=attendance.id, status=decision.status)


def _build_dependencies():
    return {
        'unit_of_work': DjangoWorkspaceAtomicUnitOfWork(),
        'writer': DjangoWorkspaceActionWriter(
            clock=DjangoWorkspaceClockPort(),
            store=DjangoWorkspaceStore(),
        ),
        'audit': DjangoWorkspaceActionAudit(),
    }


def execute_link_payment_enrollment_command(command: LinkPaymentEnrollmentCommand):
    return execute_link_payment_enrollment_use_case(command, **_build_dependencies())


def execute_create_technical_behavior_note_command(command: CreateTechnicalBehaviorNoteCommand):
    return execute_create_technical_behavior_note_use_case(command, **_build_dependencies())


def execute_apply_attendance_action_command(command: ApplyAttendanceActionCommand):
    return execute_apply_attendance_action_use_case(command, **_build_dependencies())


__all__ = [
    'execute_apply_attendance_action_command',
    'execute_create_technical_behavior_note_command',
    'execute_link_payment_enrollment_command',
]