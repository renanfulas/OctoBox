"""
ARQUIVO: superficie publica das regras puras do dominio de alunos.

POR QUE ELE EXISTE:
- Reune politicas de negocio reutilizaveis por web, API e jobs sem depender de ORM ou Django.

O QUE ESTE ARQUIVO FAZ:
1. Exporta a politica de sincronizacao comercial de matricula.

PONTOS CRITICOS:
- So regras puras devem entrar aqui; persistencia e transacao continuam em infrastructure.
"""

from .action_policies import (
    EnrollmentActionDecision,
    PaymentMutationDecision,
    build_enrollment_action_decision,
    build_payment_mutation_decision,
    resolve_regeneration_enrollment_id,
)
from .enrollment_lifecycle import (
    EnrollmentCancellationDecision,
    EnrollmentReactivationDecision,
    EnrollmentSyncDefaults,
    build_enrollment_cancellation_decision,
    build_enrollment_reactivation_decision,
    resolve_enrollment_sync_defaults,
)
from .enrollment_sync import EnrollmentSyncDecision, append_enrollment_note, build_enrollment_sync_decision, describe_plan_change
from .intake_conversion import (
    DEFAULT_INTAKE_CONVERSION_NOTE,
    IntakeConversionDecision,
    IntakeLookupDecision,
    append_intake_note,
    build_intake_conversion_decision,
    build_intake_lookup_decision,
)
from .payment_terms import (
    PaymentRegenerationDecision,
    PlannedPayment,
    advance_due_date,
    build_payment_regeneration_decision,
    build_payment_schedule_plan,
    shift_month,
)

__all__ = [
    'EnrollmentSyncDecision',
    'EnrollmentActionDecision',
    'EnrollmentCancellationDecision',
    'EnrollmentReactivationDecision',
    'EnrollmentSyncDefaults',
    'IntakeConversionDecision',
    'IntakeLookupDecision',
    'PaymentRegenerationDecision',
    'PaymentMutationDecision',
    'PlannedPayment',
    'DEFAULT_INTAKE_CONVERSION_NOTE',
    'advance_due_date',
    'append_enrollment_note',
    'append_intake_note',
    'build_enrollment_cancellation_decision',
    'build_enrollment_action_decision',
    'build_enrollment_reactivation_decision',
    'build_enrollment_sync_decision',
    'build_intake_conversion_decision',
    'build_intake_lookup_decision',
    'build_payment_mutation_decision',
    'build_payment_regeneration_decision',
    'build_payment_schedule_plan',
    'describe_plan_change',
    'resolve_regeneration_enrollment_id',
    'resolve_enrollment_sync_defaults',
    'shift_month',
]