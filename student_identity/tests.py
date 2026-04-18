import base64
import hashlib
import hmac
import json
from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.test import override_settings
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from auditing.models import AuditEvent
from shared_support.box_runtime import get_box_runtime_slug
from student_identity.application.commands import CreateStudentInvitationCommand, TransferStudentToBoxCommand
from student_identity.application.use_cases import CreateStudentInvitation, TransferStudentToBox
from student_identity.infrastructure.repositories import DjangoStudentIdentityRepository
from student_identity.infrastructure.session import read_student_session_value
from student_identity.models import (
    StudentAppInvitation,
    StudentBoxMembership,
    StudentBoxMembershipStatus,
    StudentIdentity,
    StudentIdentityProvider,
    StudentIdentityStatus,
    StudentInvitationDelivery,
    StudentInvitationDeliveryEvent,
    StudentInvitationDeliveryStatus,
    StudentInvitationType,
)
from students.models import Student


def build_resend_svix_signature(*, secret: str, webhook_id: str, timestamp: str, payload: bytes) -> str:
    expected_signature = base64.b64encode(
        hmac.new(secret[len('whsec_'):].encode('utf-8'), b'.'.join([
            webhook_id.encode('utf-8'),
            timestamp.encode('utf-8'),
            payload,
        ]), hashlib.sha256).digest()
    ).decode('utf-8')
    return f'v1,{expected_signature}'


class StudentIdentityFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = Student.objects.create(
            full_name='Aluno Box',
            phone='5511999999999',
            email='aluno@example.com',
        )

    def _create_role_user(self, *, username: str, email: str, role_name: str):
        user = get_user_model().objects.create_user(
            username=username,
            email=email,
            password='Senha@123456',
        )
        group, _ = Group.objects.get_or_create(name=role_name)
        user.groups.add(group)
        return user

    @override_settings(
        STUDENT_GOOGLE_OAUTH_CLIENT_ID='google-client-id',
        STUDENT_GOOGLE_OAUTH_CLIENT_SECRET='google-client-secret',
    )
    @patch('student_identity.views.build_provider')
    def test_student_can_authenticate_with_google_callback_in_same_box(self, build_provider_mock):
        provider = Mock()
        provider.exchange_code.return_value = Mock(
            provider='google',
            email='aluno@example.com',
            provider_subject='google-subject-1',
        )
        build_provider_mock.return_value = provider

        from student_identity.oauth_state import build_oauth_state

        response = self.client.get(
            reverse('student-identity-oauth-callback', kwargs={'provider': 'google'}),
            {
                'code': 'oauth-code',
                'state': build_oauth_state(provider='google'),
            },
        )

        self.assertRedirects(response, reverse('student-app-home'))
        identity = StudentIdentity.objects.get(student=self.student)
        self.assertEqual(identity.box_root_slug, get_box_runtime_slug())
        self.assertEqual(identity.primary_box_root_slug, get_box_runtime_slug())
        self.assertEqual(identity.status, StudentIdentityStatus.ACTIVE)
        self.assertEqual(identity.provider_subject, 'google-subject-1')
        membership = StudentBoxMembership.objects.get(identity=identity, box_root_slug=get_box_runtime_slug())
        self.assertEqual(membership.status, StudentBoxMembershipStatus.ACTIVE)
        self.assertIn('octobox_student_session', response.cookies)
        session_payload = read_student_session_value(response.cookies['octobox_student_session'].value)
        self.assertTrue(session_payload['device_fingerprint'])

    @override_settings(
        STUDENT_APPLE_OAUTH_CLIENT_ID='com.octobox.student',
        STUDENT_APPLE_OAUTH_TEAM_ID='TEAM123',
        STUDENT_APPLE_OAUTH_KEY_ID='KEY123',
        STUDENT_APPLE_OAUTH_PRIVATE_KEY='apple-private-key-placeholder',
    )
    @patch('student_identity.views.build_provider')
    def test_student_can_authenticate_with_apple_invitation_when_student_email_is_blank(self, build_provider_mock):
        student = Student.objects.create(
            full_name='Convite Box',
            phone='5511888888888',
            email='',
        )
        invitation = StudentAppInvitation.objects.create(
            student=student,
            invited_email='convite@example.com',
            expires_at=timezone.now() + timedelta(days=3),
        )
        provider = Mock()
        provider.exchange_code.return_value = Mock(
            provider='apple',
            email='convite@example.com',
            provider_subject='apple-subject-1',
        )
        build_provider_mock.return_value = provider

        from student_identity.oauth_state import build_oauth_state

        response = self.client.post(
            reverse('student-identity-oauth-callback', kwargs={'provider': 'apple'}),
            {
                'code': 'apple-code',
                'state': build_oauth_state(provider='apple', invite_token=str(invitation.token)),
            },
        )

        self.assertRedirects(response, reverse('student-app-home'))
        identity = StudentIdentity.objects.get(student=student)
        self.assertEqual(identity.email, 'convite@example.com')
        self.assertEqual(identity.primary_box_root_slug, get_box_runtime_slug())
        student.refresh_from_db()
        self.assertEqual(student.email, 'convite@example.com')
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.accepted_at)
        membership = StudentBoxMembership.objects.get(identity=identity, box_root_slug=get_box_runtime_slug())
        self.assertEqual(membership.created_from_invite_id, invitation.id)
        self.assertEqual(membership.status, StudentBoxMembershipStatus.ACTIVE)

    @override_settings(
        STUDENT_GOOGLE_OAUTH_CLIENT_ID='google-client-id',
        STUDENT_GOOGLE_OAUTH_CLIENT_SECRET='google-client-secret',
    )
    @patch('student_identity.views.build_provider')
    def test_open_box_invite_redirects_student_to_membership_pending(self, build_provider_mock):
        invitation = StudentAppInvitation.objects.create(
            student=self.student,
            invited_email='aluno@example.com',
            invite_type=StudentInvitationType.OPEN_BOX,
            expires_at=timezone.now() + timedelta(days=3),
        )
        provider = Mock()
        provider.exchange_code.return_value = Mock(
            provider='google',
            email='aluno@example.com',
            provider_subject='google-open-box-subject',
        )
        build_provider_mock.return_value = provider

        from student_identity.oauth_state import build_oauth_state

        response = self.client.get(
            reverse('student-identity-oauth-callback', kwargs={'provider': 'google'}),
            {
                'code': 'oauth-code',
                'state': build_oauth_state(provider='google', invite_token=str(invitation.token)),
            },
        )

        self.assertRedirects(response, reverse('student-app-membership-pending'))
        identity = StudentIdentity.objects.get(student=self.student)
        membership = StudentBoxMembership.objects.get(identity=identity, box_root_slug=get_box_runtime_slug())
        self.assertEqual(membership.status, StudentBoxMembershipStatus.PENDING_APPROVAL)
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.accepted_at)

    def test_transfer_student_moves_box_root_without_creating_second_house(self):
        identity = StudentIdentity.objects.create(
            student=self.student,
            box_root_slug='box-raiz-a',
            provider=StudentIdentityProvider.GOOGLE,
            provider_subject='provider-subject-a',
            email='aluno@example.com',
            status=StudentIdentityStatus.ACTIVE,
        )
        actor = get_user_model().objects.create_user(
            username='owner.transfer',
            email='owner.transfer@example.com',
            password='Senha@123456',
        )

        result = TransferStudentToBox(DjangoStudentIdentityRepository()).execute(
            TransferStudentToBoxCommand(
                identity_id=identity.id,
                to_box_root_slug='box-raiz-b',
                actor_id=actor.id,
                reason='Mudanca operacional de unidade.',
            )
        )

        self.assertTrue(result.success)
        identity.refresh_from_db()
        self.assertEqual(identity.box_root_slug, 'box-raiz-b')
        self.assertEqual(identity.primary_box_root_slug, 'box-raiz-b')
        self.assertEqual(StudentIdentity.objects.filter(student=self.student).count(), 1)
        old_membership = StudentBoxMembership.objects.get(identity=identity, box_root_slug='box-raiz-a')
        new_membership = StudentBoxMembership.objects.get(identity=identity, box_root_slug='box-raiz-b')
        self.assertEqual(old_membership.status, StudentBoxMembershipStatus.INACTIVE)
        self.assertEqual(new_membership.status, StudentBoxMembershipStatus.ACTIVE)

    @override_settings(STUDENT_GOOGLE_OAUTH_CLIENT_ID='google-client-id')
    def test_oauth_start_redirects_to_provider(self):
        response = self.client.get(reverse('student-identity-oauth-start', kwargs={'provider': 'google'}))
        self.assertEqual(response.status_code, 302)
        self.assertIn('accounts.google.com', response['Location'])

    @override_settings(
        STUDENT_GOOGLE_OAUTH_CLIENT_ID='google-client-id',
        STUDENT_OAUTH_PUBLIC_BASE_URL='https://student-oauth.example.com',
    )
    def test_oauth_start_uses_public_base_url_when_configured(self):
        response = self.client.get(reverse('student-identity-oauth-start', kwargs={'provider': 'google'}))

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            'redirect_uri=https%3A%2F%2Fstudent-oauth.example.com%2Faluno%2Fauth%2Foauth%2Fgoogle%2Fcallback%2F',
            response['Location'],
        )

    def test_login_page_keeps_social_buttons_clickable_without_provider_config(self):
        response = self.client.get(reverse('student-identity-login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Continuar com Google')
        self.assertContains(response, 'Continuar com Apple')
        self.assertNotContains(response, 'aria-disabled="true"')
        self.assertContains(response, reverse('student-identity-oauth-start', kwargs={'provider': 'google'}))
        self.assertContains(response, reverse('student-identity-oauth-start', kwargs={'provider': 'apple'}))

    @override_settings(
        STUDENT_GOOGLE_OAUTH_CLIENT_ID='',
        STUDENT_GOOGLE_OAUTH_CLIENT_SECRET='',
    )
    def test_oauth_start_returns_with_message_when_google_is_not_configured(self):
        response = self.client.get(reverse('student-identity-oauth-start', kwargs={'provider': 'google'}), follow=True)

        self.assertRedirects(response, reverse('student-identity-login'))
        messages = list(response.context['messages'])
        self.assertTrue(any('Google ainda nao foi configurado' in str(message) for message in messages))

    @override_settings(
        STUDENT_APPLE_OAUTH_CLIENT_ID='',
        STUDENT_APPLE_OAUTH_TEAM_ID='',
        STUDENT_APPLE_OAUTH_KEY_ID='',
        STUDENT_APPLE_OAUTH_PRIVATE_KEY='',
    )
    def test_oauth_start_returns_with_message_when_apple_is_not_configured(self):
        response = self.client.get(reverse('student-identity-oauth-start', kwargs={'provider': 'apple'}), follow=True)

        self.assertRedirects(response, reverse('student-identity-login'))
        messages = list(response.context['messages'])
        self.assertTrue(any('Apple ainda nao foi configurada' in str(message) for message in messages))

    def test_create_student_invitation_revokes_previous_open_invite(self):
        actor = get_user_model().objects.create_user(
            username='owner.convite',
            email='owner.convite@example.com',
            password='Senha@123456',
        )
        previous_invitation = StudentAppInvitation.objects.create(
            student=self.student,
            invited_email='aluno@example.com',
            expires_at=timezone.now() + timedelta(days=5),
        )

        result = CreateStudentInvitation(DjangoStudentIdentityRepository()).execute(
            CreateStudentInvitationCommand(
                student_id=self.student.id,
                invited_email='aluno@example.com',
                box_root_slug=get_box_runtime_slug(),
                expires_in_days=7,
                actor_id=actor.id,
            )
        )

        self.assertTrue(result.success)
        self.assertIsNotNone(result.invitation)
        previous_invitation.refresh_from_db()
        self.assertTrue(previous_invitation.is_expired)
        self.assertEqual(StudentAppInvitation.objects.filter(student=self.student).count(), 2)

    @override_settings(
        STUDENT_OPEN_BOX_INVITE_LIMIT_PER_WINDOW=1,
        STUDENT_OPEN_BOX_INVITE_WINDOW_HOURS=24,
    )
    def test_open_box_invite_rate_limit_blocks_second_open_invite_in_window(self):
        actor = get_user_model().objects.create_user(
            username='owner.open-box-limit',
            email='owner.open-box-limit@example.com',
            password='Senha@123456',
        )
        StudentAppInvitation.objects.create(
            student=self.student,
            invited_email='aluno@example.com',
            invite_type=StudentInvitationType.OPEN_BOX,
            box_root_slug=get_box_runtime_slug(),
            expires_at=timezone.now() + timedelta(days=5),
            created_by=actor,
        )

        result = CreateStudentInvitation(DjangoStudentIdentityRepository()).execute(
            CreateStudentInvitationCommand(
                student_id=self.student.id,
                invited_email='aluno@example.com',
                box_root_slug=get_box_runtime_slug(),
                invite_type=StudentInvitationType.OPEN_BOX,
                expires_in_days=7,
                actor_id=actor.id,
            )
        )

        self.assertFalse(result.success)
        self.assertEqual(result.failure_reason, 'open-box-rate-limit-exceeded')

    @override_settings(
        STUDENT_INVITE_LANDING_RATE_LIMIT_MAX_REQUESTS=1,
        STUDENT_INVITE_LANDING_RATE_LIMIT_WINDOW_SECONDS=300,
    )
    def test_invite_landing_rate_limit_blocks_second_open_in_window(self):
        invitation = StudentAppInvitation.objects.create(
            student=self.student,
            invited_email='aluno@example.com',
            expires_at=timezone.now() + timedelta(days=3),
        )

        first_response = self.client.get(reverse('student-identity-invite', kwargs={'token': invitation.token}))
        second_response = self.client.get(reverse('student-identity-invite', kwargs={'token': invitation.token}))

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 429)
        self.assertTrue(
            AuditEvent.objects.filter(
                action='student_invite_landing.rate_limited',
                target_label=str(invitation.token),
            ).exists()
        )

    @override_settings(
        STUDENT_GOOGLE_OAUTH_CLIENT_ID='google-client-id',
        STUDENT_GOOGLE_OAUTH_CLIENT_SECRET='google-client-secret',
        STUDENT_OAUTH_CALLBACK_RATE_LIMIT_MAX_REQUESTS=1,
        STUDENT_OAUTH_CALLBACK_RATE_LIMIT_WINDOW_SECONDS=300,
    )
    @patch('student_identity.views.build_provider')
    def test_oauth_callback_rate_limit_blocks_second_attempt_from_same_ip(self, build_provider_mock):
        provider = Mock()
        provider.exchange_code.return_value = Mock(
            provider='google',
            email='aluno@example.com',
            provider_subject='google-rate-limit-subject',
        )
        build_provider_mock.return_value = provider

        from student_identity.oauth_state import build_oauth_state

        callback_url = reverse('student-identity-oauth-callback', kwargs={'provider': 'google'})
        first_response = self.client.get(
            callback_url,
            {'code': 'oauth-code-1', 'state': build_oauth_state(provider='google')},
        )
        second_response = self.client.get(
            callback_url,
            {'code': 'oauth-code-2', 'state': build_oauth_state(provider='google')},
        )

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(second_response.status_code, 429)
        self.assertTrue(
            AuditEvent.objects.filter(
                action='student_oauth_callback.rate_limited',
                target_label='google',
            ).exists()
        )

    @override_settings(
        STUDENT_INVITE_CREATION_ACTOR_ALERT_THRESHOLD=1,
        STUDENT_INVITE_CREATION_ACTOR_ALERT_WINDOW_SECONDS=900,
        STUDENT_INVITE_CREATION_BOX_ALERT_THRESHOLD=99,
        STUDENT_INVITE_CREATION_BOX_ALERT_WINDOW_SECONDS=900,
    )
    def test_invite_creation_anomaly_alert_fires_for_actor_burst(self):
        owner = get_user_model().objects.create_superuser(
            username='owner-anomaly',
            email='owner-anomaly@example.com',
            password='Senha@123456',
        )
        self.client.force_login(owner)

        first_student = Student.objects.create(
            full_name='Primeiro Burst',
            phone='5511666666661',
            email='primeiro.burst@example.com',
        )
        second_student = Student.objects.create(
            full_name='Segundo Burst',
            phone='5511666666662',
            email='segundo.burst@example.com',
        )

        first_response = self.client.post(
            reverse('student-invitation-operations'),
            {
                'student': str(first_student.id),
                'invited_email': 'primeiro.burst@example.com',
                'invite_type': StudentInvitationType.INDIVIDUAL,
                'expires_in_days': '7',
            },
        )
        second_response = self.client.post(
            reverse('student-invitation-operations'),
            {
                'student': str(second_student.id),
                'invited_email': 'segundo.burst@example.com',
                'invite_type': StudentInvitationType.INDIVIDUAL,
                'expires_in_days': '7',
            },
        )

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(second_response.status_code, 302)
        self.assertTrue(
            AuditEvent.objects.filter(
                action='student_security.anomaly_detected',
                target_label=str(owner.id),
            ).exists()
        )

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_owner_can_send_student_invitation_email_from_operations_screen(self):
        owner = get_user_model().objects.create_superuser(
            username='owner-mail',
            email='owner-mail@example.com',
            password='Senha@123456',
        )
        invitation = StudentAppInvitation.objects.create(
            student=self.student,
            invited_email='aluno@example.com',
            expires_at=timezone.now() + timedelta(days=5),
            created_by=owner,
        )
        self.client.force_login(owner)

        response = self.client.post(
            reverse('student-invitation-operations'),
            {
                'action': 'send-email',
                'invitation_id': str(invitation.id),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Seu acesso ao app do aluno', mail.outbox[0].subject)
        self.assertIn(str(invitation.token), mail.outbox[0].body)
        delivery = StudentInvitationDelivery.objects.get(invitation=invitation)
        self.assertEqual(delivery.status, StudentInvitationDeliveryStatus.SENT)
        self.assertEqual(delivery.provider, 'smtp')
        self.assertTrue(
            AuditEvent.objects.filter(action='student_invitation.delivery.sent', target_id=str(invitation.id)).exists()
        )

    @override_settings(STUDENT_EMAIL_PROVIDER='resend', STUDENT_RESEND_API_KEY='resend-key', STUDENT_EMAIL_FROM='no-reply@example.com')
    @patch('student_identity.delivery_gateways.ResendStudentEmailGateway.send')
    def test_owner_can_send_student_invitation_email_with_resend_provider(self, resend_send_mock):
        owner = get_user_model().objects.create_superuser(
            username='owner-resend',
            email='owner-resend@example.com',
            password='Senha@123456',
        )
        invitation = StudentAppInvitation.objects.create(
            student=self.student,
            invited_email='aluno@example.com',
            expires_at=timezone.now() + timedelta(days=5),
            created_by=owner,
        )
        resend_send_mock.return_value = Mock(
            provider='resend',
            recipient='aluno@example.com',
            provider_message_id='email_123',
            metadata={'response': {'id': 'email_123'}},
        )
        self.client.force_login(owner)

        response = self.client.post(
            reverse('student-invitation-operations'),
            {
                'action': 'send-email',
                'invitation_id': str(invitation.id),
            },
        )

        self.assertEqual(response.status_code, 302)
        delivery = StudentInvitationDelivery.objects.get(invitation=invitation)
        self.assertEqual(delivery.provider, 'resend')
        self.assertEqual(delivery.provider_message_id, 'email_123')

    def test_owner_can_open_whatsapp_invitation_with_audit_trail(self):
        owner = get_user_model().objects.create_superuser(
            username='owner-whatsapp',
            email='owner-whatsapp@example.com',
            password='Senha@123456',
        )
        invitation = StudentAppInvitation.objects.create(
            student=self.student,
            invited_email='aluno@example.com',
            expires_at=timezone.now() + timedelta(days=5),
            created_by=owner,
        )
        self.client.force_login(owner)

        response = self.client.post(
            reverse('student-invitation-operations'),
            {
                'action': 'open-whatsapp',
                'invitation_id': str(invitation.id),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('wa.me/', response['Location'])
        whatsapp_delivery = StudentInvitationDelivery.objects.filter(
            invitation=invitation,
            channel='whatsapp',
            provider='whatsapp_link',
        ).latest('created_at')
        self.assertEqual(whatsapp_delivery.status, StudentInvitationDeliveryStatus.SENT)
        self.assertTrue(
            AuditEvent.objects.filter(
                action='student_invitation.whatsapp.handoff',
                target_id=str(invitation.id),
            ).exists()
        )

    def test_owner_can_approve_pending_membership_from_operations_screen(self):
        owner = get_user_model().objects.create_superuser(
            username='owner-approve',
            email='owner-approve@example.com',
            password='Senha@123456',
        )
        identity = StudentIdentity.objects.create(
            student=self.student,
            box_root_slug=get_box_runtime_slug(),
            primary_box_root_slug=get_box_runtime_slug(),
            provider=StudentIdentityProvider.GOOGLE,
            provider_subject='google-pending-approval',
            email='aluno@example.com',
            status=StudentIdentityStatus.ACTIVE,
        )
        invitation = StudentAppInvitation.objects.create(
            student=self.student,
            invited_email='aluno@example.com',
            invite_type=StudentInvitationType.OPEN_BOX,
            box_root_slug=get_box_runtime_slug(),
            expires_at=timezone.now() + timedelta(days=5),
            created_by=owner,
        )
        membership = StudentBoxMembership.objects.create(
            identity=identity,
            student=self.student,
            box_root_slug=get_box_runtime_slug(),
            status=StudentBoxMembershipStatus.PENDING_APPROVAL,
            created_from_invite=invitation,
        )
        self.client.force_login(owner)

        response = self.client.post(
            reverse('student-invitation-operations'),
            {
                'action': 'approve-membership',
                'membership_id': str(membership.id),
            },
        )

        self.assertEqual(response.status_code, 302)
        membership.refresh_from_db()
        self.assertEqual(membership.status, StudentBoxMembershipStatus.ACTIVE)
        self.assertEqual(membership.approved_by_id, owner.id)
        self.assertIsNotNone(membership.approved_at)

    def test_reception_can_change_student_email_once_per_month(self):
        reception = self._create_role_user(
            username='recepcao-email-1',
            email='recepcao-email-1@example.com',
            role_name='Recepcao',
        )
        identity = StudentIdentity.objects.create(
            student=self.student,
            box_root_slug=get_box_runtime_slug(),
            primary_box_root_slug=get_box_runtime_slug(),
            provider=StudentIdentityProvider.GOOGLE,
            provider_subject='google-email-first-change',
            email='aluno@example.com',
            status=StudentIdentityStatus.ACTIVE,
        )
        membership = StudentBoxMembership.objects.create(
            identity=identity,
            student=self.student,
            box_root_slug=get_box_runtime_slug(),
            status=StudentBoxMembershipStatus.ACTIVE,
        )
        self.client.force_login(reception)

        response = self.client.post(
            reverse('student-invitation-operations'),
            {
                'action': 'change-email',
                'membership_id': str(membership.id),
                'new_email': 'novo.aluno@example.com',
                'change_reason': 'Aluno atualizou o e-mail principal.',
            },
        )

        self.assertEqual(response.status_code, 302)
        identity.refresh_from_db()
        self.student.refresh_from_db()
        self.assertEqual(identity.email, 'novo.aluno@example.com')
        self.assertEqual(self.student.email, 'novo.aluno@example.com')
        self.assertTrue(
            AuditEvent.objects.filter(
                action='student_identity.email_changed',
                target_id=str(identity.id),
                actor_id=reception.id,
            ).exists()
        )

    def test_second_reception_email_change_in_month_requires_manager_or_owner(self):
        reception = self._create_role_user(
            username='recepcao-email-2',
            email='recepcao-email-2@example.com',
            role_name='Recepcao',
        )
        identity = StudentIdentity.objects.create(
            student=self.student,
            box_root_slug=get_box_runtime_slug(),
            primary_box_root_slug=get_box_runtime_slug(),
            provider=StudentIdentityProvider.GOOGLE,
            provider_subject='google-email-second-change',
            email='aluno@example.com',
            status=StudentIdentityStatus.ACTIVE,
        )
        membership = StudentBoxMembership.objects.create(
            identity=identity,
            student=self.student,
            box_root_slug=get_box_runtime_slug(),
            status=StudentBoxMembershipStatus.ACTIVE,
        )
        AuditEvent.objects.create(
            actor=reception,
            actor_role='Recepcao',
            action='student_identity.email_changed',
            target_model='student_identity.StudentIdentity',
            target_id=str(identity.id),
            target_label=self.student.full_name,
            description='Primeira troca do mes.',
            metadata={'old_email': 'aluno@example.com', 'new_email': 'primeiro@example.com'},
        )
        self.client.force_login(reception)

        response = self.client.post(
            reverse('student-invitation-operations'),
            {
                'action': 'change-email',
                'membership_id': str(membership.id),
                'new_email': 'segunda.troca@example.com',
                'change_reason': 'Tentativa de segunda troca no mes.',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        identity.refresh_from_db()
        self.assertEqual(identity.email, 'aluno@example.com')
        messages = list(response.context['messages'])
        self.assertTrue(any('segunda troca de e-mail' in str(message) for message in messages))

    def test_manager_can_override_second_email_change(self):
        manager = self._create_role_user(
            username='manager-email-1',
            email='manager-email-1@example.com',
            role_name='Manager',
        )
        identity = StudentIdentity.objects.create(
            student=self.student,
            box_root_slug=get_box_runtime_slug(),
            primary_box_root_slug=get_box_runtime_slug(),
            provider=StudentIdentityProvider.GOOGLE,
            provider_subject='google-manager-email-change',
            email='aluno@example.com',
            status=StudentIdentityStatus.ACTIVE,
        )
        membership = StudentBoxMembership.objects.create(
            identity=identity,
            student=self.student,
            box_root_slug=get_box_runtime_slug(),
            status=StudentBoxMembershipStatus.ACTIVE,
        )
        self.client.force_login(manager)

        response = self.client.post(
            reverse('student-invitation-operations'),
            {
                'action': 'change-email',
                'membership_id': str(membership.id),
                'new_email': 'manager.override@example.com',
                'change_reason': 'Correcao autorizada pela gerencia.',
            },
        )

        self.assertEqual(response.status_code, 302)
        identity.refresh_from_db()
        self.assertEqual(identity.email, 'manager.override@example.com')

    def test_owner_can_suspend_membership_financially(self):
        owner = get_user_model().objects.create_superuser(
            username='owner-suspend',
            email='owner-suspend@example.com',
            password='Senha@123456',
        )
        identity = StudentIdentity.objects.create(
            student=self.student,
            box_root_slug=get_box_runtime_slug(),
            primary_box_root_slug=get_box_runtime_slug(),
            provider=StudentIdentityProvider.GOOGLE,
            provider_subject='google-suspend-financial',
            email='aluno@example.com',
            status=StudentIdentityStatus.ACTIVE,
        )
        membership = StudentBoxMembership.objects.create(
            identity=identity,
            student=self.student,
            box_root_slug=get_box_runtime_slug(),
            status=StudentBoxMembershipStatus.ACTIVE,
        )
        self.client.force_login(owner)

        response = self.client.post(
            reverse('student-invitation-operations'),
            {
                'action': 'suspend-membership',
                'membership_id': str(membership.id),
            },
        )

        self.assertEqual(response.status_code, 302)
        membership.refresh_from_db()
        self.assertEqual(membership.status, StudentBoxMembershipStatus.SUSPENDED_FINANCIAL)
        self.assertTrue(
            AuditEvent.objects.filter(
                action='student_membership.suspended_financial',
                target_id=str(membership.id),
            ).exists()
        )

    def test_reception_cannot_suspend_membership_financially(self):
        reception = self._create_role_user(
            username='recepcao-suspend',
            email='recepcao-suspend@example.com',
            role_name='Recepcao',
        )
        identity = StudentIdentity.objects.create(
            student=self.student,
            box_root_slug=get_box_runtime_slug(),
            primary_box_root_slug=get_box_runtime_slug(),
            provider=StudentIdentityProvider.GOOGLE,
            provider_subject='google-reception-suspend-denied',
            email='aluno@example.com',
            status=StudentIdentityStatus.ACTIVE,
        )
        membership = StudentBoxMembership.objects.create(
            identity=identity,
            student=self.student,
            box_root_slug=get_box_runtime_slug(),
            status=StudentBoxMembershipStatus.ACTIVE,
        )
        self.client.force_login(reception)

        response = self.client.post(
            reverse('student-invitation-operations'),
            {
                'action': 'suspend-membership',
                'membership_id': str(membership.id),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        membership.refresh_from_db()
        self.assertEqual(membership.status, StudentBoxMembershipStatus.ACTIVE)
        messages = list(response.context['messages'])
        self.assertTrue(any('Suspensao financeira exige Manager, Owner ou DEV' in str(message) for message in messages))

    def test_owner_revoke_promotes_another_active_membership_to_primary(self):
        owner = get_user_model().objects.create_superuser(
            username='owner-revoke',
            email='owner-revoke@example.com',
            password='Senha@123456',
        )
        identity = StudentIdentity.objects.create(
            student=self.student,
            box_root_slug='control',
            primary_box_root_slug='control',
            provider=StudentIdentityProvider.GOOGLE,
            provider_subject='google-revoke-fallback',
            email='aluno@example.com',
            status=StudentIdentityStatus.ACTIVE,
        )
        target_membership = StudentBoxMembership.objects.create(
            identity=identity,
            student=self.student,
            box_root_slug=get_box_runtime_slug(),
            status=StudentBoxMembershipStatus.ACTIVE,
        )
        fallback_membership = StudentBoxMembership.objects.create(
            identity=identity,
            student=self.student,
            box_root_slug='box-secundario',
            status=StudentBoxMembershipStatus.ACTIVE,
        )
        identity.box_root_slug = target_membership.box_root_slug
        identity.primary_box_root_slug = target_membership.box_root_slug
        identity.save(update_fields=['box_root_slug', 'primary_box_root_slug'])
        self.client.force_login(owner)

        response = self.client.post(
            reverse('student-invitation-operations'),
            {
                'action': 'revoke-membership',
                'membership_id': str(target_membership.id),
                'revoke_reason': 'Encerramento operacional.',
            },
        )

        self.assertEqual(response.status_code, 302)
        target_membership.refresh_from_db()
        identity.refresh_from_db()
        fallback_membership.refresh_from_db()
        self.assertEqual(target_membership.status, StudentBoxMembershipStatus.REVOKED)
        self.assertEqual(identity.primary_box_root_slug, fallback_membership.box_root_slug)
        self.assertEqual(identity.box_root_slug, fallback_membership.box_root_slug)

    @override_settings(STUDENT_RESEND_WEBHOOK_SECRET='whsec_test_secret')
    def test_resend_webhook_marks_delivery_as_delivered(self):
        delivery = StudentInvitationDelivery.objects.create(
            invitation=StudentAppInvitation.objects.create(
                student=self.student,
                invited_email='aluno@example.com',
                expires_at=timezone.now() + timedelta(days=5),
            ),
            channel='email',
            provider='resend',
            status=StudentInvitationDeliveryStatus.SENT,
            recipient='aluno@example.com',
            provider_message_id='email_123',
            sent_at=timezone.now(),
        )
        payload = json.dumps(
            {
                'type': 'email.delivered',
                'created_at': timezone.now().isoformat(),
                'data': {
                    'email_id': 'email_123',
                    'to': ['aluno@example.com'],
                    'created_at': timezone.now().isoformat(),
                },
            }
        ).encode('utf-8')
        webhook_id = 'msg_delivery_1'
        timestamp = str(int(timezone.now().timestamp()))

        response = self.client.post(
            reverse('api-v1-resend-student-invitations-webhook'),
            data=payload,
            content_type='application/json',
            **{
                'HTTP_SVIX_ID': webhook_id,
                'HTTP_SVIX_TIMESTAMP': timestamp,
                'HTTP_SVIX_SIGNATURE': build_resend_svix_signature(
                    secret='whsec_test_secret',
                    webhook_id=webhook_id,
                    timestamp=timestamp,
                    payload=payload,
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, StudentInvitationDeliveryStatus.DELIVERED)
        self.assertTrue(StudentInvitationDeliveryEvent.objects.filter(provider_event_id=webhook_id).exists())

    @override_settings(STUDENT_RESEND_WEBHOOK_SECRET='whsec_test_secret')
    def test_resend_webhook_marks_delivery_as_bounced(self):
        delivery = StudentInvitationDelivery.objects.create(
            invitation=StudentAppInvitation.objects.create(
                student=self.student,
                invited_email='aluno@example.com',
                expires_at=timezone.now() + timedelta(days=5),
            ),
            channel='email',
            provider='resend',
            status=StudentInvitationDeliveryStatus.SENT,
            recipient='aluno@example.com',
            provider_message_id='email_bounce_1',
            sent_at=timezone.now(),
        )
        payload = json.dumps(
            {
                'type': 'email.bounced',
                'created_at': timezone.now().isoformat(),
                'data': {
                    'email_id': 'email_bounce_1',
                    'to': ['aluno@example.com'],
                },
            }
        ).encode('utf-8')
        webhook_id = 'msg_bounce_1'
        timestamp = str(int(timezone.now().timestamp()))

        response = self.client.post(
            reverse('api-v1-resend-student-invitations-webhook'),
            data=payload,
            content_type='application/json',
            **{
                'HTTP_SVIX_ID': webhook_id,
                'HTTP_SVIX_TIMESTAMP': timestamp,
                'HTTP_SVIX_SIGNATURE': build_resend_svix_signature(
                    secret='whsec_test_secret',
                    webhook_id=webhook_id,
                    timestamp=timestamp,
                    payload=payload,
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, StudentInvitationDeliveryStatus.BOUNCED)
        self.assertEqual(delivery.error_message, 'email.bounced')

    @override_settings(STUDENT_RESEND_WEBHOOK_SECRET='whsec_test_secret')
    def test_resend_webhook_rejects_invalid_signature(self):
        payload = json.dumps(
            {
                'type': 'email.delivered',
                'created_at': timezone.now().isoformat(),
                'data': {'email_id': 'email_invalid_sig'},
            }
        ).encode('utf-8')

        response = self.client.post(
            reverse('api-v1-resend-student-invitations-webhook'),
            data=payload,
            content_type='application/json',
            **{
                'HTTP_SVIX_ID': 'msg_invalid_sig',
                'HTTP_SVIX_TIMESTAMP': str(int(timezone.now().timestamp())),
                'HTTP_SVIX_SIGNATURE': 'v1,invalid-signature',
            },
        )

        self.assertEqual(response.status_code, 400)

    @override_settings(STUDENT_RESEND_WEBHOOK_SECRET='whsec_test_secret')
    def test_resend_webhook_ignores_duplicate_event_id(self):
        StudentInvitationDelivery.objects.create(
            invitation=StudentAppInvitation.objects.create(
                student=self.student,
                invited_email='aluno@example.com',
                expires_at=timezone.now() + timedelta(days=5),
            ),
            channel='email',
            provider='resend',
            status=StudentInvitationDeliveryStatus.SENT,
            recipient='aluno@example.com',
            provider_message_id='email_dup_1',
            sent_at=timezone.now(),
        )
        payload = json.dumps(
            {
                'type': 'email.delivered',
                'created_at': timezone.now().isoformat(),
                'data': {'email_id': 'email_dup_1'},
            }
        ).encode('utf-8')
        webhook_id = 'msg_dup_1'
        timestamp = str(int(timezone.now().timestamp()))
        headers = {
            'HTTP_SVIX_ID': webhook_id,
            'HTTP_SVIX_TIMESTAMP': timestamp,
            'HTTP_SVIX_SIGNATURE': build_resend_svix_signature(
                secret='whsec_test_secret',
                webhook_id=webhook_id,
                timestamp=timestamp,
                payload=payload,
            ),
        }

        first_response = self.client.post(
            reverse('api-v1-resend-student-invitations-webhook'),
            data=payload,
            content_type='application/json',
            **headers,
        )
        second_response = self.client.post(
            reverse('api-v1-resend-student-invitations-webhook'),
            data=payload,
            content_type='application/json',
            **headers,
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(StudentInvitationDeliveryEvent.objects.filter(provider_event_id=webhook_id).count(), 1)
