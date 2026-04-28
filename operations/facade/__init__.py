"""
ARQUIVO: entradas publicas por capacidade do app operations.

POR QUE ELE EXISTE:
- cria um andar publico entre delivery historico e o nucleo interno de operations.

O QUE ESTE ARQUIVO FAZ:
1. expoe fachadas estaveis por capacidade.
2. evita que views e services antigos conhecam wiring interno demais.

PONTOS CRITICOS:
- esta camada coordena entrada e saida; regra continua em domain/application e detalhe tecnico em infrastructure.
"""

from .class_grid import (
    ClassGridCommandResult,
    ClassGridPlannerResult,
    ClassGridResetResult,
    run_class_schedule_create,
    run_class_schedule_reset,
    run_class_session_delete,
    run_class_session_update,
)
from .workspace import (
    WorkspaceAttendanceActionResult,
    WorkspaceLinkPaymentResult,
    WorkspaceTechnicalBehaviorNoteResult,
    build_coach_workspace_snapshot,
    build_dev_workspace_snapshot,
    build_manager_workspace_snapshot,
    build_owner_workspace_snapshot,
    build_reception_workspace_snapshot,
    run_apply_attendance_action,
    run_create_technical_behavior_note,
    run_link_payment_enrollment,
)

__all__ = [
    'ClassGridCommandResult',
    'ClassGridPlannerResult',
    'ClassGridResetResult',
    'WorkspaceAttendanceActionResult',
    'WorkspaceLinkPaymentResult',
    'WorkspaceTechnicalBehaviorNoteResult',
    'build_coach_workspace_snapshot',
    'build_dev_workspace_snapshot',
    'build_manager_workspace_snapshot',
    'build_owner_workspace_snapshot',
    'build_reception_workspace_snapshot',
    'run_apply_attendance_action',
    'run_class_schedule_create',
    'run_class_schedule_reset',
    'run_class_session_delete',
    'run_class_session_update',
    'run_create_technical_behavior_note',
    'run_link_payment_enrollment',
]
