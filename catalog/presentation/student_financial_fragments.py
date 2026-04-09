"""
ARQUIVO: montagem compartilhada dos fragmentos financeiros da ficha do aluno.

POR QUE ELE EXISTE:
- evita duplicar a montagem do workspace financeiro entre views HTML e endpoints de mutacao.
- garante que checkout, vinculo, KPIs, ledger e cards leiam do mesmo snapshot recomposto.

O QUE ESTE ARQUIVO FAZ:
1. monta os forms contextuais de pagamento e matricula.
2. monta o page payload minimo para os templates do workspace financeiro.
3. renderiza os fragmentos principais para recomposicao parcial da superficie.

PONTOS CRITICOS:
- toda mudanca aqui afeta recomposicao parcial da ficha financeira.
- o pagamento contextual precisa sempre pertencer ao aluno correto.
"""

from django.template.loader import render_to_string
from django.utils import timezone

from catalog.forms import EnrollmentManagementForm, PaymentManagementForm
from catalog.student_queries import build_student_financial_snapshot


def resolve_student_payment_selection_id(form):
    if not form:
        return None

    instance = getattr(form, 'instance', None)
    if instance and getattr(instance, 'pk', None):
        return instance.pk

    try:
        return form['payment_id'].value() or None
    except Exception:
        return None


def build_student_payment_management_form(student, payment=None):
    latest_payment = payment or student.payments.order_by('-due_date', '-created_at').first()
    if latest_payment is None:
        return PaymentManagementForm(
            initial={
                'amount': '',
                'due_date': timezone.localdate().strftime('%d/%m/%Y'),
            }
        )

    return PaymentManagementForm(
        instance=latest_payment,
        initial={
            'payment_id': latest_payment.id,
            'amount': latest_payment.amount,
            'due_date': latest_payment.due_date,
            'method': latest_payment.method,
            'reference': latest_payment.reference,
            'notes': latest_payment.notes,
        },
    )


def build_student_enrollment_management_form(student):
    latest_enrollment = student.enrollments.order_by('-start_date', '-created_at').first()
    if latest_enrollment is None:
        return None

    return EnrollmentManagementForm(
        initial={
            'enrollment_id': latest_enrollment.id,
            'action_date': timezone.localdate(),
        }
    )


def build_student_financial_fragment_page(student, *, selected_payment=None):
    financial_overview = build_student_financial_snapshot(student)
    payment_management_form = build_student_payment_management_form(student, payment=selected_payment)
    return {
        'data': {
            'student_object': student,
            'financial_overview': financial_overview,
            'payment_management_form': payment_management_form,
            'selected_payment_id': resolve_student_payment_selection_id(payment_management_form),
            'enrollment_management_form': build_student_enrollment_management_form(student),
        }
    }


def render_student_financial_fragments(student, *, request=None, selected_payment=None):
    page = build_student_financial_fragment_page(student, selected_payment=selected_payment)
    context = {'page': page}
    render_kwargs = {'context': context}
    if request is not None:
        render_kwargs['request'] = request

    return {
        'header': render_to_string('includes/catalog/student_page/student_page_header.html', **render_kwargs),
        'payments_summary': render_to_string('includes/catalog/student_page/student_page_payments_summary.html', **render_kwargs),
        'quick_payments_summary': render_to_string('catalog/includes/student/student_quick_financial_summary.html', **render_kwargs),
        'id_card': render_to_string('includes/catalog/student_form/financial/financial_overview_id_card.html', **render_kwargs),
        'kpis': render_to_string('includes/catalog/student_form/financial/financial_overview_kpis.html', **render_kwargs),
        'ledger': render_to_string('includes/catalog/student_page/student_page_payments_history.html', **render_kwargs),
        'quick_ledger': render_to_string('catalog/includes/student/student_quick_financial_history.html', **render_kwargs),
        'management': '',
        'checkout': render_to_string('includes/catalog/student_form/financial/financial_overview_payment_management.html', **render_kwargs),
        'enrollment': render_to_string('includes/catalog/student_form/financial/financial_overview_enrollment_management.html', **render_kwargs),
    }


__all__ = [
    'build_student_enrollment_management_form',
    'build_student_financial_fragment_page',
    'build_student_payment_management_form',
    'render_student_financial_fragments',
    'resolve_student_payment_selection_id',
]
