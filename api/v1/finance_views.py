"""
API views for the Finance module.
"""
import json
from datetime import timedelta

from django.db import transaction
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from catalog.forms import EnrollmentManagementForm, PaymentManagementForm
from catalog.student_queries import build_student_financial_snapshot
from students.models import Student
from finance.models import PaymentStatus, EnrollmentStatus


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
    page = _build_financial_fragment_page(student)
    context = {'page': page}
    return {
        'id_card': render_to_string('includes/catalog/student_form/financial/financial_overview_id_card.html', context),
        'kpis': render_to_string('includes/catalog/student_form/financial/financial_overview_kpis.html', context),
        'ledger': render_to_string('includes/catalog/student_form/financial/stripe_elite_ledger.html', context),
        'management': render_to_string('includes/catalog/student_form/financial/billing_console.html', context),
        'checkout': render_to_string('includes/catalog/student_form/financial/financial_overview_payment_management.html', context),
        'enrollment': render_to_string('includes/catalog/student_form/financial/financial_overview_enrollment_management.html', context),
    }

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

                # 2. Shift Pending Payments
                pending_payments = student.payments.filter(status=PaymentStatus.PENDING)
                for payment in pending_payments:
                    payment.due_date = payment.due_date + timedelta(days=days)
                    payment.save()

                return JsonResponse({
                    'status': 'success',
                    'message': f'Aluno {student.full_name} congelado por {days} dias com sucesso.',
                    'fragments': _render_financial_fragments(request, student),
                })

        except Student.DoesNotExist:
            return JsonResponse({'error': 'Student not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
