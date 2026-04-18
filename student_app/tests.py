from datetime import timedelta
from decimal import Decimal
import json
import uuid

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from operations.models import Attendance, AttendanceStatus, ClassSession
from student_app.application.use_cases import GetStudentWorkoutPrescription
from student_app.models import (
    SessionWorkout,
    SessionWorkoutBlock,
    SessionWorkoutMovement,
    SessionWorkoutStatus,
    StudentExerciseMax,
    StudentWorkoutView,
    WorkoutBlockKind,
    WorkoutLoadType,
)
from student_identity.infrastructure.session import build_student_session_value, read_student_session_value
from student_identity.models import (
    StudentBoxMembership,
    StudentBoxMembershipStatus,
    StudentIdentity,
    StudentIdentityProvider,
    StudentIdentityStatus,
)
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
            primary_box_root_slug='control',
            provider=StudentIdentityProvider.GOOGLE,
            provider_subject='provider-subject-app',
            email='app@example.com',
            status=StudentIdentityStatus.ACTIVE,
        )
        StudentBoxMembership.objects.create(
            identity=self.identity,
            student=self.student,
            box_root_slug='control',
            status=StudentBoxMembershipStatus.ACTIVE,
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
            title='Cross de terca',
            scheduled_at=timezone.now() + timedelta(days=1),
            status='scheduled',
        )
        response = self.client.get(reverse('student-app-home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Inicio')
        self.assertNotContains(response, 'Abrir menu lateral')
        self.assertContains(response, 'Cross de terca')
        self.assertContains(response, 'Box atual: control')
        self.assertNotContains(response, 'Trocar box')
        self.assertContains(response, 'Grade')
        self.assertContains(response, 'WOD')
        self.assertContains(response, 'RM')
        self.assertContains(response, 'Modo atual: Grade')

    def test_student_home_switches_to_wod_mode_when_attendance_window_is_active(self):
        session = ClassSession.objects.create(
            title='WOD das 19h',
            scheduled_at=timezone.now() + timedelta(minutes=10),
            status='open',
        )
        Attendance.objects.create(
            student=self.student,
            session=session,
            status=AttendanceStatus.BOOKED,
        )

        response = self.client.get(reverse('student-app-home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Treino de hoje ativo.')
        self.assertContains(response, 'Modo atual: WOD')
        self.assertContains(response, 'Abrir WOD')

    def test_confirm_attendance_creates_student_booking(self):
        session = ClassSession.objects.create(
            title='Aula para reservar',
            scheduled_at=timezone.now() + timedelta(hours=3),
            status='scheduled',
        )

        response = self.client.post(
            reverse('student-app-confirm-attendance'),
            {
                'session_id': str(session.id),
                'next': reverse('student-app-grade'),
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('student-app-grade'))
        attendance = Attendance.objects.get(student=self.student, session=session)
        self.assertEqual(attendance.status, AttendanceStatus.BOOKED)
        self.assertEqual(attendance.reservation_source, 'student_app')

    def test_confirm_attendance_reactivates_canceled_booking(self):
        session = ClassSession.objects.create(
            title='Aula cancelada antes',
            scheduled_at=timezone.now() + timedelta(hours=3),
            status='scheduled',
        )
        Attendance.objects.create(
            student=self.student,
            session=session,
            status=AttendanceStatus.CANCELED,
            reservation_source='legacy',
        )

        self.client.post(
            reverse('student-app-confirm-attendance'),
            {
                'session_id': str(session.id),
                'next': reverse('student-app-grade'),
            },
            follow=False,
        )

        attendance = Attendance.objects.get(student=self.student, session=session)
        self.assertEqual(attendance.status, AttendanceStatus.BOOKED)
        self.assertEqual(attendance.reservation_source, 'student_app')

    def test_student_grade_and_rm_routes_render_new_shell(self):
        StudentExerciseMax.objects.create(
            student=self.student,
            exercise_slug='deadlift',
            exercise_label='Deadlift',
            one_rep_max_kg=Decimal('100.00'),
        )

        grade_response = self.client.get(reverse('student-app-grade'))
        rm_response = self.client.get(reverse('student-app-rm'))

        self.assertEqual(grade_response.status_code, 200)
        self.assertEqual(rm_response.status_code, 200)
        self.assertContains(grade_response, 'Sua rotina no box')
        self.assertContains(grade_response, 'Proxima aula')
        self.assertContains(rm_response, 'Seus records maximos')
        self.assertContains(rm_response, 'Deadlift')

    def test_student_wod_route_keeps_workout_calculator_inside_new_shell(self):
        StudentExerciseMax.objects.create(
            student=self.student,
            exercise_slug='deadlift',
            exercise_label='Deadlift',
            one_rep_max_kg=Decimal('100.00'),
        )

        response = self.client.get(reverse('student-app-wod'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Treino do dia com leitura rapida e carga pessoal.')
        self.assertContains(response, 'Percentual do treino')
        self.assertContains(response, 'Deadlift')

    def test_student_wod_route_renders_published_workout_day(self):
        StudentExerciseMax.objects.create(
            student=self.student,
            exercise_slug='deadlift',
            exercise_label='Deadlift',
            one_rep_max_kg=Decimal('100.00'),
        )
        session = ClassSession.objects.create(
            title='Cross de hoje',
            scheduled_at=timezone.now() + timedelta(minutes=15),
            status='open',
        )
        Attendance.objects.create(
            student=self.student,
            session=session,
            status=AttendanceStatus.BOOKED,
        )
        workout = SessionWorkout.objects.create(
            session=session,
            title='Forca + Metcon',
            coach_notes='Foco em tecnica e consistencia.',
            status=SessionWorkoutStatus.PUBLISHED,
        )
        block = SessionWorkoutBlock.objects.create(
            workout=workout,
            kind=WorkoutBlockKind.STRENGTH,
            title='Forca principal',
            notes='Suba com tecnica limpa.',
            sort_order=1,
        )
        SessionWorkoutMovement.objects.create(
            block=block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sets=5,
            reps=10,
            load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            load_value=Decimal('70.00'),
            notes='Respire no topo de cada repeticao.',
            sort_order=1,
        )

        response = self.client.get(reverse('student-app-wod'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Forca + Metcon')
        self.assertContains(response, 'Cross de hoje')
        self.assertContains(response, 'Forca principal')
        self.assertContains(response, 'Deadlift')
        self.assertContains(response, '70.00 kg')
        self.assertContains(response, 'Baseado no seu RM atual de 100.00 kg.')
        workout_view = StudentWorkoutView.objects.get(student=self.student, workout=workout)
        self.assertEqual(workout_view.view_count, 1)

        second_response = self.client.get(reverse('student-app-wod'))

        self.assertEqual(second_response.status_code, 200)
        workout_view.refresh_from_db()
        self.assertEqual(workout_view.view_count, 2)

    def test_student_wod_route_ignores_draft_workout(self):
        session = ClassSession.objects.create(
            title='Cross em rascunho',
            scheduled_at=timezone.now() + timedelta(minutes=15),
            status='open',
        )
        Attendance.objects.create(
            student=self.student,
            session=session,
            status=AttendanceStatus.BOOKED,
        )
        SessionWorkout.objects.create(
            session=session,
            title='Rascunho do coach',
            coach_notes='Ainda em ajuste.',
            status=SessionWorkoutStatus.DRAFT,
        )

        response = self.client.get(reverse('student-app-wod'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Rascunho do coach')
        self.assertContains(response, 'Treino do dia com leitura rapida e carga pessoal.')

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
        payload = read_student_session_value(cookie.value)
        self.assertEqual(payload['active_box_root_slug'], 'control')
        self.assertTrue(payload['device_fingerprint'])

    def test_student_home_redirects_to_login_when_device_fingerprint_changes(self):
        warmup_response = self.client.get(reverse('student-app-home'), HTTP_USER_AGENT='OctoBox Test Browser A')
        session_cookie = warmup_response.cookies['octobox_student_session'].value
        self.client.cookies['octobox_student_session'] = session_cookie

        response = self.client.get(
            reverse('student-app-home'),
            HTTP_USER_AGENT='OctoBox Test Browser B',
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('student-identity-login'))
        self.assertIn('octobox_student_session', response.cookies)
        self.assertEqual(response.cookies['octobox_student_session'].value, '')

    def test_student_home_shows_box_switcher_when_multiple_memberships_exist(self):
        StudentBoxMembership.objects.create(
            identity=self.identity,
            student=self.student,
            box_root_slug='box-secundario',
            status=StudentBoxMembershipStatus.ACTIVE,
        )

        response = self.client.get(reverse('student-app-home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Trocar box')
        self.assertContains(response, 'box-secundario')

    def test_switch_box_updates_active_box_in_cookie(self):
        StudentBoxMembership.objects.create(
            identity=self.identity,
            student=self.student,
            box_root_slug='box-secundario',
            status=StudentBoxMembershipStatus.ACTIVE,
        )

        response = self.client.post(
            reverse('student-app-switch-box'),
            {
                'box_root_slug': 'box-secundario',
                'next': reverse('student-app-home'),
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('student-app-home'))
        self.assertIn('octobox_student_session', response.cookies)
        payload = read_student_session_value(response.cookies['octobox_student_session'].value)
        self.assertEqual(payload['active_box_root_slug'], 'box-secundario')

    def test_student_home_redirects_to_suspended_financial_when_membership_is_suspended(self):
        membership = StudentBoxMembership.objects.get(identity=self.identity, box_root_slug='control')
        membership.status = StudentBoxMembershipStatus.SUSPENDED_FINANCIAL
        membership.save(update_fields=['status'])

        response = self.client.get(reverse('student-app-home'))

        self.assertRedirects(response, reverse('student-app-suspended-financial'))

    def test_no_active_box_page_renders_membership_statuses(self):
        membership = StudentBoxMembership.objects.get(identity=self.identity, box_root_slug='control')
        membership.status = StudentBoxMembershipStatus.REVOKED
        membership.save(update_fields=['status'])

        response = self.client.get(reverse('student-app-no-active-box'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Seu acesso esta sem nenhum box ativo agora.')
        self.assertContains(response, 'Revogado')
        self.assertContains(response, 'Entrar em outro box com convite')

    def test_runtime_falls_back_to_another_active_membership_when_current_one_is_revoked(self):
        current_membership = StudentBoxMembership.objects.get(identity=self.identity, box_root_slug='control')
        current_membership.status = StudentBoxMembershipStatus.REVOKED
        current_membership.save(update_fields=['status'])
        StudentBoxMembership.objects.create(
            identity=self.identity,
            student=self.student,
            box_root_slug='box-secundario',
            status=StudentBoxMembershipStatus.ACTIVE,
        )

        response = self.client.get(reverse('student-app-home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Box atual: box-secundario')

    def test_student_home_redirects_to_suspended_financial_page_when_all_memberships_are_suspended(self):
        membership = StudentBoxMembership.objects.get(identity=self.identity, box_root_slug='control')
        membership.status = StudentBoxMembershipStatus.SUSPENDED_FINANCIAL
        membership.save(update_fields=['status'])

        response = self.client.get(reverse('student-app-home'))

        self.assertRedirects(response, reverse('student-app-suspended-financial'))

    def test_suspended_financial_page_renders_guidance(self):
        membership = StudentBoxMembership.objects.get(identity=self.identity, box_root_slug='control')
        membership.status = StudentBoxMembershipStatus.SUSPENDED_FINANCIAL
        membership.save(update_fields=['status'])

        response = self.client.get(reverse('student-app-suspended-financial'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Seu acesso esta suspenso por agora.')
        self.assertContains(response, 'Entrar em outro box com convite')

    def test_invite_entry_redirects_from_raw_token_to_invite_landing(self):
        token = str(uuid.uuid4())

        response = self.client.post(
            reverse('student-app-enter-invite'),
            {
                'invite_token_or_url': token,
            },
        )

        self.assertRedirects(response, reverse('student-identity-invite', kwargs={'token': token}))

    def test_invite_entry_redirects_from_full_url_to_invite_landing(self):
        token = str(uuid.uuid4())
        invite_url = f'https://app.octoboxfit.com.br/aluno/auth/invite/{token}/'

        response = self.client.post(
            reverse('student-app-enter-invite'),
            {
                'invite_token_or_url': invite_url,
            },
        )

        self.assertRedirects(response, reverse('student-identity-invite', kwargs={'token': token}))
