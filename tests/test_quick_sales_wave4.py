from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from access.roles import ROLE_OWNER
from quick_sales.forms import QuickSaleManagementForm
from quick_sales.models import QuickProductTemplate, QuickSale, QuickSaleStatus
from students.models import Student


class QuickSalesWave4Tests(TestCase):
    def setUp(self):
        call_command('bootstrap_roles')
        self.user = get_user_model().objects.create_user(
            username='quick-sales-wave4-owner',
            password='CodexTemp!2026',
        )
        self.user.groups.add(Group.objects.get(name=ROLE_OWNER))
        self.client.force_login(self.user)
        self.student = Student.objects.create(
            full_name='Aluno Quick Sale Wave 4',
            phone='5511990000004',
            email='quick.sale.wave4@example.com',
        )

    def test_quick_sale_drawer_returns_fragment_payload(self):
        response = self.client.get(
            reverse('student-quick-sale-drawer', args=[self.student.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'success')
        self.assertIn('quick_sales', payload['fragments'])
        self.assertIn('student-quick-sale-form', payload['fragments']['quick_sales'])
        self.assertIn('Historico discreto', payload['fragments']['quick_sales'])

    def test_quick_sale_management_form_limits_amount_to_three_integer_digits(self):
        form = QuickSaleManagementForm(
            data={
                'description': 'Agua',
                'amount': '1000,00',
                'method': 'pix',
                'reference': '',
                'notes': '',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('O valor maximo para pagamento rapido e R$ 999,99.', form.errors['amount'])

    def test_quick_sale_suggestions_return_memory_snapshot(self):
        QuickProductTemplate.objects.create(
            name='Agua',
            normalized_name='agua',
            default_unit_price=Decimal('4.00'),
            usage_count=5,
        )

        response = self.client.get(
            reverse('student-quick-sale-suggestions', args=[self.student.id]),
            {'q': 'agua'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'success')
        self.assertIn('memory', payload)
        self.assertEqual(payload['memory']['normalized_query'], 'agua')
        self.assertEqual(payload['memory']['match']['resolved_template_label'], 'Agua')
        self.assertEqual(payload['memory']['match']['resolved_template_unit_price'], '4.00')

    def test_quick_sale_action_creates_sale_and_returns_updated_fragments(self):
        response = self.client.post(
            reverse('student-quick-sale-action', args=[self.student.id]),
            data={
                'action': 'create-quick-sale',
                'template_id': '',
                'description': 'Barra de cereal',
                'amount': '5,00',
                'method': 'pix',
                'reference': 'BALCAO-001',
                'notes': 'Venda teste',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'success')
        self.assertEqual(QuickSale.objects.filter(student=self.student).count(), 1)

        sale = QuickSale.objects.get(student=self.student)
        self.assertEqual(sale.resolved_description, 'Barra de cereal')
        self.assertEqual(sale.unit_price, Decimal('5.00'))
        self.assertIn('quick_sales', payload['fragments'])
        self.assertIn('Barra de cereal', payload['fragments']['quick_sales'])

    def test_quick_sale_drawer_shows_discreet_history(self):
        QuickSale.objects.create(
            student=self.student,
            typed_description='Agua',
            normalized_description='agua',
            resolved_description='Agua',
            quantity=1,
            unit_price=Decimal('4.00'),
            total_amount=Decimal('4.00'),
            payment_method='pix',
            status=QuickSaleStatus.PAID,
        )

        response = self.client.get(
            reverse('student-quick-sale-drawer', args=[self.student.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('Historico discreto', payload['fragments']['quick_sales'])
        self.assertIn('Cancelar', payload['fragments']['quick_sales'])
        self.assertIn('Estornar', payload['fragments']['quick_sales'])

    def test_quick_sale_action_can_cancel_from_interface_flow(self):
        sale = QuickSale.objects.create(
            student=self.student,
            typed_description='Agua',
            normalized_description='agua',
            resolved_description='Agua',
            quantity=1,
            unit_price=Decimal('4.00'),
            total_amount=Decimal('4.00'),
            payment_method='pix',
            status=QuickSaleStatus.PAID,
        )

        response = self.client.post(
            reverse('student-quick-sale-action', args=[self.student.id]),
            data={
                'quick_sale_id': sale.id,
                'action': 'cancel-quick-sale',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        sale.refresh_from_db()
        self.assertEqual(sale.status, QuickSaleStatus.CANCELED)

    def test_quick_sale_action_can_refund_from_interface_flow(self):
        sale = QuickSale.objects.create(
            student=self.student,
            typed_description='Barra',
            normalized_description='barra',
            resolved_description='Barra',
            quantity=1,
            unit_price=Decimal('5.00'),
            total_amount=Decimal('5.00'),
            payment_method='cash',
            status=QuickSaleStatus.PAID,
        )

        response = self.client.post(
            reverse('student-quick-sale-action', args=[self.student.id]),
            data={
                'quick_sale_id': sale.id,
                'action': 'refund-quick-sale',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        sale.refresh_from_db()
        self.assertEqual(sale.status, QuickSaleStatus.REFUNDED)
