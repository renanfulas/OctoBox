"""
ARQUIVO: testes do dashboard.

POR QUE ELE EXISTE:
- Garante que o painel principal continue acessível e renderizando o básico.

O QUE ESTE ARQUIVO FAZ:
1. Testa proteção por login.
2. Testa renderização do painel autenticado.

PONTOS CRITICOS:
- Se esses testes falharem, pode ter quebrado rota, template ou contexto do dashboard.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from access.roles import ROLE_COACH, ROLE_RECEPTION
from communications.models import WhatsAppContact, WhatsAppMessageLog
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

    def test_dashboard_renders_for_authenticated_user(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Seu box em tres decisoes.')
        self.assertContains(response, 'Owner')
        self.assertContains(response, 'Prioridade')
        self.assertContains(response, 'Pendente')
        self.assertContains(response, 'Próxima ação')
        self.assertContains(response, 'href="#dashboard-finance-board"')
        self.assertContains(response, 'href="/entradas/#intake-queue-board"')
        self.assertContains(response, 'href="#dashboard-sessions-board"')
        self.assertContains(response, 'Abrir aulas do dia')
        self.assertNotContains(response, 'href="/operacao/coach/"')

    def test_dashboard_adapts_actions_for_reception_role(self):
        self.client.force_login(self.reception_user)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Comece por chegada, agenda e cobrança curta sem sobrecarregar o balcão.')
        self.assertContains(response, 'Abrir balcao da recepcao')
        self.assertContains(response, '/operacao/recepcao/#reception-payment-board')
        self.assertNotContains(response, 'Abrir financeiro')
        self.assertContains(response, 'Resumo imediato')

    def test_dashboard_keeps_presence_quick_action_for_coach_role(self):
        self.client.force_login(self.coach_user)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Marcar presenca')
        self.assertContains(response, 'href="/operacao/coach/"')

    def test_dashboard_exposes_whatsapp_quick_action_on_finance_board(self):
        self.client.force_login(self.user)
        student = Student.objects.create(full_name='Bruna Lima', phone='(11) 98888-7777')
        enrollment = Enrollment.objects.create(student=student, plan=MembershipPlan.objects.create(name='Plano Whats', price='199.90'))
        Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=timezone.localdate() - timezone.timedelta(days=2),
            amount='199.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Quem cobrar agora')
        self.assertContains(response, 'Cobrar hoje.')
        self.assertContains(response, 'Ação')
        self.assertContains(response, 'Sem contato recente')
        self.assertContains(response, 'Abrir WhatsApp')
        self.assertContains(response, 'name="open_in_whatsapp" value="1"', html=False)

    def test_dashboard_priority_counts_only_actionable_financial_alerts(self):
        self.client.force_login(self.user)
        actionable_student = Student.objects.create(full_name='Bruna Ativa', phone='5511988887777', status=StudentStatus.ACTIVE)
        actionable_enrollment = Enrollment.objects.create(student=actionable_student, plan=MembershipPlan.objects.create(name='Plano Prioridade', price='199.90'))
        actionable_payment = Payment.objects.create(
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
            linked_student=blocked_student,
            last_outbound_at=timezone.now() - timezone.timedelta(hours=1),
        )
        inactive_student = Student.objects.create(full_name='Nina Inativa', phone='5511966665555', status=StudentStatus.INACTIVE)
        inactive_enrollment = Enrollment.objects.create(student=inactive_student, plan=MembershipPlan.objects.create(name='Plano Inativo', price='179.90'))
        Payment.objects.create(
            student=inactive_student,
            enrollment=inactive_enrollment,
            due_date=timezone.localdate() - timezone.timedelta(days=4),
            amount='179.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Prioridade: 1. Abrir cobrancas em atraso"', html=False)
        self.assertContains(response, 'Bruna Ativa')
        self.assertContains(response, 'Lia Bloqueada')
        self.assertContains(response, '2 alerta(s)')

    def test_dashboard_priority_resolves_after_whatsapp_touch_reopens_after_window_and_expires_for_inactive_student(self):
        self.client.force_login(self.user)
        student = Student.objects.create(full_name='Bruna Ciclo', phone='5511955554444', status=StudentStatus.ACTIVE)
        enrollment = Enrollment.objects.create(student=student, plan=MembershipPlan.objects.create(name='Plano Ciclo', price='189.90'))
        payment = Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=timezone.localdate() - timezone.timedelta(days=2),
            amount='189.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        first_response = self.client.get(reverse('dashboard'))
        action_response = self.client.post(
            reverse('finance-communication-action'),
            data={
                'action_kind': 'overdue',
                'student_id': student.id,
                'payment_id': payment.id,
                'open_in_whatsapp': '1',
            },
        )
        blocked_response = self.client.get(reverse('dashboard'))

        self.assertEqual(first_response.status_code, 200)
        self.assertContains(first_response, 'aria-label="Prioridade: 1.', html=False)
        self.assertContains(first_response, 'Abrir WhatsApp')
        self.assertEqual(action_response.status_code, 302)
        self.assertTrue(action_response['Location'].startswith(f'https://wa.me/{student.phone}?text='))
        self.assertTrue(WhatsAppMessageLog.objects.filter(contact__phone=student.phone, direction='outbound').exists())
        self.assertEqual(blocked_response.status_code, 200)
        self.assertContains(blocked_response, 'Janela bloqueada')
        self.assertNotContains(blocked_response, 'aria-label="Prioridade: 1.', html=False)
        self.assertNotContains(blocked_response, 'data-action="open-dashboard-finance-whatsapp"')

        contact = WhatsAppContact.objects.get(linked_student=student)
        contact.last_outbound_at = timezone.now() - timezone.timedelta(hours=25)
        contact.save(update_fields=['last_outbound_at', 'updated_at'])

        reopened_response = self.client.get(reverse('dashboard'))

        self.assertEqual(reopened_response.status_code, 200)
        self.assertContains(reopened_response, 'aria-label="Prioridade: 1.', html=False)
        self.assertContains(reopened_response, 'Abrir WhatsApp')

        student.status = StudentStatus.INACTIVE
        student.save(update_fields=['status', 'updated_at'])

        expired_response = self.client.get(reverse('dashboard'))

        self.assertEqual(expired_response.status_code, 200)
        self.assertNotContains(expired_response, 'aria-label="Prioridade: 1.', html=False)
        self.assertContains(expired_response, 'Nenhum pagamento atrasado')
        self.assertNotContains(expired_response, 'data-action="open-dashboard-finance-whatsapp"')

    def test_dashboard_shows_contact_block_state_on_finance_board(self):
        self.client.force_login(self.user)
        student = Student.objects.create(full_name='Marina Whats', phone='(11) 96666-2222')
        enrollment = Enrollment.objects.create(student=student, plan=MembershipPlan.objects.create(name='Plano Trava', price='219.90'))
        Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=timezone.localdate() - timezone.timedelta(days=3),
            amount='219.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )
        WhatsAppContact.objects.create(
            phone='5511966662222',
            linked_student=student,
            last_outbound_at=timezone.now() - timezone.timedelta(hours=1),
        )

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Janela bloqueada')
        self.assertContains(response, 'Bloqueado agora')
        self.assertNotContains(response, 'data-action="open-dashboard-finance-whatsapp"')

    def test_dashboard_hides_finance_whatsapp_action_for_read_only_roles(self):
        dev_user = get_user_model().objects.create_user(
            username='dev-dashboard',
            email='dev-dashboard@example.com',
            password='senha-forte-123',
        )
        dev_user.groups.add(Group.objects.get(name='DEV'))
        student = Student.objects.create(full_name='Rita Dev', phone='(11) 97777-6666')
        enrollment = Enrollment.objects.create(student=student, plan=MembershipPlan.objects.create(name='Plano Dev', price='199.90'))
        Payment.objects.create(
            student=student,
            enrollment=enrollment,
            due_date=timezone.localdate() - timezone.timedelta(days=2),
            amount='199.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )
        self.client.force_login(dev_user)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sem permissao para contato')
        self.assertNotContains(response, 'Abrir WhatsApp')

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
        self.assertContains(response, 'Finalizada')
        self.assertContains(response, '1/12')
        session.refresh_from_db()
        self.assertEqual(session.status, SessionStatus.COMPLETED)