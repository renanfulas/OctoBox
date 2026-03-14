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
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from access.roles import ROLE_COACH, ROLE_DEV, ROLE_MANAGER, ROLE_RECEPTION
from auditing.models import AuditEvent
from finance.models import Enrollment, EnrollmentStatus, MembershipPlan, Payment, PaymentMethod, PaymentStatus
from operations.models import Attendance, BehaviorNote, ClassSession
from students.models import Student


class OperationWorkspaceTests(TestCase):
    def setUp(self):
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

    def test_owner_can_access_hidden_reception_preview(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse('reception-preview-workspace'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recepcao em preparo')

    def test_dev_can_access_hidden_reception_preview(self):
        self.client.force_login(self.dev)

        response = self.client.get(reverse('reception-preview-workspace'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Preview oculto')

    def test_manager_cannot_access_hidden_reception_preview(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse('reception-preview-workspace'))

        self.assertEqual(response.status_code, 403)

    def test_reception_can_access_official_reception_workspace(self):
        self.client.force_login(self.reception)

        response = self.client.get(reverse('reception-workspace'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Centro da recepcao')
        self.assertContains(response, 'href="#reception-intake-board"')
        self.assertContains(response, 'href="#reception-payment-board"')
        self.assertContains(response, 'href="#reception-class-grid-board"')

    def test_manager_cannot_access_official_reception_workspace(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse('reception-workspace'))

        self.assertEqual(response.status_code, 403)

    def test_owner_can_mark_payment_paid_from_hidden_reception_preview(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse('reception-preview-payment-action', args=[self.payment.id]),
            data={
                'payment_id': self.payment.id,
                'amount': self.payment.amount,
                'due_date': str(self.payment.due_date),
                'method': PaymentMethod.PIX,
                'reference': 'BALCAO-OK',
                'notes': 'Recebido no preview da recepcao.',
                'action': 'mark-paid',
            },
            HTTP_REFERER=reverse('reception-preview-workspace'),
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].endswith('#reception-payment-board'))
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.PAID)
        self.assertEqual(self.payment.method, PaymentMethod.PIX)

    def test_dev_cannot_mutate_payment_from_hidden_reception_preview(self):
        self.client.force_login(self.dev)

        response = self.client.post(
            reverse('reception-preview-payment-action', args=[self.payment.id]),
            data={
                'payment_id': self.payment.id,
                'amount': self.payment.amount,
                'due_date': str(self.payment.due_date),
                'method': PaymentMethod.CASH,
                'reference': 'DEV-BLOCKED',
                'notes': 'Tentativa bloqueada.',
                'action': 'mark-paid',
            },
        )

        self.assertEqual(response.status_code, 403)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.PENDING)

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

    def test_reception_topbar_finance_chip_points_to_reception_queue(self):
        self.client.force_login(self.reception)

        response = self.client.get(reverse('reception-workspace'))

        self.assertContains(response, 'href="/operacao/recepcao/#reception-payment-board"')

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

    def test_manager_sidebar_hides_coach_links(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse('manager-workspace'))

        self.assertContains(response, 'Pagamentos')
        self.assertNotContains(response, 'Ocorrências')

    def test_coach_sidebar_hides_manager_links(self):
        self.client.force_login(self.coach)

        response = self.client.get(reverse('coach-workspace'))

        self.assertContains(response, 'Ocorrências')
        self.assertNotContains(response, 'Pagamentos')

    def test_hidden_reception_preview_does_not_appear_in_owner_sidebar(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse('owner-workspace'))

        self.assertNotContains(response, '/operacao/recepcao-preview/')

    def test_owner_can_access_owner_area(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse('owner-workspace'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Leitura executiva do box')

    def test_dev_can_access_dev_workspace(self):
        self.client.force_login(self.dev)

        response = self.client.get(reverse('dev-workspace'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Leitura técnica controlada')
        self.assertContains(response, 'Eventos recentes de auditoria')