"""
ARQUIVO: commands explicitos do fluxo rapido de aluno.

POR QUE ELE EXISTE:
- Evita que o caso de uso dependa de cleaned_data solto, ModelForm ou request web.

O QUE ESTE ARQUIVO FAZ:
1. Define o contrato de entrada do fluxo rapido de aluno.
2. Traduz dados validados da UI para um command estavel.

PONTOS CRITICOS:
- O command precisa ficar pequeno, explicito e independente do framework.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class StudentQuickCommand:
    actor_id: int | None
    full_name: str
    phone: str
    status: str
    email: str = ''
    gender: str = ''
    birth_date: date | None = None
    health_issue_status: str = ''
    cpf: str = ''
    acquisition_source: str = ''
    acquisition_source_detail: str = ''
    resolved_acquisition_source: str = ''
    resolved_source_detail: str = ''
    source_confidence: str = 'unknown'
    source_conflict_flag: bool = False
    source_resolution_method: str = ''
    source_resolution_reason: str = ''
    source_captured_at: datetime | None = None
    notes: str = ''
    student_id: int | None = None
    selected_plan_id: int | None = None
    enrollment_status: str = ''
    payment_due_date: date | None = None
    payment_method: str = ''
    confirm_payment_now: bool = False
    payment_reference: str = ''
    billing_strategy: str = 'single'
    installment_total: int = 1
    recurrence_cycles: int = 1
    initial_payment_amount: Decimal | None = None
    intake_record_id: int | None = None
    changed_fields: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StudentPaymentActionCommand:
    actor_id: int | None
    student_id: int
    payment_id: int
    action: str
    amount: Decimal | None = None
    due_date: date | None = None
    method: str = ''
    reference: str = ''
    notes: str = ''


@dataclass(frozen=True, slots=True)
class StudentEnrollmentActionCommand:
    actor_id: int | None
    student_id: int
    enrollment_id: int
    action: str
    action_date: date
    reason: str = ''


@dataclass(frozen=True, slots=True)
class StudentEnrollmentSyncCommand:
    student_id: int
    selected_plan_id: int | None
    enrollment_status: str = ''
    due_date: date | None = None
    payment_method: str = ''
    confirm_payment_now: bool = False
    payment_reference: str = ''
    billing_strategy: str = 'single'
    installment_total: int = 1
    recurrence_cycles: int = 1
    initial_payment_amount: Decimal | None = None


@dataclass(frozen=True, slots=True)
class StudentIntakeSyncCommand:
    student_id: int
    intake_record_id: int | None = None


@dataclass(frozen=True, slots=True)
class StudentPaymentScheduleCommand:
    student_id: int
    enrollment_id: int | None
    due_date: date
    payment_method: str
    confirm_payment_now: bool
    note: str
    amount: Decimal
    reference: str
    billing_strategy: str
    installment_total: int
    recurrence_cycles: int


@dataclass(frozen=True, slots=True)
class StudentPaymentRegenerationCommand:
    student_id: int
    payment_id: int
    enrollment_id: int | None = None


def _resolve_model_id(instance: Any) -> int | None:
    if instance is None:
        return None
    return getattr(instance, 'id', None)


def build_student_quick_command(
    *,
    actor_id: int | None,
    cleaned_data: dict[str, Any],
    student_id: int | None = None,
    selected_intake_id: int | None = None,
    changed_fields: tuple[str, ...] = (),
) -> StudentQuickCommand:
    intake_record = cleaned_data.get('intake_record')
    selected_plan = cleaned_data.get('selected_plan')

    return StudentQuickCommand(
        actor_id=actor_id,
        student_id=student_id,
        full_name=cleaned_data.get('full_name') or '',
        phone=cleaned_data.get('phone') or '',
        status=cleaned_data.get('status') or '',
        email=cleaned_data.get('email') or '',
        gender=cleaned_data.get('gender') or '',
        birth_date=cleaned_data.get('birth_date'),
        health_issue_status=cleaned_data.get('health_issue_status') or '',
        cpf=cleaned_data.get('cpf') or '',
        acquisition_source=cleaned_data.get('acquisition_source') or '',
        acquisition_source_detail=cleaned_data.get('acquisition_source_detail') or '',
        resolved_acquisition_source=cleaned_data.get('resolved_acquisition_source') or '',
        resolved_source_detail=cleaned_data.get('resolved_source_detail') or '',
        source_confidence=cleaned_data.get('source_confidence') or 'unknown',
        source_conflict_flag=bool(cleaned_data.get('source_conflict_flag')),
        source_resolution_method=cleaned_data.get('source_resolution_method') or '',
        source_resolution_reason=cleaned_data.get('source_resolution_reason') or '',
        source_captured_at=cleaned_data.get('source_captured_at'),
        notes=cleaned_data.get('notes') or '',
        selected_plan_id=_resolve_model_id(selected_plan),
        enrollment_status=cleaned_data.get('enrollment_status') or '',
        payment_due_date=cleaned_data.get('payment_due_date'),
        payment_method=cleaned_data.get('payment_method') or '',
        confirm_payment_now=bool(cleaned_data.get('confirm_payment_now')),
        payment_reference=cleaned_data.get('payment_reference') or '',
        billing_strategy=cleaned_data.get('billing_strategy') or 'single',
        installment_total=cleaned_data.get('installment_total') or 1,
        recurrence_cycles=cleaned_data.get('recurrence_cycles') or 1,
        initial_payment_amount=cleaned_data.get('initial_payment_amount'),
        intake_record_id=selected_intake_id or _resolve_model_id(intake_record),
        changed_fields=changed_fields,
    )


__all__ = [
    'StudentEnrollmentActionCommand',
    'StudentEnrollmentSyncCommand',
    'StudentIntakeSyncCommand',
    'StudentPaymentRegenerationCommand',
    'StudentPaymentActionCommand',
    'StudentPaymentScheduleCommand',
    'StudentQuickCommand',
    'build_student_quick_command',
]
