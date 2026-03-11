"""
ARQUIVO: workflows do cadastro leve de aluno.

POR QUE ELE EXISTE:
- Tira das views a sequencia de salvamento, sincronizacao comercial e auditoria do fluxo leve de aluno.

O QUE ESTE ARQUIVO FAZ:
1. Executa o create workflow do aluno com intake, matricula e cobranca inicial.
2. Executa o update workflow com trilha de mudancas, troca de plano e auditoria.
3. Centraliza o payload comercial que alimenta os services de matricula e intake.

PONTOS CRITICOS:
- Qualquer regressao aqui afeta o fluxo principal de cadastro e manutencao comercial do produto.
"""

from decimal import Decimal

from django.utils import timezone

from boxcore.auditing import log_audit_event
from boxcore.models import EnrollmentStatus, PaymentMethod

from .enrollments import sync_student_enrollment
from .intakes import sync_student_intake


def build_student_workflow_payload(*, student, form):
    selected_plan = form.cleaned_data.get('selected_plan')
    return {
        'student': student,
        'selected_plan': selected_plan,
        'enrollment_status': form.cleaned_data.get('enrollment_status') or EnrollmentStatus.PENDING,
        'due_date': form.cleaned_data.get('payment_due_date') or timezone.localdate(),
        'payment_method': form.cleaned_data.get('payment_method') or PaymentMethod.PIX,
        'confirm_payment_now': bool(form.cleaned_data.get('confirm_payment_now')),
        'payment_reference': form.cleaned_data.get('payment_reference') or '',
        'billing_strategy': form.cleaned_data.get('billing_strategy') or 'single',
        'installment_total': form.cleaned_data.get('installment_total') or 1,
        'recurrence_cycles': form.cleaned_data.get('recurrence_cycles') or 1,
        'initial_payment_amount': form.cleaned_data.get('initial_payment_amount')
        or (selected_plan.price if selected_plan else Decimal('0.00')),
    }


def _sync_student_sales_flow(*, student, form, selected_intake=None):
    enrollment_sync = sync_student_enrollment(**build_student_workflow_payload(student=student, form=form))
    intake = sync_student_intake(student=student, intake=form.cleaned_data.get('intake_record') or selected_intake)
    return enrollment_sync, intake


build_student_flow_payload = build_student_workflow_payload


def run_student_quick_create_workflow(*, actor, form, selected_intake=None):
    student = form.save()
    enrollment_sync, intake = _sync_student_sales_flow(student=student, form=form, selected_intake=selected_intake)

    log_audit_event(
        actor=actor,
        action='student_quick_created',
        target=student,
        description='Aluno criado pela tela leve de cadastro.',
        metadata={
            'status': student.status,
            'enrollment_id': enrollment_sync['enrollment'].id if enrollment_sync['enrollment'] else None,
            'payment_id': enrollment_sync['payment'].id if enrollment_sync['payment'] else None,
            'movement': enrollment_sync['movement'],
            'intake_id': intake.id if intake else None,
        },
    )
    if enrollment_sync['payment'] is not None:
        log_audit_event(
            actor=actor,
            action='student_quick_payment_created',
            target=enrollment_sync['payment'],
            description='Primeira cobranca criada pela tela leve do aluno.',
            metadata={'status': enrollment_sync['payment'].status, 'method': enrollment_sync['payment'].method},
        )
    if intake is not None:
        log_audit_event(
            actor=actor,
            action='student_intake_converted',
            target=intake,
            description='Lead convertido em aluno pela tela leve.',
            metadata={'student_id': student.id},
        )

    return {
        'student': student,
        'enrollment_sync': enrollment_sync,
        'intake': intake,
    }


def run_student_quick_update_workflow(*, actor, form, changed_fields, selected_intake=None):
    student = form.save()
    enrollment_sync, intake = _sync_student_sales_flow(student=student, form=form, selected_intake=selected_intake)

    log_audit_event(
        actor=actor,
        action='student_quick_updated',
        target=student,
        description='Aluno alterado pela tela leve de cadastro.',
        metadata={
            'changed_fields': changed_fields,
            'enrollment_id': enrollment_sync['enrollment'].id if enrollment_sync['enrollment'] else None,
            'payment_id': enrollment_sync['payment'].id if enrollment_sync['payment'] else None,
            'movement': enrollment_sync['movement'],
            'intake_id': intake.id if intake else None,
        },
    )
    if enrollment_sync['movement'] in ('upgrade', 'downgrade', 'troca de plano'):
        log_audit_event(
            actor=actor,
            action='student_plan_changed',
            target=enrollment_sync['enrollment'],
            description='Troca de plano registrada pela tela leve do aluno.',
            metadata={'movement': enrollment_sync['movement']},
        )
    if enrollment_sync['payment'] is not None:
        log_audit_event(
            actor=actor,
            action='student_quick_payment_created',
            target=enrollment_sync['payment'],
            description='Cobranca criada ou confirmada pela tela leve do aluno.',
            metadata={'status': enrollment_sync['payment'].status, 'method': enrollment_sync['payment'].method},
        )
    if intake is not None:
        log_audit_event(
            actor=actor,
            action='student_intake_converted',
            target=intake,
            description='Lead vinculado ao aluno pela tela leve.',
            metadata={'student_id': student.id},
        )

    return {
        'student': student,
        'enrollment_sync': enrollment_sync,
        'intake': intake,
    }