"""
API views for the Onboarding module.
"""
import json
from django.db import transaction
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from onboarding.models import StudentIntake, IntakeStatus
from students.models import Student
from finance.models import MembershipPlan, Enrollment, Payment, EnrollmentStatus, PaymentMethod, PaymentStatus
from integrations.stripe.services import create_checkout_session
from django.utils import timezone

class ExpressConvertView(LoginRequiredMixin, View):
    """
    Converte um Intake em Aluno + Matricula + Pagamento em uma unica transacao.
    """
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            intake_id = data.get('intake_id')
            plan_id = data.get('plan_id')
            payment_method = data.get('payment_method', 'pix')

            if not intake_id or not plan_id:
                return JsonResponse({'error': 'Missing intake_id or plan_id'}, status=400)

            with transaction.atomic():
                # 1. Get Intake
                intake = StudentIntake.objects.select_for_update().get(pk=intake_id)
                if intake.linked_student_id:
                    return JsonResponse({'error': 'Intake already converted'}, status=400)

                # 2. Get Plan
                plan = MembershipPlan.objects.get(pk=plan_id)

                # 3. Create Student
                student = Student.objects.create(
                    full_name=intake.full_name,
                    phone=intake.phone,
                    email=intake.email or '',
                    status='active', # Default for new converted students
                )

                # 4. Create Enrollment
                enrollment = Enrollment.objects.create(
                    student=student,
                    plan=plan,
                    start_date=timezone.localdate(),
                    status=EnrollmentStatus.ACTIVE,
                )

                # 5. Create Payment
                payment = Payment.objects.create(
                    student=student,
                    enrollment=enrollment,
                    due_date=timezone.localdate(),
                    amount=plan.price,
                    status=PaymentStatus.PENDING,
                    method=PaymentMethod.PIX if payment_method == 'pix' else PaymentMethod.OTHER
                )

                # 6. Mark Intake as Match and Link Student
                intake.status = IntakeStatus.MATCHED
                intake.linked_student = student
                intake.save()

                # 7. Generate Stripe URL if PIX (Link)
                payment_url = None
                if payment_method == 'pix':
                     payment_url = create_checkout_session(payment, request)

                return JsonResponse({
                    'status': 'success',
                    'message': f'Aluno {student.full_name} matriculado com sucesso!',
                    'student_id': student.id,
                    'payment_url': payment_url
                })

        except StudentIntake.DoesNotExist:
            return JsonResponse({'error': 'Intake not found'}, status=404)
        except MembershipPlan.DoesNotExist:
            return JsonResponse({'error': 'Plan not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
