from datetime import timedelta
from decimal import Decimal
import json

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from operations.models import ClassSession
from student_app.application.use_cases import GetStudentWorkoutPrescription
from student_app.models import StudentExerciseMax
from student_identity.infrastructure.session import build_student_session_value
from student_identity.models import StudentIdentity, StudentIdentityProvider, StudentIdentityStatus
from students.models import Student


class StudentAppExperienceTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = Student.objects.create(
            full_name='Atleta App',
            phone='5511777777777',
            email='app@example.com',
        )
        self.identity = StudentIdentity.objects.create(
            student=self.student,
            box_root_slug='control',
            provider=StudentIdentityProvider.GOOGLE,
            provider_subject='provider-subject-app',
            email='app@example.com',
            status=StudentIdentityStatus.ACTIVE,
        )
        self.client.cookies['octobox_student_session'] = build_student_session_value(
            identity_id=self.identity.id,
            box_root_slug='control',
        )

    def test_student_home_requires_student_identity_cookie(self):
        anonymous_client = Client()
        response = anonymous_client.get(reverse('student-app-home'))
        self.assertRedirects(response, reverse('student-identity-login'))

    def test_student_home_renders_without_staff_shell(self):
        ClassSession.objects.create(
            title='Cross de terça',
            scheduled_at=timezone.now() + timedelta(days=1),
            status='scheduled',
        )
        response = self.client.get(reverse('student-app-home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Meu Box')
        self.assertNotContains(response, 'Abrir menu lateral')
        self.assertContains(response, 'Cross de terça')

    def test_workout_prescription_returns_expected_rounded_load(self):
        StudentExerciseMax.objects.create(
            student=self.student,
            exercise_slug='deadlift',
            exercise_label='Deadlift',
            one_rep_max_kg=Decimal('100.00'),
        )

        result = GetStudentWorkoutPrescription().execute(
            student=self.student,
            exercise_slug='deadlift',
            percentage=Decimal('75'),
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.rounded_load_label, '75.00 kg')

    def test_student_manifest_and_service_worker_are_available(self):
        manifest_response = self.client.get(reverse('student-app-manifest'))
        sw_response = self.client.get(reverse('student-app-sw'))

        self.assertEqual(manifest_response.status_code, 200)
        self.assertEqual(manifest_response['Content-Type'], 'application/manifest+json')
        self.assertEqual(sw_response.status_code, 200)
        self.assertEqual(sw_response['Service-Worker-Allowed'], '/aluno/')
        self.assertIn('/aluno/offline/', sw_response.content.decode('utf-8'))
        manifest_payload = json.loads(manifest_response.content.decode('utf-8'))
        self.assertEqual(manifest_payload['scope'], '/aluno/')
        self.assertEqual(manifest_payload['display'], 'standalone')
        self.assertEqual(manifest_payload['short_name'], 'OctoBox')
        self.assertEqual(len(manifest_payload['icons']), 3)
        self.assertEqual(manifest_payload['icons'][0]['src'], '/static/images/student-app-icon-192.png')
        self.assertIn('/static/images/student-app-icon-maskable-512.png', sw_response.content.decode('utf-8'))

    def test_student_home_refreshes_student_session_cookie(self):
        response = self.client.get(reverse('student-app-home'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('octobox_student_session', response.cookies)
        cookie = response.cookies['octobox_student_session']
        self.assertEqual(cookie['path'], '/aluno/')
        self.assertTrue(cookie['httponly'])
