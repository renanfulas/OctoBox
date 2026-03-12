"""
ARQUIVO: testes da central visual de financeiro.

POR QUE ELE EXISTE:
- Garante que a area financeira visual continue entregando leitura comercial, filtros, regua operacional e manutencao leve de planos.

O QUE ESTE ARQUIVO FAZ:
1. Testa renderizacao da pagina de financeiro.
2. Testa filtros por plano e metodo.
3. Testa cadastro rapido e edicao rapida de plano.
4. Testa a presenca da regua de cobranca e retencao.
5. Testa exportacoes CSV/PDF do financeiro.

PONTOS CRITICOS:
- Se estes testes quebrarem, o produto perde a principal leitura gerencial fora do admin.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from boxcore.models import AuditEvent, Enrollment, EnrollmentStatus, MembershipPlan, Payment, PaymentMethod, PaymentStatus, Student


class FinanceCenterTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='finance-owner',
            email='finance-owner@example.com',
            password='senha-forte-123',
        )
        self.student = Student.objects.create(full_name='Paula Nunes', phone='5511910101010', status='active')
        self.plan = MembershipPlan.objects.create(name='Cross Gold', price='319.90', billing_cycle='monthly')
        self.enrollment = Enrollment.objects.create(student=self.student, plan=self.plan)
        Payment.objects.create(
            student=self.student,
            enrollment=self.enrollment,
            due_date=timezone.localdate(),
            amount='319.90',
            status=PaymentStatus.PAID,
            method=PaymentMethod.PIX,
        )
        previous_month = timezone.localdate().replace(day=1) - timezone.timedelta(days=1)
        previous_month_start = previous_month.replace(day=1)
        former_student = Student.objects.create(full_name='Rafa Souza', phone='5511910101011', status='inactive')
        former_plan = MembershipPlan.objects.create(name='Starter', price='199.90', billing_cycle='monthly')
        former_enrollment = Enrollment.objects.create(
            student=former_student,
            plan=former_plan,
            start_date=previous_month_start,
            status=EnrollmentStatus.CANCELED,
        )
        former_enrollment.updated_at = timezone.make_aware(timezone.datetime.combine(previous_month_start, timezone.datetime.min.time()))
        former_enrollment.save(update_fields=['updated_at'])
        Payment.objects.create(
            student=former_student,
            enrollment=former_enrollment,
            due_date=previous_month_start,
            amount='199.90',
            status=PaymentStatus.PAID,
            method=PaymentMethod.PIX,
        )

        self.overdue_payment = Payment.objects.create(
            student=self.student,
            enrollment=self.enrollment,
            due_date=timezone.localdate() - timezone.timedelta(days=6),
            amount='319.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

    def test_finance_center_renders_dashboard_and_plan_portfolio(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('finance-center'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Financeiro')
        self.assertContains(response, 'Cross Gold')
        self.assertContains(response, 'Cadastre um plano que depois conversa com aluno, matricula e pagamento')
        self.assertContains(response, 'Tendência mensal')
        self.assertContains(response, 'Ativações x cancelamentos')
        self.assertContains(response, 'Régua de cobrança e retenção')
        self.assertContains(response, 'Leitura executiva do mix')
        self.assertContains(response, 'Registrar contato no WhatsApp')
        self.assertRegex(response.content.decode(), r'R\$\s*319[,.]90')

    def test_finance_center_filters_by_plan_and_method(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('finance-center'),
            data={'months': '6', 'plan': self.plan.id, 'payment_method': 'pix'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Filtros da leitura financeira')
        self.assertContains(response, 'Cross Gold')

    def test_finance_center_can_create_plan(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('finance-center'),
            data={
                'name': 'Legends Unlimited',
                'price': '429.90',
                'billing_cycle': 'monthly',
                'sessions_per_week': 5,
                'description': 'Plano premium com prioridade de acompanhamento.',
                'active': 'True',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(MembershipPlan.objects.filter(name='Legends Unlimited').exists())
        self.assertTrue(AuditEvent.objects.filter(action='membership_plan_quick_created').exists())

    def test_finance_center_can_update_plan(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('membership-plan-quick-update', args=[self.plan.id]),
            data={
                'name': 'Cross Gold Plus',
                'price': '339.90',
                'billing_cycle': 'monthly',
                'sessions_per_week': 4,
                'description': 'Plano reposicionado para crescimento de ticket.',
                'active': 'True',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.name, 'Cross Gold Plus')
        self.assertEqual(str(self.plan.price), '339.90')
        self.assertTrue(AuditEvent.objects.filter(action='membership_plan_quick_updated').exists())

    def test_finance_center_can_export_csv(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('finance-report-export', args=['csv']))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('Paula Nunes', response.content.decode())

    def test_finance_center_can_export_pdf(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('finance-report-export', args=['pdf']))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')