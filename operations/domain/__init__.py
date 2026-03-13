"""
ARQUIVO: superficie publica das regras puras do dominio operacional.

POR QUE ELE EXISTE:
- Reune politicas reutilizaveis das mutacoes operacionais sem depender de ORM ou Django.

O QUE ESTE ARQUIVO FAZ:
1. Exporta regras puras das actions do workspace.

PONTOS CRITICOS:
- Esta camada deve permanecer livre de framework; persistencia e auditoria ficam em infrastructure.
"""

from .class_grid_schedule import PlannedClassGridSlot, build_class_grid_schedule_plan, iter_schedule_dates
from .class_grid_session_policy import ClassGridSessionPolicy, build_class_grid_session_policy
from .class_grid_write_rules import (
    ClassGridCreateExecutionPlan,
    ClassGridPlannedCreationSlot,
    ClassGridCreateSlotDecision,
    ScheduledClassGridSlot,
    build_class_grid_create_execution_plan,
    build_class_grid_create_slot_decision,
    collect_changed_field_names,
    get_month_bounds,
    get_week_bounds,
    should_enforce_schedule_limits_for_status,
)
from .workspace_action_rules import (
    AttendanceActionDecision,
    TechnicalBehaviorNoteDecision,
    build_attendance_action_decision,
    build_payment_enrollment_note,
    build_technical_behavior_note_decision,
)

__all__ = [
    'AttendanceActionDecision',
    'ClassGridCreateExecutionPlan',
    'ClassGridPlannedCreationSlot',
    'ClassGridCreateSlotDecision',
    'PlannedClassGridSlot',
    'ClassGridSessionPolicy',
    'ScheduledClassGridSlot',
    'TechnicalBehaviorNoteDecision',
    'build_attendance_action_decision',
    'build_class_grid_create_execution_plan',
    'build_class_grid_create_slot_decision',
    'build_class_grid_schedule_plan',
    'build_class_grid_session_policy',
    'build_payment_enrollment_note',
    'build_technical_behavior_note_decision',
    'collect_changed_field_names',
    'get_month_bounds',
    'get_week_bounds',
    'iter_schedule_dates',
    'should_enforce_schedule_limits_for_status',
]