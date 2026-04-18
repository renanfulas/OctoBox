import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder
from django.test import TestCase

from quick_sales.facade import run_quick_sale_create, run_quick_sale_match, run_quick_sale_memory_snapshot
from quick_sales.models import QuickProductAlias, QuickProductTemplate, QuickSaleResolutionMode
from quick_sales.services.matching import normalize_quick_product_name
from students.models import Student


class QuickSalesWave3Tests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='quick-sales-wave3-owner',
            password='CodexTemp!2026',
        )
        self.student = Student.objects.create(
            full_name='Aluno Quick Sale Wave 3',
            phone='5511990000002',
            email='quick.sale.wave3@example.com',
        )

    def test_normalize_quick_product_name_removes_accents_and_noise(self):
        self.assertEqual(normalize_quick_product_name('  ÁGUA   com gás!! '), 'agua com gas')

    def test_create_quick_sale_uses_exact_alias_match(self):
        template = QuickProductTemplate.objects.create(
            name='Barra de cereal',
            normalized_name='barra de cereal',
            default_unit_price=Decimal('8.00'),
        )
        QuickProductAlias.objects.create(
            template=template,
            alias_name='Barra cereal',
            normalized_alias_name='barra cereal',
        )

        sale = run_quick_sale_create(
            actor=self.user,
            student=self.student,
            payload={
                'description': 'barra cereal',
                'amount': Decimal('8.00'),
                'method': 'pix',
                'reference': '',
                'notes': '',
            },
        )

        self.assertEqual(sale.template_id, template.id)
        self.assertEqual(sale.resolution_mode, QuickSaleResolutionMode.EXACT_ALIAS)
        self.assertEqual(sale.normalized_description, 'barra de cereal')

    def test_match_snapshot_returns_fuzzy_suggestion_for_close_name(self):
        QuickProductTemplate.objects.create(
            name='Agua',
            normalized_name='agua',
            default_unit_price=Decimal('4.00'),
            usage_count=10,
        )

        snapshot = run_quick_sale_match(raw_query='aguaz')

        self.assertEqual(snapshot['normalized_name'], 'aguaz')
        self.assertEqual(snapshot['resolution_mode'], QuickSaleResolutionMode.MANUAL)
        self.assertEqual(snapshot['suggestions'][0]['label'], 'Agua')

    def test_repeated_sales_promote_pattern_to_template(self):
        for _ in range(3):
            run_quick_sale_create(
                actor=self.user,
                student=self.student,
                payload={
                    'description': 'Barra de cereal',
                    'amount': Decimal('5.00'),
                    'method': 'cash',
                    'reference': '',
                    'notes': '',
                },
            )

        template = QuickProductTemplate.objects.get(normalized_name='barra de cereal')
        self.assertEqual(template.default_unit_price, Decimal('5.00'))
        self.assertEqual(template.usage_count, 3)

    def test_memory_snapshot_is_json_serializable_and_exposes_recent_and_templates(self):
        for description, amount in [('Agua', Decimal('4.00')), ('Agua', Decimal('4.00')), ('Barra de cereal', Decimal('5.00')), ('Barra de cereal', Decimal('5.00')), ('Barra de cereal', Decimal('5.00'))]:
            run_quick_sale_create(
                actor=self.user,
                student=self.student,
                payload={
                    'description': description,
                    'amount': amount,
                    'method': 'pix',
                    'reference': '',
                    'notes': '',
                },
            )

        snapshot = run_quick_sale_memory_snapshot(student_id=self.student.id, query='barra cereal')
        encoded = json.dumps(snapshot, cls=DjangoJSONEncoder)

        self.assertIn('recent', snapshot)
        self.assertIn('templates', snapshot)
        self.assertEqual(snapshot['templates'][0]['label'], 'Barra de cereal')
        self.assertTrue(snapshot['recent'])
        self.assertIn('Barra de cereal', encoded)
