"""
ARQUIVO: testes da trilha de auditoria.

POR QUE ELE EXISTE:
- Garante que autenticação e admin deixem rastros úteis para integridade e investigação.

O QUE ESTE ARQUIVO FAZ:
1. Testa auditoria de login.
2. Testa auditoria de logout.
3. Testa auditoria de alteração financeira feita no admin.

PONTOS CRITICOS:
- Se estes testes falharem, o sistema pode continuar funcionando sem rastreabilidade adequada.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from auditing.models import AuditEvent
from finance.models import Payment, PaymentStatus
from students.models import Student


class AuditTrailTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='auditor-user',
            email='audit@example.com',
            password='senha-forte-123',
        )
        self.superuser = user_model.objects.create_superuser(
            username='audit-admin',
            email='audit-admin@example.com',
            password='senha-forte-123',
        )
        self.student = Student.objects.create(full_name='Aluno Financeiro', phone='5511911111111')
        self.payment = Payment.objects.create(
            student=self.student,
            due_date='2026-03-20',
            amount='199.90',
            status=PaymentStatus.PENDING,
        )

    def test_login_creates_audit_event(self):
        response = self.client.post(
            reverse('login'),
            data={'username': 'auditor-user', 'password': 'senha-forte-123'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(AuditEvent.objects.filter(action='user_login', actor=self.user).exists())

    def test_logout_creates_audit_event(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('logout'))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(AuditEvent.objects.filter(action='user_logout', actor=self.user).exists())

    def test_admin_payment_change_creates_financial_audit_event(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse('admin:boxcore_payment_change', args=[self.payment.id]),
            data={
                'student': self.student.id,
                'enrollment': '',
                'due_date': '2026-03-20',
                'paid_at_0': '2026-03-18',
                'paid_at_1': '10:30:00',
                'amount': '249.90',
                'status': PaymentStatus.PAID,
                'method': 'pix',
                'reference': 'PIX-2026-03',
                'notes': 'Pagamento confirmado no admin.',
                'version': self.payment.version,
                '_save': 'Salvar',
            },
        )

        self.assertEqual(response.status_code, 302)
        event = AuditEvent.objects.filter(action='admin_change_payment', actor=self.superuser).latest('created_at')
        self.assertEqual(event.target_id, str(self.payment.id))
        self.assertTrue(event.metadata.get('is_financial'))
        self.assertIn('status', event.metadata.get('changed_fields', []))
        self.assertIn('amount', event.metadata.get('changed_fields', []))
