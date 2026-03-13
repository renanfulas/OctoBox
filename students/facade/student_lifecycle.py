"""
ARQUIVO: facade publica do lifecycle comercial do aluno.

POR QUE ELE EXISTE:
- cria um ponto de entrada estavel para cadastro rapido, intake, matricula e cobrancas sem expor commands e adapters concretos ao catalogo.

O QUE ESTE ARQUIVO FAZ:
1. monta commands pequenos do lifecycle do aluno.
2. chama os entrypoints concretos da aplicacao de students.
3. devolve resultados pequenos e previsiveis para a borda externa.

PONTOS CRITICOS:
- esta camada organiza entrada e saida; nao deve duplicar regra de negocio.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from students.application.commands import (
    StudentEnrollmentActionCommand,
    StudentEnrollmentSyncCommand,
    StudentIntakeSyncCommand,
    StudentPaymentActionCommand,
    StudentPaymentRegenerationCommand,
    StudentPaymentScheduleCommand,
    build_student_quick_command,
)
from students.infrastructure import (
    execute_create_student_quick_command,
    execute_student_enrollment_action_command,
    execute_student_payment_action_command,
    execute_student_payment_regeneration_command,
    execute_student_payment_schedule_command,
    execute_student_intake_sync_command,
    execute_update_student_quick_command,
)


@dataclass(frozen=True, slots=True)
class StudentQuickWorkflowFacadeResult:
    student_id: int
    enrollment_id: int | None
    payment_id: int | None
    intake_id: int | None
    movement: str
    changed_fields: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StudentEnrollmentActionFacadeResult:
    student_id: int
    enrollment_id: int | None
    action: str


@dataclass(frozen=True, slots=True)
class StudentPaymentActionFacadeResult:
    student_id: int
    payment_id: int | None
    action: str


@dataclass(frozen=True, slots=True)
class StudentEnrollmentSyncFacadeResult:
    enrollment_id: int | None
    payment_id: int | None
    movement: str


@dataclass(frozen=True, slots=True)
class StudentIntakeSyncFacadeResult:
    intake_id: int | None


@dataclass(frozen=True, slots=True)
class StudentPaymentScheduleFacadeResult:
    student_id: int
    payment_id: int | None
    billing_group: str
    created_count: int


@dataclass(frozen=True, slots=True)
class StudentPaymentRegenerationFacadeResult:
    student_id: int
    payment_id: int | None
    enrollment_id: int | None


def _build_quick_workflow_result(result) -> StudentQuickWorkflowFacadeResult:
    return StudentQuickWorkflowFacadeResult(
        student_id=result.student.id,
        enrollment_id=result.enrollment_sync.enrollment_id,
        payment_id=result.enrollment_sync.payment_id,
        intake_id=result.intake_id,
        movement=result.enrollment_sync.movement,
        changed_fields=tuple(result.changed_fields),
    )


def run_student_quick_create(
    *,
    actor_id: int | None,
    cleaned_data: dict[str, Any],
    selected_intake_id: int | None = None,
) -> StudentQuickWorkflowFacadeResult:
    command = build_student_quick_command(
        actor_id=actor_id,
        cleaned_data=cleaned_data,
        selected_intake_id=selected_intake_id,
    )
    return _build_quick_workflow_result(execute_create_student_quick_command(command))


def run_student_quick_update(
    *,
    actor_id: int | None,
    cleaned_data: dict[str, Any],
    student_id: int,
    changed_fields: tuple[str, ...] = (),
    selected_intake_id: int | None = None,
) -> StudentQuickWorkflowFacadeResult:
    command = build_student_quick_command(
        actor_id=actor_id,
        cleaned_data=cleaned_data,
        student_id=student_id,
        selected_intake_id=selected_intake_id,
        changed_fields=changed_fields,
    )
    return _build_quick_workflow_result(execute_update_student_quick_command(command))


def run_student_enrollment_action(
    *,
    actor_id: int | None,
    student_id: int,
    enrollment_id: int,
    action: str,
    action_date: date,
    reason: str = '',
) -> StudentEnrollmentActionFacadeResult:
    result = execute_student_enrollment_action_command(
        StudentEnrollmentActionCommand(
            actor_id=actor_id,
            student_id=student_id,
            enrollment_id=enrollment_id,
            action=action,
            action_date=action_date,
            reason=reason,
        )
    )
    return StudentEnrollmentActionFacadeResult(
        student_id=result.student_id,
        enrollment_id=result.enrollment_id,
        action=result.action,
    )


def run_student_payment_action(
    *,
    actor_id: int | None,
    student_id: int,
    payment_id: int,
    action: str,
    amount: Decimal | None = None,
    due_date: date | None = None,
    method: str = '',
    reference: str = '',
    notes: str = '',
) -> StudentPaymentActionFacadeResult:
    result = execute_student_payment_action_command(
        StudentPaymentActionCommand(
            actor_id=actor_id,
            student_id=student_id,
            payment_id=payment_id,
            action=action,
            amount=amount,
            due_date=due_date,
            method=method,
            reference=reference,
            notes=notes,
        )
    )
    return StudentPaymentActionFacadeResult(
        student_id=result.student_id,
        payment_id=result.payment_id,
        action=result.action,
    )


def run_student_enrollment_sync(
    *,
    student_id: int,
    selected_plan_id: int | None,
    enrollment_status: str = '',
    due_date: date | None = None,
    payment_method: str = '',
    confirm_payment_now: bool = False,
    payment_reference: str = '',
    billing_strategy: str = 'single',
    installment_total: int = 1,
    recurrence_cycles: int = 1,
    initial_payment_amount: Decimal | None = None,
) -> StudentEnrollmentSyncFacadeResult:
    result = execute_student_enrollment_sync_command(
        StudentEnrollmentSyncCommand(
            student_id=student_id,
            selected_plan_id=selected_plan_id,
            enrollment_status=enrollment_status,
            due_date=due_date,
            payment_method=payment_method,
            confirm_payment_now=confirm_payment_now,
            payment_reference=payment_reference,
            billing_strategy=billing_strategy,
            installment_total=installment_total,
            recurrence_cycles=recurrence_cycles,
            initial_payment_amount=initial_payment_amount,
        )
    )
    return StudentEnrollmentSyncFacadeResult(
        enrollment_id=result.enrollment_id,
        payment_id=result.payment_id,
        movement=result.movement,
    )


def run_student_intake_sync(*, student_id: int, intake_record_id: int | None = None) -> StudentIntakeSyncFacadeResult:
    intake_id = execute_student_intake_sync_command(
        StudentIntakeSyncCommand(
            student_id=student_id,
            intake_record_id=intake_record_id,
        )
    )
    return StudentIntakeSyncFacadeResult(intake_id=intake_id)


def run_student_payment_schedule(
    *,
    student_id: int,
    enrollment_id: int | None,
    due_date: date,
    payment_method: str,
    confirm_payment_now: bool,
    note: str,
    amount: Decimal,
    reference: str,
    billing_strategy: str,
    installment_total: int,
    recurrence_cycles: int,
) -> StudentPaymentScheduleFacadeResult:
    result = execute_student_payment_schedule_command(
        StudentPaymentScheduleCommand(
            student_id=student_id,
            enrollment_id=enrollment_id,
            due_date=due_date,
            payment_method=payment_method,
            confirm_payment_now=confirm_payment_now,
            note=note,
            amount=amount,
            reference=reference,
            billing_strategy=billing_strategy,
            installment_total=installment_total,
            recurrence_cycles=recurrence_cycles,
        )
    )
    return StudentPaymentScheduleFacadeResult(
        student_id=result.student_id,
        payment_id=result.payment_id,
        billing_group=result.billing_group,
        created_count=result.created_count,
    )


def run_student_payment_regeneration(
    *,
    student_id: int,
    payment_id: int,
    enrollment_id: int | None = None,
) -> StudentPaymentRegenerationFacadeResult:
    result = execute_student_payment_regeneration_command(
        StudentPaymentRegenerationCommand(
            student_id=student_id,
            payment_id=payment_id,
            enrollment_id=enrollment_id,
        )
    )
    return StudentPaymentRegenerationFacadeResult(
        student_id=result.student_id,
        payment_id=result.payment_id,
        enrollment_id=result.enrollment_id,
    )


__all__ = [
    'StudentEnrollmentActionFacadeResult',
    'StudentEnrollmentSyncFacadeResult',
    'StudentIntakeSyncFacadeResult',
    'StudentPaymentActionFacadeResult',
    'StudentPaymentRegenerationFacadeResult',
    'StudentPaymentScheduleFacadeResult',
    'StudentQuickWorkflowFacadeResult',
    'run_student_enrollment_action',
    'run_student_enrollment_sync',
    'run_student_intake_sync',
    'run_student_payment_action',
    'run_student_payment_regeneration',
    'run_student_payment_schedule',
    'run_student_quick_create',
    'run_student_quick_update',
]