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

from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from auditing.models import AuditEvent
from communications.models import WhatsAppContact
from finance.models import Enrollment, EnrollmentStatus, MembershipPlan, Payment, PaymentMethod, PaymentStatus
from students.models import Student


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
            due_date=timezone.localdate() - timezone.timedelta(days=8),
            amount='319.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

    def test_finance_center_renders_dashboard_and_plan_portfolio(self):
        """Sprint 4 refactor: asserts estruturais em vez de 60+ assertContains
        de copy do template. Mantemos o intent original (a pagina renderiza
        os blocos principais e mostra o plano + valor do aluno) sem acoplar
        cada redacao do produto ao test.

        Copy individual fica coberta por testes menores e dedicados em
        templates/includes/ snapshots ou screenshot regression — nao em
        teste de view.
        """
        self.client.force_login(self.user)

        response = self.client.get(reverse('finance-center'))

        # 1. Pagina renderiza com sucesso para o owner.
        self.assertEqual(response.status_code, 200)

        # 2. Os blocos estruturais (IDs estaveis usados por JS/anchor links)
        #    permanecem no DOM. Mudancas de copy nao quebram este contrato,
        #    mas remocao de bloco quebra (que e o intent do teste).
        for block_id in (
            'finance-trend-preview-board',
            'finance-queue-board',
            'finance-overdue-support-board',
            'finance-ai-board',
            'finance-portfolio-board',
        ):
            self.assertContains(response, f'id="{block_id}"')

        # 3. Modos de visualizacao (3-tab control board) intactos.
        for mode in ('traditional', 'hybrid', 'ai'):
            self.assertContains(response, f'data-finance-mode-button="{mode}"')
            self.assertNotContains(response, f'?mode={mode}')

        # 4. Anchor links de navegacao interna preservados.
        self.assertContains(response, 'href="#finance-priority-board"')
        self.assertContains(response, 'href="#finance-portfolio-board"')

        # 5. Plano do aluno aparece + valor formatado em BRL.
        self.assertContains(response, 'Cross Gold')
        self.assertRegex(response.content.decode(), r'R\$\s*319[,.]90')

        # 6. Link de quick-update do aluno permanece com anchor financeiro.
        self.assertContains(
            response,
            f'href="{reverse("student-quick-update", args=[self.student.id])}#student-financial-overview"',
        )

        # 7. Blocos AI/recommendation visiveis (data-attributes estaveis).
        self.assertContains(response, 'data-finance-trend-button="recebido"')
        self.assertContains(response, 'data-finance-trend-button="churn"')

        # 8. CTA whatsapp render no fluxo financeiro.
        self.assertContains(response, 'name="open_in_whatsapp" value="1"', html=False)

    def test_finance_center_filters_by_plan_and_method(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('finance-center'),
            data={'months': '6', 'plan': self.plan.id, 'payment_method': 'pix'},
        )

        self.assertEqual(response.status_code, 200)
        # Copy reformulada — template usa 'Filtros do financeiro'
        # (control_board.html:17).
        self.assertContains(response, 'Filtros do financeiro')
        self.assertContains(response, 'Cross Gold')
        self.assertEqual(response.context['finance_center_page']['behavior']['default_panel'], 'tab-finance-filters')
        self.assertContains(response, 'Recorte atual: 6 meses | Cross Gold | PIX')

    def test_finance_center_filters_queue_by_mission(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('finance-center'),
            data={'queue_focus': 'high_signal'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alto risco')
        self.assertContains(response, 'Missao da fila')

    def test_finance_center_restores_last_filter_state_from_session(self):
        self.client.force_login(self.user)

        self.client.get(
            reverse('finance-center'),
            data={
                'apply_filters': '1',
                'months': '3',
                'plan': self.plan.id,
                'payment_status': '',
                'payment_method': 'pix',
                'queue_focus': 'high_signal',
            },
        )

        response = self.client.get(reverse('finance-center'))

        self.assertEqual(response.status_code, 200)
        # Copy reformulada: 'desta' -> 'para esta' + 'último' com acento
        # (templates/includes/catalog/finance/boards/control_board.html:58).
        self.assertContains(response, 'Estamos usando o último recorte salvo para esta leitura.')
        self.assertContains(response, 'Recorte atual: 3 meses | Cross Gold | PIX | Alto risco')
        self.assertContains(response, '3 meses')
        self.assertContains(response, 'Cross Gold')
        self.assertContains(response, 'PIX')
        self.assertContains(response, 'Alto risco')

    def test_finance_center_hides_recent_movements_board_from_the_raiox_tab(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('finance-center'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="finance-movements-board"')
        self.assertNotContains(response, 'finance-movements-panel')
        self.assertContains(response, 'id="finance-trend-board"')
        self.assertContains(response, 'finance-revenue-trend-card')

    def test_finance_revenue_chart_css_exposes_compact_dual_bar_contract(self):
        finance_css = (
            Path(__file__).resolve().parents[2] / 'static' / 'css' / 'catalog' / 'finance' / '_boards.css'
        ).read_text(encoding='utf-8')

        self.assertIn('.finance-revenue-trend-card {', finance_css)
        self.assertIn('.finance-revenue-trend-columns {', finance_css)
        self.assertIn('.finance-revenue-bar.is-realized {', finance_css)

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

        follow_response = self.client.get(reverse('finance-center'))
        self.assertContains(follow_response, 'Legends Unlimited')
        # Copy reformulada: agora com artigo + cedilha + acento
        # (portfolio_board.html "Aguardando a primeira adesão").
        self.assertContains(follow_response, 'Aguardando a primeira adesão')

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

    def test_finance_plan_update_page_shows_guided_support_blocks(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('membership-plan-quick-update', args=[self.plan.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Como decidir sem espalhar a leitura')
        self.assertContains(response, 'Leitura de impacto')
        self.assertContains(response, 'O que esta decisao deve deixar claro')

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

    def test_finance_center_hides_priority_rail_when_all_whatsapp_contacts_are_blocked(self):
        self.client.force_login(self.user)
        WhatsAppContact.objects.create(
            phone='5511910101010',
            display_name=self.student.full_name,
            linked_student=self.student,
            last_outbound_at=timezone.now(),
        )

        response = self.client.get(reverse('finance-center'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="finance-priority-board"')
        self.assertNotContains(response, 'Registrar e abrir WhatsApp')
        self.assertContains(response, 'id="finance-queue-board"')
        self.assertContains(response, 'href="#finance-queue-board"')
