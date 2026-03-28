"""
API views for the Finance module.
"""
import json
from django.db import transaction
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from datetime import timedelta

from students.models import Student
from finance.models import Enrollment, Payment, PaymentStatus, EnrollmentStatus

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
                    'message': f'Aluno {student.full_name} congelado por {days} dias com sucesso.'
                })

        except Student.DoesNotExist:
            return JsonResponse({'error': 'Student not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
