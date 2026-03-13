"""
ARQUIVO: politicas puras das actions comerciais do aluno.

POR QUE ELE EXISTE:
- Remove do adapter Django as decisoes de mutacao de pagamento, despacho de matricula e precedencia de regeneracao.

O QUE ESTE ARQUIVO FAZ:
1. Define a mutacao comercial de cada action de pagamento.
2. Define o despacho tecnico das actions de matricula.
3. Resolve a matricula alvo para regeneracao sem depender de ORM.

PONTOS CRITICOS:
- Esta camada deve permanecer pura; consulta e persistencia continuam em infrastructure.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PaymentMutationDecision:
    status: str
    update_paid_at: bool
    audit_method: str


@dataclass(frozen=True, slots=True)
class EnrollmentActionDecision:
    handler_name: str
    audit_method: str
    use_action_result_enrollment: bool


def build_payment_mutation_decision(action: str) -> PaymentMutationDecision | None:
    decisions = {
        'mark-paid': PaymentMutationDecision(
            status='paid',
            update_paid_at=True,
            audit_method='record_payment_marked_paid',
        ),
        'refund-payment': PaymentMutationDecision(
            status='refunded',
            update_paid_at=False,
            audit_method='record_payment_refunded',
        ),
        'cancel-payment': PaymentMutationDecision(
            status='canceled',
            update_paid_at=False,
            audit_method='record_payment_canceled',
        ),
    }
    return decisions.get(action)


def build_enrollment_action_decision(action: str) -> EnrollmentActionDecision | None:
    decisions = {
        'cancel-enrollment': EnrollmentActionDecision(
            handler_name='cancel_student_enrollment_command',
            audit_method='record_enrollment_canceled',
            use_action_result_enrollment=False,
        ),
        'reactivate-enrollment': EnrollmentActionDecision(
            handler_name='reactivate_student_enrollment_command',
            audit_method='record_enrollment_reactivated',
            use_action_result_enrollment=True,
        ),
    }
    return decisions.get(action)


def resolve_regeneration_enrollment_id(*, payment_enrollment_id: int | None, latest_enrollment_id: int | None) -> int | None:
    return payment_enrollment_id or latest_enrollment_id


__all__ = [
    'EnrollmentActionDecision',
    'PaymentMutationDecision',
    'build_enrollment_action_decision',
    'build_payment_mutation_decision',
    'resolve_regeneration_enrollment_id',
]