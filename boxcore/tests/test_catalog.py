"""
ARQUIVO: testes das paginas visuais de catalogo.

POR QUE ELE EXISTE:
- Protege a camada leve de alunos, grade e operacao comercial contra regressao.

O QUE ESTE ARQUIVO FAZ:
1. Testa renderizacao da pagina de alunos e da grade de aulas.
2. Testa criacao e edicao de aluno pelo fluxo leve.
3. Testa conversao de intake, geracao de cobranca e mudanca de plano.
4. Testa acoes diretas de pagamento e matricula.

PONTOS CRITICOS:
- Se estes testes quebrarem, a operacao diaria perde o fluxo principal fora do admin.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from boxcore.models import (
    AuditEvent,
    ClassSession,
    Enrollment,
    EnrollmentStatus,
    MembershipPlan,
    Payment,
    PaymentMethod,
    PaymentStatus,
    Student,
    StudentIntake,
)


class CatalogViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='catalog-owner',
            email='catalog-owner@example.com',
            password='senha-forte-123',
        )
        self.student = Student.objects.create(full_name='Bruna Costa', phone='5511988888888')
        self.plan = MembershipPlan.objects.create(name='Cross Prime', price='289.90')
        self.plan_plus = MembershipPlan.objects.create(name='Cross Black', price='349.90')
        self.enrollment = Enrollment.objects.create(student=self.student, plan=self.plan)
        Payment.objects.create(student=self.student, enrollment=self.enrollment, due_date=timezone.localdate(), amount='289.90')
        self.intake = StudentIntake.objects.create(full_name='Lead Bruna', phone='5511970000000', email='lead@example.com')
        ClassSession.objects.create(title='WOD 18h', scheduled_at=timezone.now())

    def test_student_directory_renders(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('student-directory'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alunos')
        self.assertContains(response, 'Bruna Costa')
        self.assertContains(response, 'WhatsApp')
        self.assertContains(response, 'Cadastrar aluno com fluxo leve')
        self.assertContains(response, 'Fila de entrada provisoria pronta para conversao')

    def test_class_grid_renders(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('class-grid'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Grade de aulas')
        self.assertContains(response, 'WOD 18h')

    def test_student_quick_create_flow_creates_student(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('student-quick-create'),
            data={
                'full_name': 'Mateus Oliveira',
                'phone': '5511977777777',
                'status': 'active',
                'email': 'mateus@example.com',
                'gender': 'male',
                'birth_date': '',
                'health_issue_status': 'no',
                'cpf': '123.456.789-00',
                'notes': '',
                'selected_plan': self.plan.id,
                'enrollment_status': 'active',
                'payment_method': PaymentMethod.PIX,
                'confirm_payment_now': 'True',
                'payment_due_date': str(timezone.localdate()),
                'billing_strategy': 'single',
                'installment_total': 1,
                'recurrence_cycles': 3,
                'intake_record': self.intake.id,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Student.objects.filter(full_name='Mateus Oliveira').exists())
        created_student = Student.objects.get(full_name='Mateus Oliveira')
        self.assertEqual(created_student.cpf, '123.456.789-00')
        self.assertTrue(created_student.enrollments.filter(plan=self.plan, status='active').exists())
        created_payment = created_student.payments.latest('created_at')
        self.assertEqual(created_payment.method, PaymentMethod.PIX)
        self.assertEqual(created_payment.status, PaymentStatus.PAID)
        self.intake.refresh_from_db()
        self.assertEqual(self.intake.linked_student, created_student)
        self.assertTrue(AuditEvent.objects.filter(action='student_quick_created').exists())
        self.assertTrue(AuditEvent.objects.filter(action='student_quick_payment_created').exists())
        self.assertTrue(AuditEvent.objects.filter(action='student_intake_converted').exists())

    def test_student_quick_update_flow_updates_student(self):
        self.client.force_login(self.user)
        student = Student.objects.get(full_name='Bruna Costa')

        response = self.client.post(
            reverse('student-quick-update', args=[student.id]),
            data={
                'full_name': 'Bruna Costa Lima',
                'phone': '5511988888888',
                'email': 'bruna@example.com',
                'status': 'active',
                'gender': 'female',
                'birth_date': '',
                'health_issue_status': 'yes',
                'cpf': '987.654.321-00',
                'notes': 'Lesao antiga no ombro esquerdo.',
                'selected_plan': self.plan_plus.id,
                'enrollment_status': 'active',
                'payment_method': PaymentMethod.CREDIT_CARD,
                'confirm_payment_now': 'False',
                'payment_due_date': str(timezone.localdate()),
                'billing_strategy': 'installments',
                'installment_total': 3,
                'recurrence_cycles': 1,
            },
        )

        self.assertEqual(response.status_code, 302)
        student.refresh_from_db()
        self.assertEqual(student.full_name, 'Bruna Costa Lima')
        self.assertEqual(student.gender, 'female')
        self.assertEqual(student.health_issue_status, 'yes')
        self.assertTrue(student.enrollments.filter(plan=self.plan_plus, status='active').exists())
        self.assertTrue(student.enrollments.filter(plan=self.plan, status='expired').exists())
        self.assertEqual(student.payments.filter(enrollment__plan=self.plan_plus).count(), 3)
        latest_payment = student.payments.filter(enrollment__plan=self.plan_plus).order_by('created_at').first()
        self.assertEqual(latest_payment.method, PaymentMethod.CREDIT_CARD)
        self.assertEqual(latest_payment.status, PaymentStatus.PENDING)
        self.assertTrue(AuditEvent.objects.filter(action='student_quick_updated').exists())
        self.assertTrue(AuditEvent.objects.filter(action='student_plan_changed').exists())

    def test_student_payment_action_marks_payment_as_paid(self):
        self.client.force_login(self.user)
        payment = self.student.payments.first()

        response = self.client.post(
            reverse('student-payment-action', args=[self.student.id]),
            data={
                'payment_id': payment.id,
                'amount': payment.amount,
                'due_date': str(payment.due_date),
                'method': payment.method,
                'reference': '',
                'notes': '',
                'action': 'mark-paid',
            },
        )

        self.assertEqual(response.status_code, 302)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PAID)

    def test_student_enrollment_action_can_cancel_and_reactivate(self):
        self.client.force_login(self.user)

        cancel_response = self.client.post(
            reverse('student-enrollment-action', args=[self.student.id]),
            data={
                'enrollment_id': self.enrollment.id,
                'action_date': str(timezone.localdate()),
                'reason': 'Mudanca de rotina.',
                'action': 'cancel-enrollment',
            },
        )
        self.assertEqual(cancel_response.status_code, 302)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, EnrollmentStatus.CANCELED)

        reactivate_response = self.client.post(
            reverse('student-enrollment-action', args=[self.student.id]),
            data={
                'enrollment_id': self.enrollment.id,
                'action_date': str(timezone.localdate()),
                'reason': 'Retorno ao box.',
                'action': 'reactivate-enrollment',
            },
        )
        self.assertEqual(reactivate_response.status_code, 302)
        self.assertEqual(self.student.enrollments.filter(status=EnrollmentStatus.ACTIVE).count(), 1)

    def test_student_update_page_shows_financial_overview(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('student-quick-update', args=[self.student.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Plano, status e tramite financeiro')
        self.assertContains(response, 'Cross Prime')
        self.assertContains(response, 'Historico financeiro recente')
        self.assertContains(response, 'Passo 4: plano e status comercial')
        self.assertContains(response, 'Passo 5: cobranca e confirmacao')
        self.assertContains(response, 'Gestao da cobranca atual')