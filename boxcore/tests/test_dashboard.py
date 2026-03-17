"""
ARQUIVO: testes do dashboard.

POR QUE ELE EXISTE:
- Garante que o painel principal continue acessivel e com o contrato visual e funcional esperado.

O QUE ESTE ARQUIVO FAZ:
1. Testa protecao por login.
2. Testa renderizacao do resumo rapido, metricas e agenda.
3. Testa links vivos do presenter e regressao de anchors removidas.
4. Mantem smoke de status das aulas e rate limit.
"""

from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from communications.models import WhatsAppContact
from access.roles import ROLE_COACH, ROLE_RECEPTION
from dashboard.presentation import _build_dashboard_execution_focus
from finance.models import Enrollment, MembershipPlan, Payment, PaymentMethod, PaymentStatus
from operations.models import Attendance, ClassSession, SessionStatus
from students.models import Student, StudentStatus


class DashboardViewTests(TestCase):
    def setUp(self):
        cache.clear()
        call_command('bootstrap_roles')
        self.user = get_user_model().objects.create_superuser(
            username='gestor',
            email='gestor@example.com',
            password='senha-forte-123',
        )
        self.reception_user = get_user_model().objects.create_user(
            username='recepcao',
            email='recepcao@example.com',
            password='senha-forte-123',
        )
        self.coach_user = get_user_model().objects.create_user(
            username='coach-dashboard',
            email='coach-dashboard@example.com',
            password='senha-forte-123',
        )
        self.reception_user.groups.add(Group.objects.get(name=ROLE_RECEPTION))
        self.coach_user.groups.add(Group.objects.get(name=ROLE_COACH))
        MembershipPlan.objects.create(name='Mensal 3x', price='249.90')
        Student.objects.create(full_name='Ana Silva', phone='5511999999999')

    def test_redirects_when_user_is_not_authenticated(self):
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 302)

    def test_dashboard_renders_summary_strip_metrics_and_sessions_for_authenticated_user(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Seu box em alta performance.')
        self.assertContains(response, 'Owner')
        self.assertContains(response, 'Leitura rapida')
        self.assertContains(response, 'class="dashboard-glance-strip dashboard-glance-strip--summary"', html=False)
        self.assertContains(response, 'class="dashboard-glance-card dashboard-glance-card--summary is-finance"', html=False)
        self.assertContains(response, 'class="dashboard-glance-card dashboard-glance-card--summary is-base"', html=False)
        self.assertContains(response, 'class="dashboard-glance-card dashboard-glance-card--summary is-risk"', html=False)
        self.assertContains(response, 'Urgencia')
        self.assertContains(response, 'Emergencia')
        self.assertContains(response, 'Risco')
        self.assertContains(response, 'Sem pendencia financeira critica no recorte atual', html=False)
        self.assertContains(response, 'Nenhuma pendencia emergente ligada a retencao ou experiencia aparece no recorte atual', html=False)
        self.assertContains(response, 'Sem sinal forte de desorganizacao no recorte imediato', html=False)
        self.assertContains(response, 'href="/financeiro/"', html=False)
        self.assertContains(response, 'href="/alunos/"', html=False)
        self.assertContains(response, 'href="#dashboard-sessions-board"', html=False)
        self.assertContains(response, 'Agenda do turno')
        self.assertContains(response, 'class="dashboard-support-grid"', html=False)
        content = response.content.decode('utf-8')
        self.assertLess(content.index('Receita realizada'), content.index('Cobrancas em atraso'))
        self.assertLess(content.index('Cobrancas em atraso'), content.index('Entradas pendentes'))
        self.assertNotContains(response, '#dashboard-finance-board')
        self.assertNotContains(response, '#dashboard-risk-board')

    def test_dashboard_adapts_actions_for_reception_role(self):
        self.client.force_login(self.reception_user)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Chegada, agenda e caixa curto em um painel rapido, energico e imediatamente util para o balcao.')
        self.assertContains(response, 'href="/alunos/novo/"', html=False)
        self.assertContains(response, '/operacao/recepcao/#reception-payment-board')
        self.assertContains(response, 'Abrir cobrancas do balcao')
        self.assertContains(response, 'class="dashboard-glance-strip dashboard-glance-strip--summary"', html=False)
        self.assertNotContains(response, '#dashboard-finance-board')

    def test_dashboard_keeps_sessions_shortcut_for_coach_role(self):
        self.client.force_login(self.coach_user)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Leitura rapida')
        self.assertContains(response, 'href="#dashboard-sessions-board"', html=False)
        self.assertNotContains(response, '/operacao/recepcao/#reception-payment-board')

    def test_owner_execution_focus_targets_only_live_destinations(self):
        next_session = {'object': SimpleNamespace(title='Cross 19h15')}
        next_payment_alert = SimpleNamespace(student=SimpleNamespace(full_name='Bruna Ativa'))
        highest_risk_student = SimpleNamespace(full_name='Caio Menezes', total_absences=2)

        focus = _build_dashboard_execution_focus(
            'owner',
            next_session=next_session,
            next_payment_alert=next_payment_alert,
            highest_risk_student=highest_risk_student,
            actionable_payment_alerts_count=2,
        )

        self.assertEqual(focus[0]['href'], '/financeiro/')
        self.assertEqual(focus[0]['href_label'], 'Abrir financeiro')
        self.assertEqual(focus[1]['href'], '#dashboard-sessions-board')
        self.assertEqual(focus[2]['href'], '/alunos/')
        self.assertEqual(focus[2]['href_label'], 'Abrir alunos em atencao')

    def test_reception_execution_focus_keeps_payment_board_and_live_student_target(self):
        next_payment_alert = SimpleNamespace(student=SimpleNamespace(full_name='Rafa Balcao'))

        focus = _build_dashboard_execution_focus(
            ROLE_RECEPTION,
            next_session=None,
            next_payment_alert=next_payment_alert,
            highest_risk_student=None,
            actionable_payment_alerts_count=1,
        )

        self.assertEqual(focus[0]['href'], '/operacao/recepcao/#reception-payment-board')
        self.assertEqual(focus[1]['href'], '#dashboard-sessions-board')
        self.assertEqual(focus[2]['href'], '/alunos/')
        self.assertEqual(focus[2]['href_label'], 'Abrir alunos que pedem cuidado')

    def test_dashboard_keeps_routine_session_out_of_emergency_card(self):
        self.client.force_login(self.user)
        today = timezone.localdate()
        ClassSession.objects.create(
            title='Gymnastics 19h',
            coach=self.user,
            scheduled_at=timezone.make_aware(
                timezone.datetime.combine(today, timezone.datetime.strptime('19:00', '%H:%M').time()),
                timezone.get_current_timezone(),
            ),
            duration_minutes=60,
            capacity=18,
            status=SessionStatus.SCHEDULED,
        )

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nenhuma pendencia emergente ligada a retencao ou experiencia aparece no recorte atual', html=False)
        self.assertContains(response, 'Entradas pendentes')

    def test_dashboard_priority_counts_only_actionable_financial_alerts(self):
        self.client.force_login(self.user)
        actionable_student = Student.objects.create(full_name='Bruna Ativa', phone='5511988887777', status=StudentStatus.ACTIVE)
        actionable_enrollment = Enrollment.objects.create(student=actionable_student, plan=MembershipPlan.objects.create(name='Plano Prioridade', price='199.90'))
        Payment.objects.create(
            student=actionable_student,
            enrollment=actionable_enrollment,
            due_date=timezone.localdate() - timezone.timedelta(days=2),
            amount='199.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )
        blocked_student = Student.objects.create(full_name='Lia Bloqueada', phone='5511977776666', status=StudentStatus.ACTIVE)
        blocked_enrollment = Enrollment.objects.create(student=blocked_student, plan=MembershipPlan.objects.create(name='Plano Bloqueio', price='219.90'))
        Payment.objects.create(
            student=blocked_student,
            enrollment=blocked_enrollment,
            due_date=timezone.localdate() - timezone.timedelta(days=3),
            amount='219.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )
        WhatsAppContact.objects.create(
            phone=blocked_student.phone,
            display_name='Lia Bloqueada',
            linked_student=blocked_student,
            last_outbound_at=timezone.now(),
        )

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Cobrancas: 1. Abrir financeiro"', html=False)
        self.assertContains(response, 'Urgencia')
        self.assertContains(response, 'class="dashboard-glance-card dashboard-glance-card--summary is-finance"', html=False)
        self.assertContains(response, 'Bruna Ativa')
        self.assertNotContains(response, 'aria-label="Cobrancas: 2. Abrir financeiro"', html=False)
        self.assertContains(response, 'Abrir financeiro')
        self.assertNotContains(response, '#dashboard-finance-board')

    @override_settings(DASHBOARD_RATE_LIMIT_MAX_REQUESTS=1, DASHBOARD_RATE_LIMIT_WINDOW_SECONDS=60)
    def test_dashboard_blocks_short_burst_attempts(self):
        self.client.force_login(self.user)

        first_response = self.client.get(reverse('dashboard'))
        blocked_response = self.client.get(reverse('dashboard'))

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(blocked_response.status_code, 429)
        self.assertEqual(blocked_response['Retry-After'], '60')

    def test_dashboard_marks_today_session_as_in_progress_during_runtime(self):
        self.client.force_login(self.user)
        today = timezone.localdate()
        session = ClassSession.objects.create(
            title='WOD 08h',
            coach=self.user,
            scheduled_at=timezone.make_aware(
                timezone.datetime.combine(today, timezone.datetime.strptime('08:00', '%H:%M').time()),
                timezone.get_current_timezone(),
            ),
            duration_minutes=60,
            capacity=10,
            status=SessionStatus.SCHEDULED,
        )
        Attendance.objects.create(student=Student.objects.create(full_name='Aluno 08h', phone='5511988880001'), session=session)
        original_localtime = timezone.localtime
        simulated_now = timezone.make_aware(
            timezone.datetime.combine(today, timezone.datetime.strptime('08:00', '%H:%M').time()),
            timezone.get_current_timezone(),
        )

        with patch(
            'boxcore.dashboard.dashboard_snapshot_queries.timezone.localtime',
            side_effect=lambda value=None, *args, **kwargs: simulated_now if value is None else original_localtime(value, *args, **kwargs),
        ):
            response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Em andamento')
        self.assertContains(response, 'Em aula agora')
        self.assertContains(response, 'class="dashboard-session-card dashboard-session-card--featured is-primary"', html=False)
        self.assertContains(response, '1/10')
        session.refresh_from_db()
        self.assertEqual(session.status, SessionStatus.SCHEDULED)

    def test_dashboard_auto_completes_session_after_end_time(self):
        self.client.force_login(self.user)
        today = timezone.localdate()
        session = ClassSession.objects.create(
            title='WOD 08h final',
            coach=self.user,
            scheduled_at=timezone.make_aware(
                timezone.datetime.combine(today, timezone.datetime.strptime('08:00', '%H:%M').time()),
                timezone.get_current_timezone(),
            ),
            duration_minutes=60,
            capacity=12,
            status=SessionStatus.SCHEDULED,
        )
        Attendance.objects.create(student=Student.objects.create(full_name='Aluno final', phone='5511988880002'), session=session)
        original_localtime = timezone.localtime
        simulated_now = timezone.make_aware(
            timezone.datetime.combine(today, timezone.datetime.strptime('09:01', '%H:%M').time()),
            timezone.get_current_timezone(),
        )

        with patch(
            'boxcore.dashboard.dashboard_snapshot_queries.timezone.localtime',
            side_effect=lambda value=None, *args, **kwargs: simulated_now if value is None else original_localtime(value, *args, **kwargs),
        ):
            response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'WOD 08h final')
        self.assertContains(response, 'Nenhuma aula cadastrada ainda')
        session.refresh_from_db()
        self.assertEqual(session.status, SessionStatus.COMPLETED)














