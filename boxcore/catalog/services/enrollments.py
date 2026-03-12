"""
ARQUIVO: fachada do motor de matrícula do catálogo.

POR QUE ELE EXISTE:
- Mantem o contrato historico de matrícula enquanto a implementação real foi movida para commands e adapters do domínio students.

O QUE ESTE ARQUIVO FAZ:
1. Traduz a sincronização de matrícula para um command explícito.
2. Encaminha cancelamento e reativação para o adapter real.
3. Devolve modelos e payloads compatíveis com os chamadores atuais.

PONTOS CRITICOS:
- Este arquivo não deve voltar a concentrar ORM, transação ou geração de cobrança.
"""

from boxcore.models import Enrollment, MembershipPlan, Payment
from students.application.commands import StudentEnrollmentActionCommand, StudentEnrollmentSyncCommand
from students.infrastructure.django_enrollments import (
    cancel_student_enrollment_command,
    execute_student_enrollment_sync_command,
    reactivate_student_enrollment_command,
)


def sync_student_enrollment(
    *,
    student,
    selected_plan,
    enrollment_status=None,
    due_date=None,
    payment_method=None,
    confirm_payment_now=False,
    payment_reference='',
    billing_strategy='single',
    installment_total=1,
    recurrence_cycles=1,
    initial_payment_amount=None,
):
    result = execute_student_enrollment_sync_command(
        StudentEnrollmentSyncCommand(
            student_id=student.id,
            selected_plan_id=getattr(selected_plan, 'id', None),
            enrollment_status=enrollment_status or '',
            due_date=due_date,
            payment_method=payment_method or '',
            confirm_payment_now=confirm_payment_now,
            payment_reference=payment_reference,
            billing_strategy=billing_strategy,
            installment_total=installment_total,
            recurrence_cycles=recurrence_cycles,
            initial_payment_amount=initial_payment_amount,
        )
    )
    enrollment = Enrollment.objects.filter(pk=result.enrollment_id).first() if result.enrollment_id else None
    payment = Payment.objects.filter(pk=result.payment_id).first() if result.payment_id else None
    return {'enrollment': enrollment, 'payment': payment, 'movement': result.movement}


def cancel_enrollment(*, enrollment, action_date, reason=''):
    command = StudentEnrollmentActionCommand(
        actor_id=None,
        student_id=enrollment.student_id,
        enrollment_id=enrollment.id,
        action='cancel-enrollment',
        action_date=action_date,
        reason=reason,
    )
    result = cancel_student_enrollment_command(command)
    return Enrollment.objects.get(pk=result.enrollment_id)


def reactivate_enrollment(*, student, enrollment, action_date, reason=''):
    command = StudentEnrollmentActionCommand(
        actor_id=None,
        student_id=student.id,
        enrollment_id=enrollment.id,
        action='reactivate-enrollment',
        action_date=action_date,
        reason=reason,
    )
    result = reactivate_student_enrollment_command(command)
    return Enrollment.objects.get(pk=result.enrollment_id)


def describe_plan_change(previous_plan, selected_plan):
    if selected_plan.price > previous_plan.price:
        return 'upgrade'
    if selected_plan.price < previous_plan.price:
        return 'downgrade'
    return 'troca de plano'