"""
ARQUIVO: testes da página de guia interno.

POR QUE ELE EXISTE:
- Garante que a página Mapa do Sistema continue acessível e útil para leitura do projeto.

O QUE ESTE ARQUIVO FAZ:
1. Testa renderização da página autenticada.
2. Valida a presença de conteúdos centrais do mapa.

PONTOS CRITICOS:
- Se esses testes falharem, a página de orientação interna pode ter quebrado ou perdido contexto.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from guide.models import OperationalRuntimeSetting
from student_identity.models import StudentAppInvitation, StudentInvitationDelivery, StudentInvitationDeliveryStatus
from students.models import Student


class GuideViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='owner-guide',
            email='owner-guide@example.com',
            password='senha-forte-123',
        )

    def test_system_map_renders_for_authenticated_user(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('system-map'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mapa do Sistema')
        self.assertContains(response, 'Primeira triagem por sintoma')
        self.assertContains(response, 'Rotina operacional do box')
        self.assertContains(response, 'Sidebar ou atalhos errados para o papel')
        self.assertContains(response, 'Auditoria')
        self.assertContains(response, 'DEV')
        self.assertContains(response, 'data-panel="system-flow-grid"')
        self.assertContains(response, 'id="system-reading-board"')
        self.assertContains(response, 'id="system-bug-board"')

    def test_operational_settings_renders_for_authenticated_user(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('operational-settings'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Operacao configurada.')
        self.assertContains(response, 'Salvar bloqueio do WhatsApp')
        self.assertContains(response, 'Criar perfis de acesso')
        self.assertContains(response, 'Abrir convites do aluno')

    def test_operational_settings_can_update_whatsapp_repeat_window(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('operational-settings'), {'repeat_block_hours': '12'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            OperationalRuntimeSetting.objects.get(key='whatsapp_repeat_block_hours').value,
            '12',
        )

    def test_student_invitation_operations_renders_for_owner(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('student-invitation-operations'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Convites operacionais prontos.')
        self.assertContains(response, 'Gerar convite do app do aluno')

    def test_student_invitation_operations_can_create_invite(self):
        self.client.force_login(self.user)
        student = Student.objects.create(
            full_name='Aluno Convite Operacional',
            phone='5511988887777',
            email='aluno.convite@example.com',
        )

        response = self.client.post(
            reverse('student-invitation-operations'),
            {
                'student': str(student.id),
                'invited_email': '',
                'expires_in_days': '7',
            },
        )

        self.assertEqual(response.status_code, 302)
        invitation = StudentAppInvitation.objects.get(student=student)
        self.assertEqual(invitation.invited_email, 'aluno.convite@example.com')
        self.assertGreater(invitation.expires_at, timezone.now())

    def test_student_invitation_operations_shows_delivery_status_badges(self):
        self.client.force_login(self.user)
        student = Student.objects.create(
            full_name='Aluno Status Convite',
            phone='5511977776666',
            email='status.convite@example.com',
        )
        invitation = StudentAppInvitation.objects.create(
            student=student,
            invited_email='status.convite@example.com',
            expires_at=timezone.now() + timezone.timedelta(days=7),
            created_by=self.user,
        )
        StudentInvitationDelivery.objects.create(
            invitation=invitation,
            channel='email',
            provider='resend',
            status=StudentInvitationDeliveryStatus.DELIVERED,
            recipient='status.convite@example.com',
            sent_at=timezone.now(),
        )

        response = self.client.get(reverse('student-invitation-operations'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Entregue')
        self.assertContains(response, 'E-mail entregue')

    def test_student_invitation_operations_shows_bounce_status_badge(self):
        self.client.force_login(self.user)
        student = Student.objects.create(
            full_name='Aluno Bounce Convite',
            phone='5511966665555',
            email='bounce.convite@example.com',
        )
        invitation = StudentAppInvitation.objects.create(
            student=student,
            invited_email='bounce.convite@example.com',
            expires_at=timezone.now() + timezone.timedelta(days=7),
            created_by=self.user,
        )
        StudentInvitationDelivery.objects.create(
            invitation=invitation,
            channel='email',
            provider='resend',
            status=StudentInvitationDeliveryStatus.BOUNCED,
            recipient='bounce.convite@example.com',
            failed_at=timezone.now(),
            error_message='email.bounced',
        )

        response = self.client.get(reverse('student-invitation-operations'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bounce')
        self.assertContains(response, 'Bounce detectado. Use Enviar mensagem no WhatsApp com o link do convite.')
        self.assertNotContains(response, 'Enviar e-mail')
        self.assertContains(response, 'Enviar mensagem')

    def test_student_invitation_operations_shows_complaint_recommendation(self):
        self.client.force_login(self.user)
        student = Student.objects.create(
            full_name='Aluno Complaint Convite',
            phone='5511955554444',
            email='complaint.convite@example.com',
        )
        invitation = StudentAppInvitation.objects.create(
            student=student,
            invited_email='complaint.convite@example.com',
            expires_at=timezone.now() + timezone.timedelta(days=7),
            created_by=self.user,
        )
        StudentInvitationDelivery.objects.create(
            invitation=invitation,
            channel='email',
            provider='resend',
            status=StudentInvitationDeliveryStatus.COMPLAINED,
            recipient='complaint.convite@example.com',
            failed_at=timezone.now(),
            error_message='email.complained',
        )

        response = self.client.get(reverse('student-invitation-operations'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Complaint')
        self.assertContains(response, 'Complaint detectado. Nao reenvie por e-mail; use Enviar mensagem no WhatsApp.')
        self.assertNotContains(response, 'Enviar e-mail')

    def test_student_invitation_operations_shows_whatsapp_handoff_status(self):
        self.client.force_login(self.user)
        student = Student.objects.create(
            full_name='Aluno WhatsApp Convite',
            phone='5511944443333',
            email='whatsapp.convite@example.com',
        )
        invitation = StudentAppInvitation.objects.create(
            student=student,
            invited_email='whatsapp.convite@example.com',
            expires_at=timezone.now() + timezone.timedelta(days=7),
            created_by=self.user,
        )
        StudentInvitationDelivery.objects.create(
            invitation=invitation,
            channel='whatsapp',
            provider='whatsapp_link',
            status=StudentInvitationDeliveryStatus.SENT,
            recipient='5511944443333',
            sent_at=timezone.now(),
        )

        response = self.client.get(reverse('student-invitation-operations'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mensagem aberta')
        self.assertContains(response, 'Ultima mensagem aberta')

    def test_student_invitation_operations_shows_stalled_queue_for_bounce_without_whatsapp(self):
        self.client.force_login(self.user)
        student = Student.objects.create(
            full_name='Aluno Travado Convite',
            phone='5511933332222',
            email='travado.convite@example.com',
        )
        invitation = StudentAppInvitation.objects.create(
            student=student,
            invited_email='travado.convite@example.com',
            expires_at=timezone.now() + timezone.timedelta(days=7),
            created_by=self.user,
        )
        StudentInvitationDelivery.objects.create(
            invitation=invitation,
            channel='email',
            provider='resend',
            status=StudentInvitationDeliveryStatus.BOUNCED,
            recipient='travado.convite@example.com',
            failed_at=timezone.now(),
            error_message='email.bounced',
        )

        response = self.client.get(reverse('student-invitation-operations'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alunos travados esperando mensagem')
        self.assertContains(response, 'Aluno Travado Convite')
        self.assertContains(response, 'E-mail devolvido. Falta enviar mensagem no WhatsApp.')

    def test_student_invitation_operations_prioritizes_complaint_over_bounce_in_stalled_queue(self):
        self.client.force_login(self.user)
        complaint_student = Student.objects.create(
            full_name='Aluno Complaint Primeiro',
            phone='5511922221111',
            email='primeiro.complaint@example.com',
        )
        complaint_invitation = StudentAppInvitation.objects.create(
            student=complaint_student,
            invited_email='primeiro.complaint@example.com',
            expires_at=timezone.now() + timezone.timedelta(days=7),
            created_by=self.user,
        )
        StudentInvitationDelivery.objects.create(
            invitation=complaint_invitation,
            channel='email',
            provider='resend',
            status=StudentInvitationDeliveryStatus.COMPLAINED,
            recipient='primeiro.complaint@example.com',
            failed_at=timezone.now() - timezone.timedelta(hours=1),
            error_message='email.complained',
        )

        bounce_student = Student.objects.create(
            full_name='Aluno Bounce Depois',
            phone='5511911110000',
            email='depois.bounce@example.com',
        )
        bounce_invitation = StudentAppInvitation.objects.create(
            student=bounce_student,
            invited_email='depois.bounce@example.com',
            expires_at=timezone.now() + timezone.timedelta(days=7),
            created_by=self.user,
        )
        StudentInvitationDelivery.objects.create(
            invitation=bounce_invitation,
            channel='email',
            provider='resend',
            status=StudentInvitationDeliveryStatus.BOUNCED,
            recipient='depois.bounce@example.com',
            failed_at=timezone.now() - timezone.timedelta(hours=3),
            error_message='email.bounced',
        )

        response = self.client.get(reverse('student-invitation-operations'))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        stalled_section = content.split('Alunos travados esperando mensagem', 1)[1].split('Ultimos links emitidos para o app do aluno', 1)[0]
        self.assertLess(
            stalled_section.index('Aluno Complaint Primeiro'),
            stalled_section.index('Aluno Bounce Depois'),
        )
        self.assertContains(response, 'Prioridade maxima')
