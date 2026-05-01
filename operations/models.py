"""
ARQUIVO: superficie estavel de modelos do dominio operacional.

POR QUE ELE EXISTE:
- reduz imports diretos de boxcore.models nas camadas de operations.

O QUE ESTE ARQUIVO FAZ:
1. reexporta aulas, presencas e ocorrencias.
2. reexporta enums operacionais usados por views, queries e adapters.

PONTOS CRITICOS:
- o ownership de codigo da operacao diaria ja saiu de boxcore, mas o estado historico do app ainda permanece nesta fase.
"""

from operations.model_definitions import (
    Attendance,
    AttendanceStatus,
    BehaviorCategory,
    BehaviorNote,
    ClassType,
    ClassSession,
    LeadImportDeclaredRange,
    LeadImportJob,
    LeadImportJobStatus,
    LeadImportProcessingMode,
    LeadImportSourceType,
    SessionCancellationEvent,
    SessionStatus,
    WorkoutApprovalPolicySetting,
    WorkoutTemplate,
    WorkoutTemplateBlock,
    WorkoutTemplateMovement,
    WorkoutPlannerTemplatePickerEvent,
    SmartPlanGateEvent,
    SmartPlanGateOutcome,
)

__all__ = [
    'Attendance',
    'AttendanceStatus',
    'BehaviorCategory',
    'BehaviorNote',
    'ClassType',
    'ClassSession',
    'LeadImportDeclaredRange',
    'LeadImportJob',
    'LeadImportJobStatus',
    'LeadImportProcessingMode',
    'LeadImportSourceType',
    'SessionCancellationEvent',
    'SessionStatus',
    'WorkoutApprovalPolicySetting',
    'WorkoutTemplate',
    'WorkoutTemplateBlock',
    'WorkoutTemplateMovement',
    'WorkoutPlannerTemplatePickerEvent',
    'SmartPlanGateEvent',
    'SmartPlanGateOutcome',
]
