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

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from access.admin import admin_changelist_url
from guide.models import OperationalRuntimeSetting
from onboarding.models import StudentIntake
from operations.models import LeadImportDeclaredRange, LeadImportJob, LeadImportJobStatus, LeadImportProcessingMode, LeadImportSourceType
from shared_support.box_runtime import get_box_runtime_slug
from student_identity.models import (
    StudentAppInvitation,
    StudentBoxMembership,
    StudentBoxMembershipStatus,
    StudentIdentity,
    StudentIdentityProvider,
    StudentIdentityStatus,
    StudentInvitationDelivery,
    StudentInvitationDeliveryStatus,
    StudentInvitationType,
)
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
        self.assertContains(response, 'Faixa declarada')
        self.assertContains(response, 'Ate 200 leads')
        self.assertNotContains(response, 'Status atual da importacao')

    def test_operational_settings_shows_latest_lead_import_status_when_job_exists(self):
        self.client.force_login(self.user)
        LeadImportJob.objects.create(
            created_by=self.user,
            source_type=LeadImportSourceType.WHATSAPP_LIST,
            declared_range=LeadImportDeclaredRange.FROM_201_TO_500,
            processing_mode=LeadImportProcessingMode.ASYNC_NOW,
            status=LeadImportJobStatus.RUNNING,
            original_filename='lista-whatsapp.csv',
            detected_lead_count=320,
        )

        response = self.client.get(reverse('operational-settings'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Status atual da importacao')
        self.assertContains(response, 'Arquivo de leads sendo avaliado')
        self.assertContains(response, 'lista-whatsapp.csv')
        self.assertContains(response, 'Leads detectados: 320')

    def test_operational_settings_hides_lead_import_status_after_24_hours(self):
        self.client.force_login(self.user)
        job = LeadImportJob.objects.create(
            created_by=self.user,
            source_type=LeadImportSourceType.WHATSAPP_LIST,
            declared_range=LeadImportDeclaredRange.FROM_201_TO_500,
            processing_mode=LeadImportProcessingMode.ASYNC_NOW,
            status=LeadImportJobStatus.RUNNING,
            original_filename='lista-antiga.csv',
            detected_lead_count=320,
        )
        stale_time = timezone.now() - timezone.timedelta(hours=25)
        LeadImportJob.objects.filter(pk=job.pk).update(created_at=stale_time, updated_at=stale_time)

        response = self.client.get(reverse('operational-settings'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Status atual da importacao')
        self.assertNotContains(response, 'lista-antiga.csv')

    def test_operational_settings_can_update_whatsapp_repeat_window(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('operational-settings'), {'repeat_block_hours': '12'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            OperationalRuntimeSetting.objects.get(key='whatsapp_repeat_block_hours').value,
            '12',
        )

    def test_operational_settings_can_import_contacts_csv(self):
        self.client.force_login(self.user)
        contacts_file = SimpleUploadedFile(
            'contatos.csv',
            b'Nome,Telefone,Email\nMaria Silva,(11) 99888-7766,maria@example.com\n',
            content_type='text/csv',
        )

        response = self.client.post(
            reverse('operational-settings'),
            {
                'source_platform': 'whatsapp',
                'declared_range': 'up_to_200',
                'contacts_file': contacts_file,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1 contatos importados com sucesso.')
        self.assertTrue(StudentIntake.objects.filter(full_name='Maria Silva').exists())
        job = LeadImportJob.objects.get(created_by=self.user)
        self.assertEqual(job.processing_mode, LeadImportProcessingMode.SYNC)
        self.assertEqual(job.status, LeadImportJobStatus.COMPLETED)

    def test_operational_settings_persists_duplicate_log_for_sync_import(self):
        self.client.force_login(self.user)
        StudentIntake.objects.create(
            full_name='Lead Existente',
            phone='5511998887766',
            email='existente@example.com',
        )
        contacts_file = SimpleUploadedFile(
            'contatos_duplicados.csv',
            b'Nome,Telefone,Email\nMaria Silva,(11) 99888-7766,maria@example.com\n',
            content_type='text/csv',
        )

        response = self.client.post(
            reverse('operational-settings'),
            {
                'source_platform': 'whatsapp',
                'declared_range': 'up_to_200',
                'contacts_file': contacts_file,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1 contatos ja existiam no banco e foram ignorados.')
        job = LeadImportJob.objects.get(created_by=self.user)
        self.assertEqual(job.status, LeadImportJobStatus.COMPLETED_WITH_WARNINGS)
        self.assertEqual(job.duplicate_count, 1)
        self.assertEqual(job.duplicate_details[0]['reason'], 'duplicate_in_database_phone')
        self.assertEqual(job.duplicate_details[0]['normalized_phone'], '5511998887766')

    @patch('guide.views.run_lead_import_job.delay')
    def test_operational_settings_routes_medium_import_to_background(self, delay_mock):
        self.client.force_login(self.user)
        rows = [
            f'Aluno {index},(11) 97000-{index:04d},lead{index}@example.com'
            for index in range(1, 250)
        ]
        contacts_file = SimpleUploadedFile(
            'contatos_medios.csv',
            ('Nome,Telefone,Email\n' + '\n'.join(rows) + '\n').encode('utf-8'),
            content_type='text/csv',
        )

        response = self.client.post(
            reverse('operational-settings'),
            {
                'source_platform': 'tecnofit',
                'declared_range': 'from_201_to_500',
                'contacts_file': contacts_file,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sua importacao foi enviada para processamento em background.')
        job = LeadImportJob.objects.get(created_by=self.user)
        self.assertEqual(job.processing_mode, LeadImportProcessingMode.ASYNC_NOW)
        self.assertEqual(job.status, LeadImportJobStatus.QUEUED)
        delay_mock.assert_called_once_with(job.id)

    def test_operational_settings_shows_policy_rejection_message(self):
        self.client.force_login(self.user)
        rows = [
            f'Aluno {index},(11) 98000-{index:04d},lead{index}@example.com'
            for index in range(1, 2050)
        ]
        contacts_file = SimpleUploadedFile(
            'contatos_grandes.csv',
            ('Nome,Telefone,Email\n' + '\n'.join(rows) + '\n').encode('utf-8'),
            content_type='text/csv',
        )

        response = self.client.post(
            reverse('operational-settings'),
            {
                'source_platform': 'whatsapp',
                'declared_range': 'from_501_to_2000',
                'contacts_file': contacts_file,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Este arquivo excede o limite de 2000 leads para importacao.')
        job = LeadImportJob.objects.get(created_by=self.user)
        self.assertEqual(job.status, LeadImportJobStatus.REJECTED)

    def test_dev_workspace_renders_signal_mesh_board_only_for_dev(self):
        dev_user = get_user_model().objects.create_user(
            username='dev-runtime',
            email='dev-runtime@example.com',
            password='senha-forte-123',
        )
        dev_group, _ = Group.objects.get_or_create(name='DEV')
        dev_user.groups.add(dev_group)
        self.client.force_login(dev_user)

        response = self.client.get(reverse('dev-workspace'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Estado operacional do Red Beacon')
        self.assertContains(response, 'Red Beacon')

    def test_dashboard_and_owner_workspace_do_not_render_red_beacon_anymore(self):
        self.client.force_login(self.user)

        dashboard_response = self.client.get(reverse('dashboard'))
        owner_response = self.client.get(reverse('owner-workspace'))

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertEqual(owner_response.status_code, 200)
        self.assertNotContains(dashboard_response, 'Estado operacional do Red Beacon')
        self.assertNotContains(owner_response, 'Estado operacional do Red Beacon')

    def test_student_invitation_operations_renders_for_owner(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('student-invitation-operations'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Convites operacionais prontos.')
        self.assertContains(response, 'Gerar convite do app do aluno')
        self.assertContains(
            response,
            admin_changelist_url('student_identity', 'studentappinvitation'),
        )

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
                'invite_type': StudentInvitationType.INDIVIDUAL,
                'expires_in_days': '7',
            },
        )

        self.assertEqual(response.status_code, 302)
        invitation = StudentAppInvitation.objects.get(student=student)
        self.assertEqual(invitation.invited_email, 'aluno.convite@example.com')
        self.assertEqual(invitation.invite_type, StudentInvitationType.INDIVIDUAL)
        self.assertGreater(invitation.expires_at, timezone.now())

    def test_student_invitation_operations_renders_pending_membership_board(self):
        self.client.force_login(self.user)
        student = Student.objects.create(
            full_name='Aluno Pendente Operacional',
            phone='5511932109876',
            email='pendente.operacional@example.com',
        )
        box_root_slug = get_box_runtime_slug()
        identity = StudentIdentity.objects.create(
            student=student,
            box_root_slug=box_root_slug,
            primary_box_root_slug=box_root_slug,
            provider=StudentIdentityProvider.GOOGLE,
            provider_subject='google-pendente-operacional',
            email='pendente.operacional@example.com',
            status=StudentIdentityStatus.ACTIVE,
        )
        invitation = StudentAppInvitation.objects.create(
            student=student,
            invited_email='pendente.operacional@example.com',
            invite_type=StudentInvitationType.OPEN_BOX,
            box_root_slug=box_root_slug,
            expires_at=timezone.now() + timezone.timedelta(days=7),
            created_by=self.user,
        )
        StudentBoxMembership.objects.create(
            identity=identity,
            student=student,
            box_root_slug=box_root_slug,
            status=StudentBoxMembershipStatus.PENDING_APPROVAL,
            created_from_invite=invitation,
        )

        response = self.client.get(reverse('student-invitation-operations'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alunos que fecharam a identidade e agora esperam o box')
        self.assertContains(response, 'Aluno Pendente Operacional')
        self.assertContains(response, 'Aprovar acesso')

    @override_settings(
        STUDENT_OPEN_BOX_INVITE_LIMIT_PER_WINDOW=2,
        STUDENT_OPEN_BOX_INVITE_WINDOW_HOURS=24,
    )
    def test_student_invitation_operations_renders_observability_alert_when_open_box_window_is_hot(self):
        self.client.force_login(self.user)
        student = Student.objects.create(
            full_name='Aluno Janela Quente',
            phone='5511931112222',
            email='janela.quente@example.com',
        )
        StudentAppInvitation.objects.create(
            student=student,
            invited_email='janela.quente@example.com',
            invite_type=StudentInvitationType.OPEN_BOX,
            box_root_slug=get_box_runtime_slug(),
            expires_at=timezone.now() + timezone.timedelta(days=7),
            created_by=self.user,
        )
        StudentAppInvitation.objects.create(
            student=student,
            invited_email='janela.quente@example.com',
            invite_type=StudentInvitationType.OPEN_BOX,
            box_root_slug=get_box_runtime_slug(),
            expires_at=timezone.now() + timezone.timedelta(days=7),
            created_by=self.user,
        )

        response = self.client.get(reverse('student-invitation-operations'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Painel de temperatura dos convites')
        self.assertContains(response, '2/2')
        self.assertContains(response, 'limite tecnico de convites abertos')

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
