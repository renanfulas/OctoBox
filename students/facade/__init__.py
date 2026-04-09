"""
ARQUIVO: entradas publicas por capacidade do app students.

POR QUE ELE EXISTE:
- cria um ponto de entrada estavel para o lifecycle comercial do aluno sem expor commands e wiring interno ao catalogo historico.

O QUE ESTE ARQUIVO FAZ:
1. expoe a facade do lifecycle do aluno.
2. estabiliza a fronteira publica de students para consumo por outras cascas.

PONTOS CRITICOS:
- esta camada organiza entrada e saida; regra continua em domain/application e detalhe tecnico em infrastructure.
"""

from .student_lifecycle import (
    StudentEnrollmentActionFacadeResult,
    StudentEnrollmentSyncFacadeResult,
    StudentIntakeSyncFacadeResult,
    StudentPaymentActionFacadeResult,
    StudentPaymentRegenerationFacadeResult,
    StudentPaymentScheduleFacadeResult,
    StudentQuickWorkflowFacadeResult,
    run_student_enrollment_action,
    run_student_enrollment_sync,
    run_student_intake_sync,
    run_student_payment_action,
    run_student_payment_regeneration,
    run_student_payment_schedule,
    run_student_quick_create,
    run_student_quick_update,
)
from .student_attribution import (
    StudentSourceDeclarationFacadeResult,
    run_student_source_declaration_record,
)

__all__ = [
    'StudentEnrollmentActionFacadeResult',
    'StudentEnrollmentSyncFacadeResult',
    'StudentIntakeSyncFacadeResult',
    'StudentPaymentActionFacadeResult',
    'StudentPaymentRegenerationFacadeResult',
    'StudentPaymentScheduleFacadeResult',
    'StudentQuickWorkflowFacadeResult',
    'StudentSourceDeclarationFacadeResult',
    'run_student_enrollment_action',
    'run_student_enrollment_sync',
    'run_student_intake_sync',
    'run_student_payment_action',
    'run_student_payment_regeneration',
    'run_student_payment_schedule',
    'run_student_quick_create',
    'run_student_quick_update',
    'run_student_source_declaration_record',
]
