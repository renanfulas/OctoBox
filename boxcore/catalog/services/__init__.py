"""
ARQUIVO: exportador dos services do catalogo.

POR QUE ELE EXISTE:
- Organiza a camada de regra de negocio usada pelas views leves de alunos e financeiro.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta services de matricula, cobranca, intake, workflows de aluno/plano, handlers operacionais e relatorios.
2. Mantem imports curtos dentro das views.

PONTOS CRITICOS:
- Qualquer mudanca de nome aqui impacta diretamente a orquestracao das views do catalogo.
"""

from .enrollments import cancel_enrollment, reactivate_enrollment, sync_student_enrollment
from .student_enrollment_actions import handle_student_enrollment_action
from .intakes import sync_student_intake
from .communications import register_operational_message
from .class_schedule_workflows import run_class_schedule_create_workflow
from .class_schedule_actions import (
    handle_class_session_cancel_action,
    handle_class_session_duplicate_action,
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
    'handle_class_session_cancel_action',
    'handle_class_session_duplicate_action',
    'handle_class_session_update_action',
    'handle_finance_communication_action',
    'handle_student_enrollment_action',
    'handle_student_payment_action',
    'reactivate_enrollment',
    'regenerate_payment',
    'register_operational_message',
    'run_class_schedule_create_workflow',
    'run_membership_plan_create_workflow',
    'run_membership_plan_update_workflow',
    'run_student_quick_create_workflow',
    'run_student_quick_update_workflow',
    'sync_student_enrollment',
    'sync_student_intake',
]