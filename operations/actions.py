"""
ARQUIVO: handlers das acoes operacionais por papel.

POR QUE ELE EXISTE:
- tira da camada HTTP as mudancas de estado reais executadas por manager e coach no app real operations.

O QUE ESTE ARQUIVO FAZ:
1. vincula pagamento a matricula ativa.
2. registra ocorrencia tecnica de comportamento.
3. atualiza status operacional de presenca com auditoria.

PONTOS CRITICOS:
- qualquer regressao aqui muda estado real da operacao e da trilha de auditoria.
"""

from finance.models import Payment
from operations.facade import (
    run_apply_attendance_action,
    run_create_technical_behavior_note,
    run_link_payment_enrollment,
)
from operations.models import Attendance, BehaviorNote


def handle_payment_enrollment_link_action(*, actor, payment):
    result = run_link_payment_enrollment(actor_id=getattr(actor, 'id', None), payment_id=payment.id)
    if result is None:
        return None
    return Payment.objects.get(pk=result.payment_id)


def handle_technical_behavior_note_action(*, actor, student, category, description):
    result = run_create_technical_behavior_note(
        actor_id=getattr(actor, 'id', None),
        student_id=student.id,
        category=category,
        description=description,
    )
    if result is None:
        return None
    return BehaviorNote.objects.get(pk=result.note_id)


def handle_attendance_action(*, actor, attendance, action):
    result = run_apply_attendance_action(
        actor_id=getattr(actor, 'id', None),
        attendance_id=attendance.id,
        action=action,
    )
    if result is None:
        return None
    return Attendance.objects.get(pk=result.attendance_id)


link_payment_to_active_enrollment = handle_payment_enrollment_link_action
create_technical_behavior_note = handle_technical_behavior_note_action
apply_attendance_action = handle_attendance_action

__all__ = [
    'apply_attendance_action',
    'create_technical_behavior_note',
    'handle_attendance_action',
    'handle_payment_enrollment_link_action',
    'handle_technical_behavior_note_action',
    'link_payment_to_active_enrollment',
]