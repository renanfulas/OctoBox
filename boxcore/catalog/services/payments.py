"""
ARQUIVO: fachada do motor de cobrança do catálogo.

POR QUE ELE EXISTE:
- Mantem a interface interna historica enquanto a regra de agenda e regeneracao foi extraida para application + adapter.

O QUE ESTE ARQUIVO FAZ:
1. Traduz chamadas antigas para commands explicitos.
2. Encaminha execução para adapters Django do dominio de students.
3. Devolve os modelos Payment esperados pelas regras atuais.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar ORM nem regra de calculo financeiro.
"""

from finance.models import Payment
from students.application.commands import StudentPaymentRegenerationCommand, StudentPaymentScheduleCommand
from students.application.payment_terms import advance_due_date, shift_month
from students.infrastructure.django_payments import (
    execute_student_payment_regeneration_command,
    execute_student_payment_schedule_command,
)


def create_payment_schedule(
    *,
    student,
    enrollment,
    due_date,
    payment_method,
    confirm_payment_now,
    note,
    amount,
    reference,
    billing_strategy,
    installment_total,
    recurrence_cycles,
):
    command = StudentPaymentScheduleCommand(
        student_id=student.id,
        enrollment_id=getattr(enrollment, 'id', None),
        due_date=due_date,
        payment_method=payment_method,
        confirm_payment_now=confirm_payment_now,
        note=note,
        amount=amount,
        reference=reference,
        billing_strategy=billing_strategy,
        installment_total=installment_total,
        recurrence_cycles=recurrence_cycles,
    )
    result = execute_student_payment_schedule_command(command)
    return Payment.objects.get(pk=result.payment_id)


def regenerate_payment(*, student, payment, enrollment=None):
    command = StudentPaymentRegenerationCommand(
        student_id=student.id,
        payment_id=payment.id,
        enrollment_id=getattr(enrollment, 'id', None),
    )
    result = execute_student_payment_regeneration_command(command)
    if result.payment_id is None:
        return None
    return Payment.objects.get(pk=result.payment_id)


__all__ = ['advance_due_date', 'create_payment_schedule', 'regenerate_payment', 'shift_month']