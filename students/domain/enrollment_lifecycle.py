"""
ARQUIVO: politicas puras do ciclo de vida comercial da matricula.

POR QUE ELE EXISTE:
- Remove do adapter Django os defaults comerciais da sincronizacao e as decisoes de cancelamento/reativacao.

O QUE ESTE ARQUIVO FAZ:
1. Normaliza defaults comerciais da sincronizacao de matricula.
2. Define a decisao pura de cancelamento de matricula.
3. Define a decisao pura de reativacao e da cobranca inicial associada.

PONTOS CRITICOS:
- Esta camada deve permanecer pura; lock, ORM e transacao continuam em infrastructure.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class EnrollmentSyncDefaults:
    enrollment_status: str
    due_date: date
    payment_method: str
    billing_strategy: str
    installment_total: int
    recurrence_cycles: int
    base_amount: Decimal


@dataclass(frozen=True, slots=True)
class EnrollmentCancellationDecision:
    status: str
    end_date: date
    note: str
    cancel_payment_status: str
    cancel_pending_from_date: date


@dataclass(frozen=True, slots=True)
class EnrollmentReactivationDecision:
    expire_current_active_status: str
    expire_current_active_end_date: date
    cancel_payment_statuses: tuple[str, ...]
    cancel_payment_target_status: str
    new_enrollment_status: str
    new_enrollment_start_date: date
    new_enrollment_note: str
    payment_due_date: date
    payment_method: str
    confirm_payment_now: bool
    payment_note: str
    payment_reference: str
    billing_strategy: str
    installment_total: int
    recurrence_cycles: int


def resolve_enrollment_sync_defaults(
    *,
    enrollment_status: str,
    due_date: date | None,
    payment_method: str,
    billing_strategy: str,
    installment_total: int,
    recurrence_cycles: int,
    initial_payment_amount: Decimal | None,
    selected_plan_price: Decimal | None,
    today: date,
) -> EnrollmentSyncDefaults:
    return EnrollmentSyncDefaults(
        enrollment_status=enrollment_status or 'pending',
        due_date=due_date or today,
        payment_method=payment_method or 'pix',
        billing_strategy=billing_strategy or 'single',
        installment_total=installment_total or 1,
        recurrence_cycles=recurrence_cycles or 1,
        base_amount=initial_payment_amount or selected_plan_price or Decimal('0.00'),
    )


def build_enrollment_cancellation_decision(*, action_date: date, reason: str) -> EnrollmentCancellationDecision:
    normalized_reason = reason or 'nao informado'
    return EnrollmentCancellationDecision(
        status='canceled',
        end_date=action_date,
        note=f'Cancelada pela tela do aluno. Motivo: {normalized_reason}.',
        cancel_payment_status='canceled',
        cancel_pending_from_date=action_date,
    )


def build_enrollment_reactivation_decision(*, action_date: date, reason: str) -> EnrollmentReactivationDecision:
    normalized_reason = reason or 'nao informado'
    return EnrollmentReactivationDecision(
        expire_current_active_status='expired',
        expire_current_active_end_date=action_date,
        cancel_payment_statuses=('pending', 'overdue'),
        cancel_payment_target_status='canceled',
        new_enrollment_status='active',
        new_enrollment_start_date=action_date,
        new_enrollment_note=f'Reativada pela tela do aluno. Motivo: {normalized_reason}.',
        payment_due_date=action_date,
        payment_method='pix',
        confirm_payment_now=False,
        payment_note='Cobranca criada na reativacao da matricula.',
        payment_reference='',
        billing_strategy='single',
        installment_total=1,
        recurrence_cycles=1,
    )


__all__ = [
    'EnrollmentCancellationDecision',
    'EnrollmentReactivationDecision',
    'EnrollmentSyncDefaults',
    'build_enrollment_cancellation_decision',
    'build_enrollment_reactivation_decision',
    'resolve_enrollment_sync_defaults',
]