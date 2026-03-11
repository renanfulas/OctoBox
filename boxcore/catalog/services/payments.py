"""
ARQUIVO: services de cobrança do catálogo.

POR QUE ELE EXISTE:
- Tira da camada de view a montagem de parcelas, recorrências e regeneração de cobranças.

O QUE ESTE ARQUIVO FAZ:
1. Calcula vencimentos futuros por ciclo de cobrança.
2. Cria cobranças únicas, parceladas ou recorrentes.
3. Regenera uma nova cobrança preservando o grupo comercial.

PONTOS CRITICOS:
- Qualquer erro aqui afeta vencimentos, parcelamento e status financeiro do aluno.
"""

from decimal import Decimal
from uuid import uuid4

from django.utils import timezone

from boxcore.models import BillingCycle, Payment, PaymentStatus


def shift_month(source_date, month_delta):
    month_index = source_date.month - 1 + month_delta
    year = source_date.year + month_index // 12
    month = month_index % 12 + 1
    return source_date.replace(year=year, month=month, day=1)


def advance_due_date(start_date, step, billing_cycle):
    if step == 0:
        return start_date
    if billing_cycle == BillingCycle.WEEKLY:
        return start_date + timezone.timedelta(days=7 * step)
    if billing_cycle == BillingCycle.QUARTERLY:
        return shift_month(start_date, step * 3)
    if billing_cycle == BillingCycle.YEARLY:
        return shift_month(start_date, step * 12)
    return shift_month(start_date, step)


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
    billing_group = str(uuid4())
    normalized_amount = Decimal(amount)
    created_payment = None

    if billing_strategy == 'installments':
        total = max(installment_total, 1)
        installment_amount = (normalized_amount / total).quantize(Decimal('0.01'))
        running_total = Decimal('0.00')
        for index in range(1, total + 1):
            current_amount = installment_amount if index < total else normalized_amount - running_total
            running_total += current_amount
            payment = Payment.objects.create(
                student=student,
                enrollment=enrollment,
                due_date=advance_due_date(due_date, index - 1, enrollment.plan.billing_cycle),
                amount=current_amount,
                status=PaymentStatus.PAID if confirm_payment_now and index == 1 else PaymentStatus.PENDING,
                method=payment_method,
                paid_at=timezone.now() if confirm_payment_now and index == 1 else None,
                reference=reference,
                notes=note,
                billing_group=billing_group,
                installment_number=index,
                installment_total=total,
            )
            created_payment = created_payment or payment
        return created_payment

    if billing_strategy == 'recurring':
        cycles = max(recurrence_cycles, 1)
        for index in range(1, cycles + 1):
            payment = Payment.objects.create(
                student=student,
                enrollment=enrollment,
                due_date=advance_due_date(due_date, index - 1, enrollment.plan.billing_cycle),
                amount=normalized_amount,
                status=PaymentStatus.PAID if confirm_payment_now and index == 1 else PaymentStatus.PENDING,
                method=payment_method,
                paid_at=timezone.now() if confirm_payment_now and index == 1 else None,
                reference=reference,
                notes=note,
                billing_group=billing_group,
                installment_number=index,
                installment_total=cycles,
            )
            created_payment = created_payment or payment
        return created_payment

    return Payment.objects.create(
        student=student,
        enrollment=enrollment,
        due_date=due_date,
        amount=normalized_amount,
        status=PaymentStatus.PAID if confirm_payment_now else PaymentStatus.PENDING,
        method=payment_method,
        paid_at=timezone.now() if confirm_payment_now else None,
        reference=reference,
        notes=note,
        billing_group=billing_group,
        installment_number=1,
        installment_total=1,
    )


def regenerate_payment(*, student, payment, enrollment=None):
    target_enrollment = enrollment or student.enrollments.order_by('-start_date', '-created_at').first()
    if target_enrollment is None:
        return None

    return Payment.objects.create(
        student=student,
        enrollment=target_enrollment,
        due_date=advance_due_date(payment.due_date, 1, target_enrollment.plan.billing_cycle),
        amount=payment.amount,
        status=PaymentStatus.PENDING,
        method=payment.method,
        reference=payment.reference,
        notes='Cobranca regenerada pela tela do aluno.',
        billing_group=payment.billing_group or str(uuid4()),
        installment_number=payment.installment_number + 1,
        installment_total=max(payment.installment_total, payment.installment_number + 1),
    )