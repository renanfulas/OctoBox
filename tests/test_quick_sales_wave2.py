from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from quick_sales.facade import run_quick_sale_cancel, run_quick_sale_create, run_quick_sale_refund
from quick_sales.forms import QuickSaleActionForm, QuickSaleManagementForm
from quick_sales.models import QuickProductTemplate, QuickSaleStatus
from students.models import Student


class QuickSalesWave2Tests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='quick-sales-owner',
            password='CodexTemp!2026',
        )
        self.student = Student.objects.create(
            full_name='Aluno Quick Sale',
            phone='5511990000001',
            email='quick.sale@example.com',
        )

    def test_management_form_normalizes_currency_input(self):
        form = QuickSaleManagementForm(
            data={
                'description': ' Barra  de cereal ',
                'amount': '5,00',
                'method': 'pix',
                'reference': '',
                'notes': '',
            }
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['description'], 'Barra de cereal')
        self.assertEqual(form.cleaned_data['amount'], Decimal('5.00'))

    def test_create_quick_sale_uses_template_snapshot_and_updates_usage(self):
        template = QuickProductTemplate.objects.create(
            name='Barra de cereal',
            normalized_name='barra de cereal',
            default_unit_price=Decimal('5.00'),
        )

        sale = run_quick_sale_create(
            actor=self.user,
            student=self.student,
            payload={
                'template_id': template.id,
                'description': 'barra cereal',
                'amount': Decimal('5.00'),
                'method': 'pix',
                'reference': 'BALCAO-001',
                'notes': 'Venda teste',
            },
        )

        template.refresh_from_db()
        self.assertEqual(sale.template_id, template.id)
        self.assertEqual(sale.resolved_description, 'Barra de cereal')
        self.assertEqual(sale.unit_price, Decimal('5.00'))
        self.assertEqual(sale.total_amount, Decimal('5.00'))
        self.assertEqual(template.usage_count, 1)

    def test_cancel_and_refund_quick_sale_change_status_without_removing_record(self):
        sale_to_cancel = run_quick_sale_create(
            actor=self.user,
            student=self.student,
            payload={
                'description': 'Agua',
                'amount': Decimal('4.00'),
                'method': 'cash',
                'reference': '',
                'notes': '',
            },
        )

        canceled = run_quick_sale_cancel(
            actor=self.user,
            student=self.student,
            quick_sale=sale_to_cancel,
            payload={'notes': 'Cancelado no balcao'},
        )
        self.assertEqual(canceled.status, QuickSaleStatus.CANCELED)

        sale_to_refund = run_quick_sale_create(
            actor=self.user,
            student=self.student,
            payload={
                'description': 'Energetico',
                'amount': Decimal('8.00'),
                'method': 'credit_card',
                'reference': '',
                'notes': '',
            },
        )
        refunded = run_quick_sale_refund(
            actor=self.user,
            student=self.student,
            quick_sale=sale_to_refund,
            payload={'notes': 'Estornado ao aluno'},
        )
        self.assertEqual(refunded.status, QuickSaleStatus.REFUNDED)
        self.assertEqual(type(refunded).objects.count(), 2)

    def test_status_actions_reject_invalid_transition(self):
        sale = run_quick_sale_create(
            actor=self.user,
            student=self.student,
            payload={
                'description': 'Agua',
                'amount': Decimal('4.00'),
                'method': 'cash',
                'reference': '',
                'notes': '',
            },
        )

        run_quick_sale_cancel(
            actor=self.user,
            student=self.student,
            quick_sale=sale,
            payload={'notes': 'Cancelado no balcao'},
        )

        with self.assertRaisesMessage(ValueError, 'Apenas vendas pagas podem ser estornadas.'):
            run_quick_sale_refund(
                actor=self.user,
                student=self.student,
                quick_sale=sale,
                payload={'notes': 'Tentativa invalida'},
            )

    def test_action_form_requires_sale_for_status_change(self):
        form = QuickSaleActionForm(data={'action': 'refund-quick-sale'})
        self.assertFalse(form.is_valid())
        self.assertIn('A venda rapida precisa ser informada para esta acao.', form.errors['__all__'])
