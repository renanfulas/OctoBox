from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from auditing.models import AuditEvent
from onboarding.models import IntakeSource, IntakeStatus, StudentIntake
from student_identity.models import StudentAppInvitation, StudentOnboardingJourney


class IntakeCenterStudentInviteSmokeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_superuser(
            username='owner.intake.smoke',
            email='owner.intake.smoke@example.com',
            password='Senha@123456',
        )
        self.client.force_login(self.user)
        self.intake = StudentIntake.objects.create(
            full_name='Lead WhatsApp',
            phone='5511999991111',
            email='',
            source=IntakeSource.WHATSAPP,
            status=IntakeStatus.NEW,
        )

    def test_intake_center_one_click_whatsapp_invite_creates_linked_student_invitation(self):
        response = self.client.post(
            reverse('intake-center'),
            {
                'action': 'send-whatsapp-invite',
                'intake_id': self.intake.id,
                'return_query': '',
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('wa.me', response['Location'])

        self.intake.refresh_from_db()
        self.assertIsNotNone(self.intake.linked_student_id)
        self.assertEqual(self.intake.status, IntakeStatus.MATCHED)

        invitation = StudentAppInvitation.objects.get(student=self.intake.linked_student)
        self.assertEqual(invitation.onboarding_journey, StudentOnboardingJourney.IMPORTED_LEAD_INVITE)
        self.assertEqual(invitation.created_by, self.user)
        self.assertTrue(
            AuditEvent.objects.filter(
                action='student_onboarding.imported_lead_invite.whatsapp_handoff_opened',
                metadata__invitation_id=invitation.id,
                metadata__intake_id=self.intake.id,
            ).exists()
        )
