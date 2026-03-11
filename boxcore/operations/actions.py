"""
ARQUIVO: handlers das acoes operacionais por papel.

POR QUE ELE EXISTE:
- Tira da camada HTTP as mudancas de estado reais executadas por manager e coach.

O QUE ESTE ARQUIVO FAZ:
1. Vincula pagamento a matricula ativa.
2. Registra ocorrencia tecnica de comportamento.
3. Atualiza status operacional de presenca com auditoria.

PONTOS CRITICOS:
- Qualquer regressao aqui muda estado real da operacao e da trilha de auditoria.
"""

from django.utils import timezone

from boxcore.auditing import log_audit_event
from boxcore.models import AttendanceStatus, BehaviorCategory, BehaviorNote, Enrollment, EnrollmentStatus


def handle_payment_enrollment_link_action(*, actor, payment):
    active_enrollment = Enrollment.objects.filter(
        student=payment.student,
        status=EnrollmentStatus.ACTIVE,
    ).order_by('-start_date').first()

    if active_enrollment is None:
        return None

    payment.enrollment = active_enrollment
    if not payment.notes:
        payment.notes = 'Vinculo operacional aplicado pela area do manager.'
    payment.save(update_fields=['enrollment', 'notes', 'updated_at'])
    log_audit_event(
        actor=actor,
        action='payment_linked_to_active_enrollment',
        target=payment,
        description='Manager vinculou pagamento a matricula ativa.',
        metadata={'enrollment_id': active_enrollment.id},
    )
    return payment


def handle_technical_behavior_note_action(*, actor, student, category, description):
    valid_categories = {choice for choice, _ in BehaviorCategory.choices}
    if not description or category not in valid_categories:
        return None

    note = BehaviorNote.objects.create(
        student=student,
        author=actor,
        category=category,
        description=description,
    )
    log_audit_event(
        actor=actor,
        action='technical_behavior_note_created',
        target=note,
        description='Coach registrou ocorrencia tecnica.',
        metadata={'student_id': student.id, 'category': category},
    )
    return note


def handle_attendance_action(*, actor, attendance, action):
    now = timezone.now()

    if action == 'check-in':
        attendance.status = AttendanceStatus.CHECKED_IN
        attendance.check_in_at = now
    elif action == 'check-out':
        attendance.status = AttendanceStatus.CHECKED_OUT
        attendance.check_out_at = now
        if attendance.check_in_at is None:
            attendance.check_in_at = now
    elif action == 'absent':
        attendance.status = AttendanceStatus.ABSENT
    else:
        return None

    attendance.save(update_fields=['status', 'check_in_at', 'check_out_at', 'updated_at'])
    log_audit_event(
        actor=actor,
        action=f'attendance_{action}',
        target=attendance,
        description='Coach alterou status operacional de presenca.',
        metadata={'status': attendance.status},
    )
    return attendance


link_payment_to_active_enrollment = handle_payment_enrollment_link_action
create_technical_behavior_note = handle_technical_behavior_note_action
apply_attendance_action = handle_attendance_action