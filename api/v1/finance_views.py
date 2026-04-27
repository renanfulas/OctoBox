"""
ARQUIVO: views da capacidade financeira na API v1.

POR QUE ELE EXISTE:
- Reune endpoints financeiros versionados sem misturar manifesto, integracao ou jobs.

O QUE ESTE ARQUIVO FAZ:
1. expõe operacoes financeiras controladas na API.
2. concentra fluxos HTTP que pertencem ao dominio financeiro.

PONTOS CRITICOS:
- endpoints daqui devem continuar pequenos e previsiveis.
"""
import json
from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from api.v1.bulk_views import GenericBulkActionView
from catalog.forms import EnrollmentManagementForm, PaymentManagementForm
from catalog.presentation.student_financial_fragments import render_student_financial_fragments
from catalog.student_queries import build_student_financial_snapshot
from finance.models import EnrollmentStatus, Payment, PaymentStatus
from integrations.stripe.services import create_checkout_session
from students.models import Student


def _build_payment_management_form(student):
    latest_payment = student.payments.order_by('-due_date', '-created_at').first()
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


def _build_enrollment_management_form(student):
    latest_enrollment = student.enrollments.order_by('-start_date', '-created_at').first()
    if latest_enrollment is None:
        return None

    return EnrollmentManagementForm(
        initial={
            'enrollment_id': latest_enrollment.id,
            'action_date': timezone.localdate(),
        }
    )


def _build_financial_fragment_page(student):
    financial_overview = build_student_financial_snapshot(student)
    return {
        'data': {
            'student_object': student,
            'financial_overview': financial_overview,
            'payment_management_form': _build_payment_management_form(student),
            'enrollment_management_form': _build_enrollment_management_form(student),
        }
    }


def _render_financial_fragments(request, student):
    fragments = render_student_financial_fragments(student, request=request)
    fragments['ledger'] = (
        '<div class="student-financial-ledger">'
        f"{fragments.get('ledger', '')}"
        '</div>'
    )
    if not fragments.get('management'):
        fragments['management'] = (
            '<div id="student-payment-management-root">'
            f"{fragments.get('checkout', '')}"
            '</div>'
    )
    return fragments


class PaymentLinkView(LoginRequiredMixin, View):
    """Gera um link de checkout do Stripe para compartilhamento manual."""

    def get(self, request, payment_id, *args, **kwargs):
        payment = Payment.objects.filter(pk=payment_id).first()
        if not payment:
            return JsonResponse({'error': 'Payment not found'}, status=404)

        if payment.status == PaymentStatus.PAID:
            return JsonResponse({'error': 'Payment already paid'}, status=400)

        try:
            url = create_checkout_session(payment, request)
            return JsonResponse({'url': url})
        except Exception as exc:
            return JsonResponse({'error': str(exc)}, status=500)

class StudentFreezeView(LoginRequiredMixin, View):
    """
    "Congela" um aluno por X dias, empurrando o fim da matricula e os vencimentos futuros.
    """
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            student_id = data.get('student_id')
            days = int(data.get('days', 0))

            if not student_id or days <= 0:
                return JsonResponse({'error': 'Invalid student_id or days'}, status=400)

            with transaction.atomic():
                student = Student.objects.get(pk=student_id)
                
                # 1. Update Active Enrollment
                enrollment = student.enrollments.filter(status=EnrollmentStatus.ACTIVE).first()
                if enrollment and enrollment.end_date:
                    enrollment.end_date = enrollment.end_date + timedelta(days=days)
                    enrollment.save()

                # 2. Shift Pending Payments — single UPDATE avoids partial-commit on N saves
                student.payments.filter(status=PaymentStatus.PENDING).update(
                    due_date=F('due_date') + timedelta(days=days)
                )

                return JsonResponse({
                    'status': 'success',
                    'message': f'Aluno {student.full_name} congelado por {days} dias com sucesso.',
                    'fragments': _render_financial_fragments(request, student),
                })

        except Student.DoesNotExist:
            return JsonResponse({'error': 'Student not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class PaymentBulkActionView(GenericBulkActionView):
    """
    Partial-commit bulk mutations for payments.
    Each item runs in its own savepoint; failures on individual payments
    do not roll back successful ones. Returns HTTP 207 when partial.

    Supported actions: mark_paid, mark_cancelled.
    """

    def perform_action(self, item_id, action, user):
        payment = Payment.objects.get(pk=item_id)
        if action == 'mark_paid':
            payment.status = PaymentStatus.PAID
            payment.save()
        elif action == 'mark_cancelled':
            payment.status = PaymentStatus.CANCELLED
            payment.save()
        else:
            raise ValueError(f'Acao desconhecida: {action}')
