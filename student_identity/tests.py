import base64
import hashlib
import hmac
import json
from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core import mail
from django.test import override_settings
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.http import urlencode
from django.utils import timezone

from auditing.models import AuditEvent
from operations.models import Attendance, AttendanceStatus, ClassSession
from shared_support.box_runtime import get_box_runtime_slug
from student_identity.application.commands import CreateStudentInvitationCommand, TransferStudentToBoxCommand
from student_identity.application.use_cases import CreateStudentInvitation, TransferStudentToBox
from student_identity.infrastructure.repositories import DjangoStudentIdentityRepository
from student_identity.infrastructure.session import read_student_session_value
from student_identity.models import (
    StudentAppInvitation,
    StudentBoxInviteLink,
    StudentBoxMembership,
    StudentBoxMembershipStatus,
    StudentIdentity,
    StudentIdentityProvider,
    StudentIdentityStatus,
    StudentInvitationDelivery,
    StudentInvitationDeliveryEvent,
    StudentInvitationDeliveryStatus,
    StudentInvitationType,
    StudentOnboardingJourney,
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
        cache.clear()
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

    def _build_google_provider_mock(self, *, email: str, provider_subject: str):
        provider = Mock()
        provider.exchange_code.return_value = Mock(
            provider='google',
            email=email,
            provider_subject=provider_subject,
        )
        return provider

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

    @override_settings(
        STUDENT_GOOGLE_OAUTH_CLIENT_ID='google-client-id',
        STUDENT_GOOGLE_OAUTH_CLIENT_SECRET='google-client-secret',
    )
    @patch('student_identity.views.build_provider')
    def test_mass_box_invite_redirects_to_onboarding_wizard(self, build_provider_mock):
        link = StudentBoxInviteLink.objects.create(
            box_root_slug=get_box_runtime_slug(),
            expires_at=timezone.now() + timedelta(days=3),
            max_uses=200,
        )
        provider = Mock()
        provider.exchange_code.return_value = Mock(
            provider='google',
            email='novo.aluno@example.com',
            provider_subject='google-mass-box-subject',
        )
        build_provider_mock.return_value = provider

        from student_identity.oauth_state import build_oauth_state

        response = self.client.get(
            reverse('student-identity-oauth-callback', kwargs={'provider': 'google'}),
            {
                'code': 'oauth-code',
                'state': build_oauth_state(provider='google', invite_token=str(link.token)),
            },
        )

        self.assertRedirects(response, reverse('student-app-onboarding'))
        self.assertEqual(StudentIdentity.objects.count(), 0)
        pending = self.client.session.get('student_pending_onboarding', {})
        self.assertEqual(pending.get('journey'), StudentOnboardingJourney.MASS_BOX_INVITE)
        link.refresh_from_db()
        self.assertEqual(link.use_count, 1)
        self.assertTrue(
            AuditEvent.objects.filter(
                action='student_onboarding.mass_box_invite.oauth_completed',
                metadata__box_invite_link_id=link.id,
            ).exists()
        )

    @override_settings(
        STUDENT_GOOGLE_OAUTH_CLIENT_ID='google-client-id',
        STUDENT_GOOGLE_OAUTH_CLIENT_SECRET='google-client-secret',
    )
    @patch('student_identity.views.build_provider')
    def test_imported_lead_invite_redirects_to_reduced_onboarding(self, build_provider_mock):
        invitation = StudentAppInvitation.objects.create(
            student=self.student,
            invited_email='',
            onboarding_journey=StudentOnboardingJourney.IMPORTED_LEAD_INVITE,
            expires_at=timezone.now() + timedelta(days=3),
        )
        provider = Mock()
        provider.exchange_code.return_value = Mock(
            provider='google',
            email='aluno@example.com',
            provider_subject='google-imported-lead-subject',
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

        self.assertRedirects(response, reverse('student-app-onboarding'))
        pending = self.client.session.get('student_pending_onboarding', {})
        self.assertEqual(pending.get('journey'), StudentOnboardingJourney.IMPORTED_LEAD_INVITE)
        identity = StudentIdentity.objects.get(student=self.student)
        self.assertEqual(identity.provider_subject, 'google-imported-lead-subject')
        self.assertTrue(
            AuditEvent.objects.filter(
                action='student_onboarding.imported_lead_invite.oauth_completed',
                metadata__invitation_id=invitation.id,
            ).exists()
        )

    @override_settings(
        STUDENT_GOOGLE_OAUTH_CLIENT_ID='google-client-id',
        STUDENT_GOOGLE_OAUTH_CLIENT_SECRET='google-client-secret',
    )
    @patch('student_identity.views.build_provider')
    def test_registered_student_invite_redirects_directly_to_app_with_funnel_events(self, build_provider_mock):
        invitation = StudentAppInvitation.objects.create(
            student=self.student,
            invited_email='aluno@example.com',
            onboarding_journey=StudentOnboardingJourney.REGISTERED_STUDENT_INVITE,
            expires_at=timezone.now() + timedelta(days=3),
        )
        provider = Mock()
        provider.exchange_code.return_value = Mock(
            provider='google',
            email='aluno@example.com',
            provider_subject='google-registered-student-subject',
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

        self.assertRedirects(response, reverse('student-app-home'))
        identity = StudentIdentity.objects.get(student=self.student)
        self.assertEqual(identity.provider_subject, 'google-registered-student-subject')
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.accepted_at)
        self.assertTrue(
            AuditEvent.objects.filter(
                action='student_onboarding.registered_student_invite.oauth_completed',
                metadata__identity_id=identity.id,
                metadata__student_id=self.student.id,
            ).exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                action='student_onboarding.registered_student_invite.app_entry_completed',
                metadata__identity_id=identity.id,
                metadata__student_id=self.student.id,
            ).exists()
        )

    @override_settings(
        STUDENT_GOOGLE_OAUTH_CLIENT_ID='google-client-id',
        STUDENT_GOOGLE_OAUTH_CLIENT_SECRET='google-client-secret',
    )
    @patch('student_identity.views.build_provider')
    def test_oauth_callback_with_invalid_invite_redirects_to_login_with_clear_message(self, build_provider_mock):
        provider = Mock()
        provider.exchange_code.return_value = Mock(
            provider='google',
            email='aluno@example.com',
            provider_subject='google-invalid-invite-subject',
        )
        build_provider_mock.return_value = provider

        from student_identity.oauth_state import build_oauth_state

        invalid_token = '33333333-3333-3333-3333-333333333333'
        response = self.client.get(
            reverse('student-identity-oauth-callback', kwargs={'provider': 'google'}),
            {
                'code': 'oauth-code',
                'state': build_oauth_state(provider='google', invite_token=invalid_token),
            },
            follow=True,
        )

        self.assertRedirects(
            response,
            f"{reverse('student-identity-login')}?invite={invalid_token}",
        )
        messages = list(response.context['messages'])
        self.assertTrue(
            any('O convite informado nao foi encontrado ou expirou. Tente entrar sem convite.' in str(message) for message in messages)
        )

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

    @override_settings(
        STUDENT_GOOGLE_OAUTH_CLIENT_ID='',
        STUDENT_APPLE_OAUTH_CLIENT_ID='',
    )
    def test_login_page_hides_social_buttons_when_provider_is_not_configured(self):
        response = self.client.get(reverse('student-identity-login'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Continuar com Google')
        self.assertNotContains(response, 'Continuar com Apple')
        self.assertContains(response, 'Entrar com usuario')
        self.assertContains(response, 'Nenhum provedor social esta disponivel agora.')
        self.assertContains(response, reverse('login-staff'))

    def test_public_login_hub_preserves_invite_token_in_student_oauth_buttons(self):
        invitation = StudentAppInvitation.objects.create(
            student=self.student,
            invited_email='aluno@example.com',
            expires_at=timezone.now() + timedelta(days=3),
        )

        response = self.client.get(reverse('login'), {'invite': str(invitation.token)})

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f"{reverse('student-identity-oauth-start', kwargs={'provider': 'google'})}?{urlencode({'invite': str(invitation.token)})}",
        )
        self.assertContains(
            response,
            f"{reverse('student-identity-oauth-start', kwargs={'provider': 'apple'})}?{urlencode({'invite': str(invitation.token)})}",
        )
        self.assertContains(response, 'Convite reconhecido.')
        self.assertContains(response, reverse('login-staff'))

    def test_invite_landing_points_student_to_student_login_with_invite_token(self):
        invitation = StudentAppInvitation.objects.create(
            student=self.student,
            invited_email='aluno@example.com',
            expires_at=timezone.now() + timedelta(days=3),
        )

        response = self.client.get(reverse('student-identity-invite', kwargs={'token': invitation.token}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"{reverse('student-identity-login')}?invite={invitation.token}")

    def test_invite_landing_shows_expired_message(self):
        invitation = StudentAppInvitation.objects.create(
            student=self.student,
            invited_email='aluno@example.com',
            expires_at=timezone.now() - timedelta(minutes=5),
        )

        response = self.client.get(reverse('student-identity-invite', kwargs={'token': invitation.token}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Este convite expirou.')

    def test_invite_landing_invalid_token_creates_audit_event(self):
        token = '22222222-2222-2222-2222-222222222222'

        response = self.client.get(reverse('student-identity-invite', kwargs={'token': token}))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            AuditEvent.objects.filter(
                action='student_invite_landing.invalid_token_accessed',
                target_label=hashlib.sha256(token.encode()).hexdigest()[:16],
            ).exists()
        )

    def test_box_invite_landing_shows_unavailable_message_when_paused(self):
        link = StudentBoxInviteLink.objects.create(
            box_root_slug=get_box_runtime_slug(),
            expires_at=timezone.now() + timedelta(days=3),
            paused_at=timezone.now(),
        )

        response = self.client.get(reverse('student-identity-box-invite', kwargs={'token': link.token}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Este link nao esta mais disponivel.')

    def test_student_login_shows_invite_context_label(self):
        invitation = StudentAppInvitation.objects.create(
            student=self.student,
            invited_email='aluno@example.com',
            expires_at=timezone.now() + timedelta(days=3),
        )

        response = self.client.get(reverse('student-identity-login'), {'invite': str(invitation.token)})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Voce esta entrando por convite do box')
        self.assertContains(response, get_box_runtime_slug().replace('-', ' ').title())

    @override_settings(
        STUDENT_GOOGLE_OAUTH_CLIENT_ID='google-client-id',
        STUDENT_GOOGLE_OAUTH_CLIENT_SECRET='google-client-secret',
    )
    @patch('student_identity.views.build_provider')
    def test_smoke_staff_creates_individual_invite_and_student_reaches_home_in_grade_mode(self, build_provider_mock):
        owner = get_user_model().objects.create_superuser(
            username='owner-smoke-grade',
            email='owner-smoke-grade@example.com',
            password='Senha@123456',
        )
        staff_client = Client()
        student_client = Client()
        staff_client.force_login(owner)
        build_provider_mock.return_value = self._build_google_provider_mock(
            email='aluno@example.com',
            provider_subject='google-smoke-grade-subject',
        )

        create_response = staff_client.post(
            reverse('student-invitation-operations'),
            {
                'student': str(self.student.id),
                'invited_email': 'aluno@example.com',
                'invite_type': StudentInvitationType.INDIVIDUAL,
                'onboarding_journey': StudentOnboardingJourney.REGISTERED_STUDENT_INVITE,
                'expires_in_days': '7',
            },
        )

        self.assertEqual(create_response.status_code, 302)
        invitation = StudentAppInvitation.objects.latest('id')

        landing_response = student_client.get(reverse('student-identity-invite', kwargs={'token': invitation.token}))
        self.assertEqual(landing_response.status_code, 200)
        self.assertContains(landing_response, f"{reverse('student-identity-login')}?invite={invitation.token}")

        from student_identity.oauth_state import build_oauth_state

        callback_response = student_client.get(
            reverse('student-identity-oauth-callback', kwargs={'provider': 'google'}),
            {
                'code': 'oauth-smoke-grade',
                'state': build_oauth_state(provider='google', invite_token=str(invitation.token)),
            },
            follow=False,
        )

        self.assertRedirects(callback_response, reverse('student-app-home'))
        home_response = student_client.get(reverse('student-app-home'))
        self.assertEqual(home_response.status_code, 200)
        self.assertContains(home_response, 'Modo atual: Grade')
        self.assertContains(home_response, 'Grade')
        membership = StudentBoxMembership.objects.get(student=self.student, box_root_slug=get_box_runtime_slug())
        self.assertEqual(membership.status, StudentBoxMembershipStatus.ACTIVE)

    @override_settings(
        STUDENT_GOOGLE_OAUTH_CLIENT_ID='google-client-id',
        STUDENT_GOOGLE_OAUTH_CLIENT_SECRET='google-client-secret',
    )
    @patch('student_identity.views.build_provider')
    def test_smoke_student_oauth_reaches_home_in_wod_mode_when_attendance_window_is_active(self, build_provider_mock):
        owner = get_user_model().objects.create_superuser(
            username='owner-smoke-wod',
            email='owner-smoke-wod@example.com',
            password='Senha@123456',
        )
        staff_client = Client()
        student_client = Client()
        staff_client.force_login(owner)
        build_provider_mock.return_value = self._build_google_provider_mock(
            email='aluno@example.com',
            provider_subject='google-smoke-wod-subject',
        )
        session = ClassSession.objects.create(
            title='WOD Smoke',
            scheduled_at=timezone.now() + timedelta(minutes=10),
            status='open',
        )
        Attendance.objects.create(
            student=self.student,
            session=session,
            status=AttendanceStatus.BOOKED,
        )

        create_response = staff_client.post(
            reverse('student-invitation-operations'),
            {
                'student': str(self.student.id),
                'invited_email': 'aluno@example.com',
                'invite_type': StudentInvitationType.INDIVIDUAL,
                'onboarding_journey': StudentOnboardingJourney.REGISTERED_STUDENT_INVITE,
                'expires_in_days': '7',
            },
        )

        self.assertEqual(create_response.status_code, 302)
        invitation = StudentAppInvitation.objects.latest('id')

        from student_identity.oauth_state import build_oauth_state

        callback_response = student_client.get(
            reverse('student-identity-oauth-callback', kwargs={'provider': 'google'}),
            {
                'code': 'oauth-smoke-wod',
                'state': build_oauth_state(provider='google', invite_token=str(invitation.token)),
            },
            follow=False,
        )

        self.assertRedirects(callback_response, reverse('student-app-home'))
        home_response = student_client.get(reverse('student-app-home'))
        self.assertEqual(home_response.status_code, 200)
        self.assertContains(home_response, 'Modo atual: WOD')
        self.assertContains(home_response, 'Treino de hoje ativo.')
        self.assertContains(home_response, 'Abrir WOD')

    @override_settings(
        STUDENT_GOOGLE_OAUTH_CLIENT_ID='google-client-id',
        STUDENT_GOOGLE_OAUTH_CLIENT_SECRET='google-client-secret',
    )
    @patch('student_identity.views.build_provider')
    def test_smoke_open_box_invite_waits_for_approval_then_student_enters_home(self, build_provider_mock):
        owner = get_user_model().objects.create_superuser(
            username='owner-smoke-open-box',
            email='owner-smoke-open-box@example.com',
            password='Senha@123456',
        )
        manager = self._create_role_user(
            username='manager-smoke-approve',
            email='manager-smoke-approve@example.com',
            role_name='Manager',
        )
        staff_client = Client()
        manager_client = Client()
        student_client = Client()
        staff_client.force_login(owner)
        manager_client.force_login(manager)
        build_provider_mock.return_value = self._build_google_provider_mock(
            email='aluno@example.com',
            provider_subject='google-smoke-open-box-subject',
        )

        create_response = staff_client.post(
            reverse('student-invitation-operations'),
            {
                'student': str(self.student.id),
                'invited_email': 'aluno@example.com',
                'invite_type': StudentInvitationType.OPEN_BOX,
                'onboarding_journey': StudentOnboardingJourney.REGISTERED_STUDENT_INVITE,
                'expires_in_days': '7',
            },
        )

        self.assertEqual(create_response.status_code, 302)
        invitation = StudentAppInvitation.objects.latest('id')

        from student_identity.oauth_state import build_oauth_state

        callback_response = student_client.get(
            reverse('student-identity-oauth-callback', kwargs={'provider': 'google'}),
            {
                'code': 'oauth-smoke-open-box',
                'state': build_oauth_state(provider='google', invite_token=str(invitation.token)),
            },
            follow=False,
        )

        self.assertRedirects(callback_response, reverse('student-app-membership-pending'))
        pending_response = student_client.get(reverse('student-app-membership-pending'))
        self.assertEqual(pending_response.status_code, 200)
        self.assertContains(pending_response, 'aguardando')

        membership = StudentBoxMembership.objects.get(student=self.student, box_root_slug=get_box_runtime_slug())
        self.assertEqual(membership.status, StudentBoxMembershipStatus.PENDING_APPROVAL)

        approve_response = manager_client.post(
            reverse('student-invitation-operations'),
            {
                'action': 'approve-membership',
                'membership_id': str(membership.id),
            },
        )

        self.assertEqual(approve_response.status_code, 302)
        membership.refresh_from_db()
        self.assertEqual(membership.status, StudentBoxMembershipStatus.ACTIVE)
        self.assertEqual(membership.approved_by_id, manager.id)

        home_response = student_client.get(reverse('student-app-home'))
        self.assertEqual(home_response.status_code, 200)
        self.assertContains(home_response, 'Modo atual: Grade')

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
                target_label=hashlib.sha256(str(invitation.token).encode()).hexdigest()[:16],
            ).exists()
        )

    @override_settings(
        STUDENT_INVITE_LANDING_RATE_LIMIT_MAX_REQUESTS=1,
        STUDENT_INVITE_LANDING_RATE_LIMIT_WINDOW_SECONDS=300,
    )
    def test_box_invite_landing_rate_limit_blocks_second_open_in_window(self):
        link = StudentBoxInviteLink.objects.create(
            box_root_slug=get_box_runtime_slug(),
            expires_at=timezone.now() + timedelta(days=3),
        )

        first_response = self.client.get(reverse('student-identity-box-invite', kwargs={'token': link.token}))
        second_response = self.client.get(reverse('student-identity-box-invite', kwargs={'token': link.token}))

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 429)
        self.assertTrue(
            AuditEvent.objects.filter(
                action='student_box_invite_landing.rate_limited',
                target_label=hashlib.sha256(str(link.token).encode()).hexdigest()[:16],
            ).exists()
        )

    def test_box_invite_landing_invalid_token_creates_audit_event(self):
        token = '11111111-1111-1111-1111-111111111111'

        response = self.client.get(reverse('student-identity-box-invite', kwargs={'token': token}))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            AuditEvent.objects.filter(
                action='student_box_invite_landing.invalid_token_accessed',
                target_label=hashlib.sha256(token.encode()).hexdigest()[:16],
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

    def test_operations_page_shows_intelligent_next_action_for_funnel(self):
        owner = get_user_model().objects.create_superuser(
            username='owner-funnel',
            email='owner-funnel@example.com',
            password='Senha@123456',
        )
        self.client.force_login(owner)
        AuditEvent.objects.create(
            actor=owner,
            actor_role='Owner',
            action='student_onboarding.mass_box_invite.landing_viewed',
            target_model='student_identity.StudentBoxInviteLink',
            target_label='control',
            description='Landing em massa aberta.',
            metadata={
                'box_root_slug': get_box_runtime_slug(),
                'journey': StudentOnboardingJourney.MASS_BOX_INVITE,
                'box_invite_link_id': 999,
            },
        )
        AuditEvent.objects.create(
            actor=owner,
            actor_role='Owner',
            action='student_onboarding.mass_box_invite.landing_viewed',
            target_model='student_identity.StudentBoxInviteLink',
            target_label='control',
            description='Landing em massa aberta.',
            metadata={
                'box_root_slug': get_box_runtime_slug(),
                'journey': StudentOnboardingJourney.MASS_BOX_INVITE,
                'box_invite_link_id': 999,
            },
        )

        response = self.client.get(reverse('student-invitation-operations'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pulso do corredor')
        self.assertContains(response, 'Proxima melhor acao: atacar visitas -&gt; oauth concluido')
        self.assertContains(response, 'O grupo esta clicando, mas pouca gente esta entrando com Google ou Apple.')

    def test_operations_page_prioritizes_stalled_invites_in_recommended_queue(self):
        owner = get_user_model().objects.create_superuser(
            username='owner-queue',
            email='owner-queue@example.com',
            password='Senha@123456',
        )
        invitation = StudentAppInvitation.objects.create(
            student=self.student,
            invited_email='aluno@example.com',
            expires_at=timezone.now() + timedelta(days=5),
            created_by=owner,
        )
        StudentInvitationDelivery.objects.create(
            invitation=invitation,
            channel='email',
            provider='smtp',
            status=StudentInvitationDeliveryStatus.BOUNCED,
            recipient='aluno@example.com',
            requested_by=owner,
            sent_at=timezone.now() - timedelta(hours=6),
            failed_at=timezone.now() - timedelta(hours=5),
            error_message='email.bounced',
        )
        self.client.force_login(owner)

        response = self.client.get(reverse('student-invitation-operations'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Prioridade do dia')
        self.assertContains(response, 'Trabalhar a fila quente do WhatsApp')
        self.assertContains(response, 'Aluno Box')
        self.assertContains(response, 'Enviar mensagem')

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

    def test_coach_can_view_operations_page_in_read_only_mode(self):
        coach = self._create_role_user(
            username='coach-readonly',
            email='coach-readonly@example.com',
            role_name='Coach',
        )
        invitation = StudentAppInvitation.objects.create(
            student=self.student,
            invited_email='aluno@example.com',
            expires_at=timezone.now() + timedelta(days=5),
        )
        StudentBoxMembership.objects.create(
            identity=StudentIdentity.objects.create(
                student=self.student,
                box_root_slug=get_box_runtime_slug(),
                primary_box_root_slug=get_box_runtime_slug(),
                provider=StudentIdentityProvider.GOOGLE,
                provider_subject='google-coach-readonly',
                email='aluno@example.com',
                status=StudentIdentityStatus.ACTIVE,
            ),
            student=self.student,
            box_root_slug=get_box_runtime_slug(),
            status=StudentBoxMembershipStatus.PENDING_APPROVAL,
            created_from_invite=invitation,
        )
        self.client.force_login(coach)

        response = self.client.get(reverse('student-invitation-operations'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Coach entra aqui em modo leitura')
        self.assertNotContains(response, 'Gerar convite individual')
        self.assertNotContains(response, 'Liberar acesso')
        self.assertNotContains(response, 'Link pronto para compartilhar')

    def test_coach_cannot_create_student_invitation_from_operations_screen(self):
        coach = self._create_role_user(
            username='coach-denied',
            email='coach-denied@example.com',
            role_name='Coach',
        )
        self.client.force_login(coach)

        response = self.client.post(
            reverse('student-invitation-operations'),
            {
                'student': str(self.student.id),
                'invited_email': 'aluno@example.com',
                'invite_type': StudentInvitationType.INDIVIDUAL,
                'onboarding_journey': StudentOnboardingJourney.REGISTERED_STUDENT_INVITE,
                'expires_in_days': '7',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(StudentAppInvitation.objects.count(), 0)
        messages = list(response.context['messages'])
        self.assertTrue(any('modo leitura' in str(message) for message in messages))

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
