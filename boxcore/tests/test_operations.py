"""
ARQUIVO: testes das áreas operacionais por papel.

POR QUE ELE EXISTE:
- Garante que cada papel veja a área correta e que o coach consiga operar presença com permissão real.

O QUE ESTE ARQUIVO FAZ:
1. Testa o redirecionamento da área principal por papel.
2. Testa bloqueio de acesso indevido entre papéis.
3. Testa mudança de status de presença via tela operacional.
4. Testa a fundação técnica de DEV e auditoria.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from access.roles import ROLE_COACH, ROLE_DEV, ROLE_MANAGER, ROLE_RECEPTION
from auditing.models import AuditEvent
from finance.models import Enrollment, EnrollmentStatus, MembershipPlan, Payment, PaymentMethod, PaymentStatus
from operations.models import Attendance, BehaviorNote, ClassSession
from operations.queries import build_reception_workspace_snapshot
from students.models import Student


class OperationWorkspaceTests(TestCase):
    def setUp(self):
        cache.clear()
        call_command('bootstrap_roles')
        user_model = get_user_model()

        self.manager = user_model.objects.create_user('manager1', password='senha-forte-123')
        self.coach = user_model.objects.create_user('coach1', password='senha-forte-123')
        self.dev = user_model.objects.create_user('dev1', password='senha-forte-123')
        self.reception = user_model.objects.create_user('reception1', password='senha-forte-123')
        self.owner = user_model.objects.create_superuser('owner1', 'owner1@example.com', 'senha-forte-123')

        self.manager.groups.add(Group.objects.get(name=ROLE_MANAGER))
        self.coach.groups.add(Group.objects.get(name=ROLE_COACH))
        self.dev.groups.add(Group.objects.get(name=ROLE_DEV))
        self.reception.groups.add(Group.objects.get(name=ROLE_RECEPTION))

        self.student = Student.objects.create(full_name='Aluno Teste', phone='5511933333333')
        self.session = ClassSession.objects.create(title='WOD 07h', scheduled_at=timezone.now())
        self.attendance = Attendance.objects.create(student=self.student, session=self.session)
        self.plan = MembershipPlan.objects.create(name='Plano Mensal', price='299.90')
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            plan=self.plan,
            status=EnrollmentStatus.ACTIVE,
        )
        self.payment = Payment.objects.create(
            student=self.student,
            due_date=timezone.localdate(),
            amount='299.90',
            status=PaymentStatus.PENDING,
        )

    def test_role_operations_redirects_manager_to_manager_area(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse('role-operations'))

        self.assertRedirects(response, reverse('manager-workspace'))

    def test_role_operations_redirects_dev_to_dev_area(self):
        self.client.force_login(self.dev)

        response = self.client.get(reverse('role-operations'))

        self.assertRedirects(response, reverse('dev-workspace'))

    def test_role_operations_redirects_reception_to_reception_area(self):
        self.client.force_login(self.reception)

        response = self.client.get(reverse('role-operations'))

        self.assertRedirects(response, reverse('reception-workspace'))

    def test_coach_cannot_access_manager_area(self):
        self.client.force_login(self.coach)

        response = self.client.get(reverse('manager-workspace'))

        self.assertEqual(response.status_code, 403)

    def test_manager_cannot_access_coach_area(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse('coach-workspace'))

        self.assertEqual(response.status_code, 403)

    def test_dev_workspace_uses_dev_shell_scope_and_shortcuts(self):
        self.client.force_login(self.dev)

        response = self.client.get(reverse('dev-workspace'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'compass-pulse--operations-dev')
        self.assertContains(response, 'href="#dev-audit-board"')
        self.assertContains(response, 'href="#dev-boundary-board"')
        self.assertContains(response, 'href="#dev-read-board"')

    def test_reception_can_access_official_reception_workspace(self):
        self.client.force_login(self.reception)

        response = self.client.get(reverse('reception-workspace'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Seu balcão.')
        self.assertContains(response, 'href="#reception-intake-board"')
        self.assertContains(response, 'href="#reception-payment-board"')
        self.assertContains(response, 'href="#reception-class-grid-board"')

    def test_manager_cannot_access_official_reception_workspace(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse('reception-workspace'))

        self.assertEqual(response.status_code, 403)

    def test_reception_can_mark_payment_paid_from_official_reception_workspace(self):
        self.client.force_login(self.reception)

        response = self.client.post(
            reverse('reception-payment-action', args=[self.payment.id]),
            data={
                'payment_id': self.payment.id,
                'amount': self.payment.amount,
                'due_date': str(self.payment.due_date),
                'method': PaymentMethod.CASH,
                'reference': 'BALCAO-RECEPCAO',
                'notes': 'Recebido na recepcao oficial.',
                'action': 'mark-paid',
            },
            HTTP_REFERER=reverse('reception-workspace'),
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].endswith('#reception-payment-board'))
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.PAID)
        self.assertEqual(self.payment.method, PaymentMethod.CASH)

    def test_reception_can_update_payment_with_localized_amount_from_official_workspace(self):
        self.client.force_login(self.reception)

        response = self.client.post(
            reverse('reception-payment-action', args=[self.payment.id]),
            data={
                'payment_id': self.payment.id,
                'amount': '299,90',
                'due_date': str(self.payment.due_date),
                'method': PaymentMethod.PIX,
                'reference': 'BALCAO-AJUSTE',
                'notes': 'Ajuste curto salvo pela recepcao.',
                'action': 'update-payment',
            },
            HTTP_REFERER=reverse('reception-workspace'),
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].endswith('#reception-payment-board'))
        self.payment.refresh_from_db()
        self.assertEqual(str(self.payment.amount), '299.90')
        self.assertEqual(self.payment.method, PaymentMethod.PIX)
        self.assertEqual(self.payment.reference, 'BALCAO-AJUSTE')
        self.assertEqual(self.payment.notes, 'Ajuste curto salvo pela recepcao.')

    @override_settings(WRITE_RATE_LIMIT_MAX_REQUESTS=2, WRITE_RATE_LIMIT_WINDOW_SECONDS=60)
    def test_reception_payment_action_blocks_burst_requests(self):
        self.client.force_login(self.reception)

        payload = {
            'payment_id': self.payment.id,
            'due_date': str(self.payment.due_date),
            'method': PaymentMethod.PIX,
            'reference': 'BALCAO-THROTTLE',
            'notes': 'Teste de rajada bloqueada.',
            'action': 'update-payment',
        }

        first_response = self.client.post(
            reverse('reception-payment-action', args=[self.payment.id]),
            data=payload,
            HTTP_REFERER=reverse('reception-workspace'),
        )
        second_response = self.client.post(
            reverse('reception-payment-action', args=[self.payment.id]),
            data=payload,
            HTTP_REFERER=reverse('reception-workspace'),
        )
        blocked_response = self.client.post(
            reverse('reception-payment-action', args=[self.payment.id]),
            data=payload,
            HTTP_REFERER=reverse('reception-workspace'),
        )

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(blocked_response.status_code, 429)
        self.assertEqual(blocked_response['Retry-After'], '60')

    def test_reception_can_access_students_and_class_grid_but_not_finance_center(self):
        self.client.force_login(self.reception)

        students_response = self.client.get(reverse('student-directory'))
        class_grid_response = self.client.get(reverse('class-grid'))
        finance_response = self.client.get(reverse('finance-center'))

        self.assertEqual(students_response.status_code, 200)
        self.assertEqual(class_grid_response.status_code, 200)
        self.assertEqual(finance_response.status_code, 403)

    def test_reception_sidebar_hides_finance_link(self):
        self.client.force_login(self.reception)

        response = self.client.get(reverse('reception-workspace'))

        self.assertNotContains(response, 'href="/financeiro/"')

    def test_sidebar_keeps_my_operation_immediately_after_dashboard_for_main_roles(self):
        scenarios = [
            (self.owner, 'owner-workspace'),
            (self.manager, 'manager-workspace'),
            (self.coach, 'coach-workspace'),
            (self.reception, 'reception-workspace'),
        ]

        for user, route_name in scenarios:
            with self.subTest(route_name=route_name):
                self.client.force_login(user)
                response = self.client.get(reverse(route_name))
                hrefs = [item['href'] for item in response.context['sidebar_navigation']]

                self.assertIn('/dashboard/', hrefs)
                self.assertIn('/operacao/', hrefs)
                self.assertLess(hrefs.index('/dashboard/'), hrefs.index('/operacao/'))

    def test_sidebar_positions_entries_between_finance_and_class_grid_when_visible(self):
        scenarios = [
            (self.owner, 'owner-workspace'),
            (self.manager, 'manager-workspace'),
        ]

        for user, route_name in scenarios:
            with self.subTest(route_name=route_name):
                self.client.force_login(user)
                response = self.client.get(reverse(route_name))
                hrefs = [item['href'] for item in response.context['sidebar_navigation']]

                self.assertIn('/financeiro/', hrefs)
                self.assertIn('/entradas/', hrefs)
                self.assertIn('/grade-aulas/', hrefs)
                self.assertLess(hrefs.index('/financeiro/'), hrefs.index('/entradas/'))
                self.assertLess(hrefs.index('/entradas/'), hrefs.index('/grade-aulas/'))

    def test_reception_topbar_finance_chip_points_to_reception_queue(self):
        self.client.force_login(self.reception)

        response = self.client.get(reverse('reception-workspace'))

        self.assertContains(response, 'href="/operacao/recepcao/#reception-payment-board"')

    def test_reception_snapshot_counts_pending_past_due_as_real_overdue(self):
        Payment.objects.create(
            student=self.student,
            enrollment=self.enrollment,
            due_date=timezone.localdate() - timezone.timedelta(days=1),
            amount='149.90',
            status=PaymentStatus.PENDING,
        )

        snapshot = build_reception_workspace_snapshot(today=timezone.localdate())

        overdue_stat = next(item for item in snapshot['hero_stats'] if item['label'] == 'Atrasos')
        self.assertEqual(overdue_stat['value'], 1)
        self.assertIn('Pagamento vencido ha 1 dia(s)', snapshot['reception_queue'][0]['reason'])

    def test_coach_can_check_in_attendance(self):
        self.client.force_login(self.coach)

        response = self.client.post(reverse('attendance-action', args=[self.attendance.id, 'check-in']))

        self.assertEqual(response.status_code, 302)
        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.status, 'checked_in')
        self.assertTrue(AuditEvent.objects.filter(action='attendance_check-in', actor=self.coach).exists())

    def test_manager_cannot_operate_attendance_action(self):
        self.client.force_login(self.manager)

        response = self.client.post(reverse('attendance-action', args=[self.attendance.id, 'check-in']))

        self.assertEqual(response.status_code, 403)

    def test_manager_can_link_payment_to_active_enrollment(self):
        self.client.force_login(self.manager)

        response = self.client.post(reverse('payment-enrollment-link', args=[self.payment.id]))

        self.assertEqual(response.status_code, 302)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.enrollment, self.enrollment)
        self.assertTrue(AuditEvent.objects.filter(action='payment_linked_to_active_enrollment', actor=self.manager).exists())

    def test_coach_can_create_technical_behavior_note(self):
        self.client.force_login(self.coach)

        response = self.client.post(
            reverse('technical-behavior-note-create', args=[self.student.id]),
            data={
                'category': 'support',
                'description': 'Aluno relatou desconforto no ombro direito durante o aquecimento.',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(BehaviorNote.objects.filter(student=self.student, author=self.coach).exists())
        self.assertTrue(AuditEvent.objects.filter(action='technical_behavior_note_created', actor=self.coach).exists())

    def test_coach_workspace_exposes_real_turn_metrics_and_boundary_anchor(self):
        self.client.force_login(self.coach)

        response = self.client.get(reverse('coach-workspace'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="#coach-boundary-board"')
        self.assertContains(response, 'id="coach-boundary-board"')
        self.assertContains(response, 'Alunos na lista')
        self.assertContains(response, 'Check-ins no turno')
        self.assertContains(response, 'Pendencias de check-in')
        self.assertNotContains(response, 'Guias de execucao')
        self.assertNotContains(response, 'Fronteiras do papel')

    def test_manager_sidebar_hides_coach_links(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse('manager-workspace'))
        hrefs = [item['href'] for item in response.context['sidebar_navigation']]

        self.assertEqual(hrefs.count('/alunos/'), 1)
        self.assertEqual(hrefs.count('/entradas/'), 1)
        self.assertEqual(hrefs.count('/financeiro/'), 1)
        self.assertContains(response, 'Pagamentos')
        self.assertNotContains(response, 'Ocorrências')

    def test_manager_workspace_keeps_single_enrollment_link_board(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse('manager-workspace'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'manager-scene')
        self.assertContains(response, 'id="manager-enrollment-link-board"', count=1)
        self.assertContains(response, 'Estrutura antes de leitura financeira', count=1)

    def test_manager_workspace_exposes_priority_surface_and_metric_anchors(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse('manager-workspace'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-manager-priority="links"')
        self.assertContains(response, 'href="#manager-link-board"')
        self.assertContains(response, 'href="#manager-enrollment-link-board"')
        self.assertContains(response, 'href="#manager-finance-board"')

    def test_coach_sidebar_hides_manager_links(self):
        self.client.force_login(self.coach)

        response = self.client.get(reverse('coach-workspace'))
        hrefs = [item['href'] for item in response.context['sidebar_navigation']]

        self.assertEqual(hrefs.count('/grade-aulas/'), 1)
        self.assertContains(response, 'Ocorrências')
        self.assertNotContains(response, 'Pagamentos')

    def test_owner_can_access_owner_area(self):
        self.client.force_login(self.owner)

        Payment.objects.create(
            student=self.student,
            enrollment=self.enrollment,
            due_date=timezone.localdate() - timezone.timedelta(days=2),
            amount='299.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        response = self.client.get(reverse('owner-workspace'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Caixa vencido: R$ 299,90')
        self.assertContains(response, 'Há cobrança atrasada pedindo contato agora.')

    def test_owner_workspace_exposes_executive_workspace_and_priority(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse('owner-workspace'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-owner-priority=')
        self.assertContains(response, 'Mesa executiva do owner')
        self.assertContains(response, 'Movimento que lidera o dia')
        self.assertContains(response, 'Como o dia esta')
        self.assertContains(response, 'Se bater duvida, siga isso')

    def test_dev_can_access_dev_workspace(self):
        self.client.force_login(self.dev)

        response = self.client.get(reverse('dev-workspace'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Leitura técnica controlada')
        self.assertContains(response, 'Eventos recentes de auditoria')
