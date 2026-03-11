"""
ARQUIVO: exportador dos services do catalogo.

POR QUE ELE EXISTE:
- organiza a camada de regra de negocio usada pelas views leves de alunos, financeiro e grade de aulas.

O QUE ESTE ARQUIVO FAZ:
1. reexporta services de matricula, cobranca, intake, workflows e handlers operacionais.
2. expoe constantes e commands da grade de aulas para manter imports curtos nas views.

PONTOS CRITICOS:
- qualquer mudanca de nome aqui impacta diretamente a orquestracao das views do catalogo.
"""

from .enrollments import cancel_enrollment, reactivate_enrollment, sync_student_enrollment
from .student_enrollment_actions import handle_student_enrollment_action
from .intakes import sync_student_intake
from .communications import register_operational_message
from .class_schedule_workflows import run_class_schedule_create_workflow
from .class_grid_dispatcher import (
    FORM_KIND_PLANNER,
    FORM_KIND_SESSION_ACTION,
    FORM_KIND_SESSION_EDIT,
    resolve_class_grid_form_kind,
    resolve_class_grid_session_action,
)
from .class_grid_commands import (
    CLASS_GRID_ACTION_COMMANDS,
    run_class_session_delete_command,
    run_class_session_update_command,
)
from .class_schedule_actions import (
    handle_class_session_delete_action,
    handle_class_session_update_action,
)
from .finance_communication_actions import handle_finance_communication_action
from .operational_queue import build_operational_queue_metrics, build_operational_queue_snapshot
from .student_payment_actions import handle_student_payment_action
from .payments import regenerate_payment
from .membership_plan_workflows import run_membership_plan_create_workflow, run_membership_plan_update_workflow
from .reports import build_csv_response, build_pdf_response, build_report_response
from .student_workflows import run_student_quick_create_workflow, run_student_quick_update_workflow

__all__ = [
    'build_csv_response',
    'build_operational_queue_metrics',
    'build_operational_queue_snapshot',
    'build_pdf_response',
    'build_report_response',
    'cancel_enrollment',
    'CLASS_GRID_ACTION_COMMANDS',
    'FORM_KIND_PLANNER',
    'FORM_KIND_SESSION_ACTION',
    'FORM_KIND_SESSION_EDIT',
    'handle_class_session_delete_action',
    'handle_class_session_update_action',
    'handle_finance_communication_action',
    'handle_student_enrollment_action',
    'handle_student_payment_action',
    'reactivate_enrollment',
    'regenerate_payment',
    'register_operational_message',
    'resolve_class_grid_form_kind',
    'resolve_class_grid_session_action',
    'run_class_session_delete_command',
    'run_class_session_update_command',
    'run_class_schedule_create_workflow',
    'run_membership_plan_create_workflow',
    'run_membership_plan_update_workflow',
    'run_student_quick_create_workflow',
    'run_student_quick_update_workflow',
    'sync_student_enrollment',
    'sync_student_intake',
]