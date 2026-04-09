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
        self.client.force_login(self.user)

        response = self.client.get(reverse('finance-center'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Financeiro')
        self.assertContains(response, 'Cross Gold')
        self.assertContains(response, 'Resumo do Recorte Ativo')
        self.assertContains(response, 'Handoff de cobranca')
        self.assertContains(response, 'Primeiro agir, depois analisar')
        self.assertContains(response, 'Separar disparo, prioridade e apoio')
        self.assertContains(response, 'Acoes prontas')
        self.assertContains(response, 'Casos semiassistidos prontos para disparo.')
        self.assertContains(response, 'Fila do turno')
        self.assertContains(response, 'Pendencias abertas')
        self.assertContains(response, 'Churn e crescimento')
        self.assertContains(response, 'Placar de follow-up')
        self.assertContains(response, 'Melhor jogada agora')
        self.assertContains(response, 'Aderencia ao turno')
        self.assertContains(response, 'Outcome de quem seguiu')
        self.assertContains(response, 'Outcome de quem divergiu')
        self.assertContains(response, 'Quando divergir valeu a pena')
        self.assertContains(response, 'Quando divergir piorou o resultado')
        self.assertContains(response, 'Outcome do turno alinhado')
        self.assertContains(response, 'Outcome do turno em tensao')
        self.assertContains(response, 'Quando a tensao valeu a pena')
        self.assertContains(response, 'Quando a tensao virou dispersao')
        self.assertContains(response, 'Tensao por timing')
        self.assertContains(response, 'Tensao por gravidade do caso')
        self.assertContains(response, 'Leitura composta da tensao')
        self.assertContains(response, 'Divergencia por timing')
        self.assertContains(response, 'Divergencia por acao sugerida')
        self.assertContains(response, 'Divergencia por gravidade do caso')
        self.assertContains(response, 'Leitura composta da divergencia')
        self.assertContains(response, 'historical_score = 0.4 * execution_rate + 0.6 * success_rate')
        self.assertContains(response, 'Timing')
        self.assertContains(response, 'Acao por timing')
        self.assertContains(response, 'Acao no tempo certo')
        self.assertContains(response, 'Receita mensal')
        self.assertContains(response, 'Realizado vs esperado')
        self.assertContains(response, 'Ativacoes vs cancelamentos')
        self.assertContains(response, 'alto risco')
        self.assertContains(response, 'Atraso financeiro recente')
        self.assertContains(response, 'Observar primeiro')
        self.assertContains(response, 'Casos que merecem monitoramento antes de empurrar a acao.')
        self.assertContains(response, 'com jogada contextual')
        self.assertContains(response, 'com conviccao alta')
        self.assertContains(response, 'com alta confianca')
        self.assertContains(response, 'Sinal dominante:')
        self.assertContains(response, 'Deixe estes')
        self.assertContains(response, 'Prioridade agregada do turno')
        self.assertContains(response, 'abrem esta faixa')
        self.assertContains(response, 'O que mais empurra esta faixa e')
        self.assertContains(response, 'Primeira jogada sugerida:')
        self.assertContains(response, 'Ela puxa para outro lado da recomendacao global do turno')
        self.assertContains(response, 'Alta confianca')
        self.assertContains(response, 'Missao primeiro, historico depois, contexto por ultimo')
        self.assertContains(response, 'Recomendacao global do turno')
        self.assertContains(response, 'Janela esfriando')
        self.assertContains(response, 'Revisar winback')
        self.assertContains(response, 'Acionar winback')
        self.assertContains(response, 'Abrir WhatsApp')
        self.assertContains(response, 'Revisar matricula')
        self.assertContains(response, 'finance-risk-action-neutral')
        self.assertContains(response, 'Nenhum contato operacional recente registrado.')
        self.assertContains(response, 'Registrar e abrir WhatsApp')
        self.assertContains(response, 'Ver sinais de apoio')
        self.assertContains(response, 'sem reforcos extras de timing ou contexto por enquanto.')
        self.assertContains(response, 'Aprendizados operacionais')
        self.assertContains(response, 'Matrizes de contexto')
        self.assertContains(response, 'name="open_in_whatsapp" value="1"', html=False)
        self.assertContains(response, 'href="#finance-priority-board"')
        self.assertContains(response, 'id="finance-queue-board"')
        self.assertContains(response, 'id="finance-overdue-support-board"')
        self.assertContains(response, 'href="#finance-portfolio-board"')
        self.assertContains(response, 'Planos ativos')
        self.assertNotContains(response, 'Mix Comercial e Dependencia')
        self.assertNotContains(response, 'Regua Ativa: Quem pede contato agora')
        self.assertContains(response, 'Total MRR')
        self.assertContains(response, f'href="{reverse("student-quick-update", args=[self.student.id])}#student-financial-overview"')
        self.assertRegex(response.content.decode(), r'R\$\s*319[,.]90')

    def test_finance_center_filters_by_plan_and_method(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('finance-center'),
            data={'months': '6', 'plan': self.plan.id, 'payment_method': 'pix'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Filtros da Leitura Financeira')
        self.assertContains(response, 'Cross Gold')

    def test_finance_center_filters_queue_by_mission(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('finance-center'),
            data={'queue_focus': 'high_signal'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alto risco')
        self.assertContains(response, 'Missao da fila')

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
        self.assertContains(follow_response, 'Aguardando primeira adesao')

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
