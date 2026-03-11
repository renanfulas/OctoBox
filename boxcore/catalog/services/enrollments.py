"""
ARQUIVO: services de matrícula do catálogo.

POR QUE ELE EXISTE:
- Centraliza as regras comerciais de vínculo entre aluno, plano e status de matrícula.

O QUE ESTE ARQUIVO FAZ:
1. Sincroniza a matrícula ativa com o plano escolhido no fluxo leve.
2. Decide criação, ajuste de status, upgrade, downgrade ou troca de plano.
3. Cancela e reativa matrículas preservando histórico.

PONTOS CRITICOS:
- Esta camada coordena criação de matrícula e cobrança inicial, então qualquer regressão aqui afeta o fluxo comercial.
"""

from decimal import Decimal

from django.utils import timezone

from boxcore.models import Enrollment, EnrollmentStatus, PaymentMethod, PaymentStatus

from .payments import create_payment_schedule


def describe_plan_change(previous_plan, selected_plan):
    if selected_plan.price > previous_plan.price:
        return 'upgrade'
    if selected_plan.price < previous_plan.price:
        return 'downgrade'
    return 'troca de plano'


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
    enrollment_status = enrollment_status or EnrollmentStatus.PENDING
    due_date = due_date or timezone.localdate()
    payment_method = payment_method or PaymentMethod.PIX
    installment_total = installment_total or 1
    recurrence_cycles = recurrence_cycles or 1
    latest_enrollment = student.enrollments.order_by('-start_date', '-created_at').first()
    base_amount = initial_payment_amount or (selected_plan.price if selected_plan else Decimal('0.00'))

    if selected_plan is None:
        return {'enrollment': None, 'payment': None, 'movement': 'none'}

    if latest_enrollment is None:
        enrollment = Enrollment.objects.create(
            student=student,
            plan=selected_plan,
            status=enrollment_status,
            start_date=timezone.localdate(),
            notes='Plano conectado pela tela leve do aluno.',
        )
        payment = create_payment_schedule(
            student=student,
            enrollment=enrollment,
            due_date=due_date,
            payment_method=payment_method,
            confirm_payment_now=confirm_payment_now,
            note='Primeira cobranca criada no fluxo leve do aluno.',
            amount=base_amount,
            reference=payment_reference,
            billing_strategy=billing_strategy,
            installment_total=installment_total,
            recurrence_cycles=recurrence_cycles,
        )
        return {'enrollment': enrollment, 'payment': payment, 'movement': 'created'}

    if latest_enrollment.plan_id == selected_plan.id:
        latest_enrollment.plan = selected_plan
        latest_enrollment.status = enrollment_status
        if latest_enrollment.start_date is None:
            latest_enrollment.start_date = timezone.localdate()
        latest_enrollment.save(update_fields=['plan', 'status', 'start_date', 'updated_at'])
        payment = None
        if not latest_enrollment.payments.exists():
            payment = create_payment_schedule(
                student=student,
                enrollment=latest_enrollment,
                due_date=due_date,
                payment_method=payment_method,
                confirm_payment_now=confirm_payment_now,
                note='Primeira cobranca criada no fluxo leve do aluno.',
                amount=base_amount,
                reference=payment_reference,
                billing_strategy=billing_strategy,
                installment_total=installment_total,
                recurrence_cycles=recurrence_cycles,
            )
        return {'enrollment': latest_enrollment, 'payment': payment, 'movement': 'status_adjusted'}

    movement = describe_plan_change(latest_enrollment.plan, selected_plan)
    latest_enrollment.status = EnrollmentStatus.EXPIRED
    latest_enrollment.end_date = timezone.localdate()
    latest_enrollment.notes = '\n'.join(
        filter(None, [latest_enrollment.notes.strip(), f'Encerrada por {movement} na tela leve do aluno.'])
    )
    latest_enrollment.save(update_fields=['status', 'end_date', 'notes', 'updated_at'])

    enrollment = Enrollment.objects.create(
        student=student,
        plan=selected_plan,
        status=enrollment_status,
        start_date=timezone.localdate(),
        notes=f'{movement.capitalize()} aplicada pela tela leve do aluno.',
    )
    payment = create_payment_schedule(
        student=student,
        enrollment=enrollment,
        due_date=due_date,
        payment_method=payment_method,
        confirm_payment_now=confirm_payment_now,
        note=f'Cobranca criada apos {movement} de plano.',
        amount=base_amount,
        reference=payment_reference,
        billing_strategy=billing_strategy,
        installment_total=installment_total,
        recurrence_cycles=recurrence_cycles,
    )
    return {'enrollment': enrollment, 'payment': payment, 'movement': movement}


def cancel_enrollment(*, enrollment, action_date, reason=''):
    enrollment.status = EnrollmentStatus.CANCELED
    enrollment.end_date = action_date
    enrollment.notes = '\n'.join(
        filter(None, [enrollment.notes.strip(), f'Cancelada pela tela do aluno. Motivo: {reason or "nao informado"}.'])
    )
    enrollment.save(update_fields=['status', 'end_date', 'notes', 'updated_at'])
    enrollment.payments.filter(status=PaymentStatus.PENDING, due_date__gte=action_date).update(status=PaymentStatus.CANCELED)
    return enrollment


def reactivate_enrollment(*, student, enrollment, action_date, reason=''):
    student.enrollments.filter(status=EnrollmentStatus.ACTIVE).exclude(pk=enrollment.pk).update(
        status=EnrollmentStatus.EXPIRED,
        end_date=action_date,
    )
    enrollment.payments.filter(status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE]).update(status=PaymentStatus.CANCELED)
    new_enrollment = Enrollment.objects.create(
        student=student,
        plan=enrollment.plan,
        status=EnrollmentStatus.ACTIVE,
        start_date=action_date,
        notes=f'Reativada pela tela do aluno. Motivo: {reason or "nao informado"}.',
    )
    create_payment_schedule(
        student=student,
        enrollment=new_enrollment,
        due_date=action_date,
        payment_method=PaymentMethod.PIX,
        confirm_payment_now=False,
        note='Cobranca criada na reativacao da matricula.',
        amount=new_enrollment.plan.price,
        reference='',
        billing_strategy='single',
        installment_total=1,
        recurrence_cycles=1,
    )
    return new_enrollment