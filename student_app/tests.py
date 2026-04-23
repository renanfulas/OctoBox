from datetime import date, timedelta
from decimal import Decimal
import json
import uuid
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from auditing.models import AuditEvent
from operations.models import Attendance, AttendanceStatus, ClassSession
from student_app.application.use_cases import GetStudentDashboard, GetStudentWorkoutPrescription
from student_app.models import (
    SessionWorkout,
    SessionWorkoutBlock,
    SessionWorkoutMovement,
    SessionWorkoutStatus,
    StudentAppActivity,
    StudentAppActivityKind,
    StudentExerciseMax,
    StudentExerciseMaxHistory,
    StudentWorkoutView,
    WorkoutBlockKind,
    WorkoutLoadType,
)
from student_identity.infrastructure.session import build_student_session_value, read_student_session_value
from student_identity.models import (
    StudentAppInvitation,
    StudentBoxInviteLink,
    StudentBoxMembership,
    StudentBoxMembershipStatus,
    StudentIdentity,
    StudentIdentityProvider,
    StudentPushSubscription,
    StudentIdentityStatus,
    StudentOnboardingJourney,
)
from students.models import Student, StudentStatus


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

    def _set_mass_onboarding_session(
        self,
        client,
        *,
        provider_subject='provider-subject-new-mass',
        email='novo@app.com',
    ):
        link = StudentBoxInviteLink.objects.create(
            box_root_slug='control',
            expires_at=timezone.now() + timedelta(days=3),
            max_uses=200,
        )
        session = client.session
        session['student_pending_onboarding'] = {
            'journey': StudentOnboardingJourney.MASS_BOX_INVITE,
            'box_root_slug': 'control',
            'provider': StudentIdentityProvider.GOOGLE,
            'provider_subject': provider_subject,
            'email': email,
            'box_invite_link_id': link.id,
        }
        session.save()
        return link

    def test_student_home_requires_student_identity_cookie(self):
        anonymous_client = Client()
        response = anonymous_client.get(reverse('student-app-home'))
        self.assertRedirects(response, reverse('student-identity-login'))

    def test_student_routes_redirect_to_onboarding_when_pending_onboarding_exists(self):
        invitation = StudentAppInvitation.objects.create(
            student=self.student,
            box_root_slug='control',
            invited_email=self.identity.email,
            onboarding_journey=StudentOnboardingJourney.IMPORTED_LEAD_INVITE,
            expires_at=timezone.now() + timedelta(days=3),
        )
        session = self.client.session
        session['student_pending_onboarding'] = {
            'journey': StudentOnboardingJourney.IMPORTED_LEAD_INVITE,
            'box_root_slug': 'control',
            'identity_id': self.identity.id,
            'student_id': self.student.id,
            'invitation_id': invitation.id,
            'email': self.identity.email,
        }
        session.save()

        response = self.client.get(reverse('student-app-home'))

        self.assertRedirects(response, reverse('student-app-onboarding'))

    def test_student_profile_edit_updates_student_and_identity_email(self):
        response = self.client.post(
            reverse('student-app-settings'),
            {
                'full_name': 'Atleta Atualizada',
                'phone': '5511777777778',
                'email': 'nova@app.com',
                'birth_date': '1998-04-03',
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('student-app-settings'))
        self.student.refresh_from_db()
        self.identity.refresh_from_db()
        self.assertEqual(self.student.full_name, 'Atleta Atualizada')
        self.assertEqual(self.student.email, 'nova@app.com')
        self.assertEqual(self.identity.email, 'nova@app.com')

    def test_mass_onboarding_creates_student_and_identity(self):
        client = Client()
        link = self._set_mass_onboarding_session(client)

        response = client.post(
            reverse('student-app-onboarding'),
            {
                'full_name': 'Novo Aluno App',
                'phone': '5511888888888',
                'birth_date': '02/01/2000',
                'selected_plan': '',
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('student-app-home'))
        identity = StudentIdentity.objects.get(provider_subject='provider-subject-new-mass')
        self.assertEqual(identity.email, 'novo@app.com')
        self.assertEqual(identity.student.full_name, 'Novo Aluno App')
        membership = StudentBoxMembership.objects.get(identity=identity, box_root_slug='control')
        self.assertEqual(membership.status, StudentBoxMembershipStatus.ACTIVE)
        self.assertTrue(
            AuditEvent.objects.filter(
                action='student_onboarding.mass_box_invite.wizard_started',
                metadata__box_invite_link_id=link.id,
            ).exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                action='student_onboarding.mass_box_invite.wizard_completed',
                metadata__identity_id=identity.id,
            ).exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                action='student_onboarding.mass_box_invite.app_entry_completed',
                metadata__identity_id=identity.id,
            ).exists()
        )

    def test_mass_onboarding_renders_hardened_input_attrs(self):
        client = Client()
        self._set_mass_onboarding_session(client)

        response = client.get(reverse('student-app-onboarding'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'maxlength="150"', html=False)
        self.assertContains(response, 'minlength="5"', html=False)
        self.assertContains(response, 'autocomplete="tel"', html=False)
        self.assertContains(response, 'pattern="[0-9]{10,20}"', html=False)
        self.assertContains(response, 'placeholder="dd/mm/aaaa"', html=False)
        self.assertContains(response, 'data-min-year="1900"', html=False)
        self.assertContains(response, 'data-max-year="2026"', html=False)
        self.assertNotContains(response, '<span>E-mail</span>', html=False)
        self.assertContains(response, 'Seu e-mail sera o mesmo validado no OAuth', html=False)

    def test_mass_onboarding_rejects_invalid_phone_payload(self):
        client = Client()
        self._set_mass_onboarding_session(client, provider_subject='provider-subject-invalid-phone')

        response = client.post(
            reverse('student-app-onboarding'),
            {
                'full_name': 'Novo Aluno App',
                'phone': '12',
                'birth_date': '02/01/2000',
                'selected_plan': '',
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Informe um WhatsApp valido com DDD.')
        self.assertFalse(StudentIdentity.objects.filter(provider_subject='provider-subject-invalid-phone').exists())

    def test_mass_onboarding_rejects_birth_date_after_max_year(self):
        client = Client()
        self._set_mass_onboarding_session(client, provider_subject='provider-subject-future-birth')

        response = client.post(
            reverse('student-app-onboarding'),
            {
                'full_name': 'Novo Aluno App',
                'phone': '5511888888888',
                'birth_date': '01/01/2027',
                'selected_plan': '',
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'O ano da data de nascimento precisa ficar entre 1900 e 2026.')
        self.assertFalse(StudentIdentity.objects.filter(provider_subject='provider-subject-future-birth').exists())

    def test_mass_onboarding_accepts_masked_phone_and_saves_clean_digits(self):
        client = Client()
        self._set_mass_onboarding_session(client, provider_subject='provider-subject-masked-phone')

        response = client.post(
            reverse('student-app-onboarding'),
            {
                'full_name': 'Novo Aluno Mascara',
                'phone': '+55 (11) 98888-7777',
                'birth_date': '02/01/2000',
                'selected_plan': '',
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        identity = StudentIdentity.objects.get(provider_subject='provider-subject-masked-phone')
        self.assertEqual(identity.student.phone, '11988887777')

    def test_imported_lead_onboarding_updates_student_and_records_funnel_events(self):
        client = Client()
        student = Student.objects.create(
            full_name='Lead Importado',
            phone='5511666666666',
            email='',
            status=StudentStatus.LEAD,
        )
        identity = StudentIdentity.objects.create(
            student=student,
            box_root_slug='control',
            primary_box_root_slug='control',
            provider=StudentIdentityProvider.GOOGLE,
            provider_subject='provider-subject-imported-lead',
            email='lead@app.com',
            status=StudentIdentityStatus.ACTIVE,
        )
        StudentBoxMembership.objects.create(
            identity=identity,
            student=student,
            box_root_slug='control',
            status=StudentBoxMembershipStatus.ACTIVE,
        )
        client.cookies['octobox_student_session'] = build_student_session_value(
            identity_id=identity.id,
            box_root_slug='control',
        )
        invitation = StudentAppInvitation.objects.create(
            student=student,
            box_root_slug='control',
            invited_email='lead@app.com',
            onboarding_journey=StudentOnboardingJourney.IMPORTED_LEAD_INVITE,
            expires_at=timezone.now() + timedelta(days=3),
        )
        session = client.session
        session['student_pending_onboarding'] = {
            'journey': StudentOnboardingJourney.IMPORTED_LEAD_INVITE,
            'box_root_slug': 'control',
            'student_id': student.id,
            'identity_id': identity.id,
            'invitation_id': invitation.id,
            'email': 'lead@app.com',
        }
        session.save()

        response = client.post(
            reverse('student-app-onboarding'),
            {
                'full_name': 'Lead Revisado',
                'phone': '5511666667777',
                'birth_date': '06/05/1999',
                'selected_plan': '',
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('student-app-home'))
        student.refresh_from_db()
        self.assertEqual(student.full_name, 'Lead Revisado')
        self.assertEqual(student.phone, '11666667777')
        self.assertEqual(student.status, StudentStatus.ACTIVE)
        self.assertTrue(
            AuditEvent.objects.filter(
                action='student_onboarding.imported_lead_invite.wizard_started',
                metadata__invitation_id=invitation.id,
            ).exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                action='student_onboarding.imported_lead_invite.wizard_completed',
                metadata__identity_id=identity.id,
            ).exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                action='student_onboarding.imported_lead_invite.app_entry_completed',
                metadata__identity_id=identity.id,
            ).exists()
        )

    def test_onboarding_redirects_to_login_when_session_is_missing(self):
        client = Client()

        response = client.get(reverse('student-app-onboarding'), follow=False)

        self.assertRedirects(response, reverse('student-identity-login'), fetch_redirect_response=False)

    def test_onboarding_redirects_to_login_when_pending_payload_is_incomplete(self):
        client = Client()
        session = client.session
        session['student_pending_onboarding'] = {
            'journey': StudentOnboardingJourney.MASS_BOX_INVITE,
            'provider': StudentIdentityProvider.GOOGLE,
        }
        session.save()

        response = client.get(reverse('student-app-onboarding'), follow=False)

        self.assertRedirects(response, reverse('student-identity-login'), fetch_redirect_response=False)

    def test_onboarding_redirects_to_login_when_imported_lead_payload_is_semantically_inconsistent(self):
        client = Client()
        another_student = Student.objects.create(
            full_name='Outro Aluno',
            phone='5511666661234',
            email='outro@app.com',
        )
        session = client.session
        session['student_pending_onboarding'] = {
            'journey': StudentOnboardingJourney.IMPORTED_LEAD_INVITE,
            'box_root_slug': 'control',
            'identity_id': self.identity.id,
            'student_id': another_student.id,
            'invitation_id': 999,
            'email': self.identity.email,
        }
        session.save()

        response = client.get(reverse('student-app-onboarding'), follow=False)

        self.assertRedirects(response, reverse('student-identity-login'), fetch_redirect_response=False)

    def test_onboarding_redirects_to_login_when_mass_invite_payload_points_to_wrong_box_link(self):
        client = Client()
        session = client.session
        session['student_pending_onboarding'] = {
            'journey': StudentOnboardingJourney.MASS_BOX_INVITE,
            'box_root_slug': 'control',
            'provider': StudentIdentityProvider.GOOGLE,
            'provider_subject': 'provider-subject-mass-mismatch',
            'email': 'novo@app.com',
            'box_invite_link_id': 123456,
        }
        session.save()

        response = client.get(reverse('student-app-onboarding'), follow=False)

        self.assertRedirects(response, reverse('student-identity-login'), fetch_redirect_response=False)

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
        self.assertContains(response, 'Proxima acao')
        self.assertContains(response, 'class="student-primary-action"', html=False)
        self.assertContains(response, 'class="student-progress-strip"', html=False)
        self.assertContains(response, 'data-theme="light"', html=False)
        self.assertContains(response, 'data-ui="student-theme-toggle"', html=False)
        self.assertContains(response, 'octobox-theme', html=False)
        self.assertContains(response, '/static/js/student_app/theme.js', html=False)

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
        self.assertContains(response, 'WOD das 19h')
        self.assertContains(response, 'Modo WOD')
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
        activity = StudentAppActivity.objects.get(student=self.student, kind=StudentAppActivityKind.ATTENDANCE_CONFIRMED)
        self.assertEqual(activity.source_object_id, session.id)

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
        self.assertContains(grade_response, 'Sem aula agora')
        self.assertContains(grade_response, 'Proximas')
        self.assertContains(rm_response, 'Seus RMs')
        self.assertContains(rm_response, 'Deadlift')

    def test_student_rm_create_and_update_record_history_and_activity(self):
        add_response = self.client.post(
            reverse('student-app-rm-add'),
            {
                'exercise_label': 'Deadlift',
                'one_rep_max_kg': '100.00',
            },
            follow=False,
        )

        self.assertEqual(add_response.status_code, 302)
        record = StudentExerciseMax.objects.get(student=self.student, exercise_slug='deadlift')
        created_history = StudentExerciseMaxHistory.objects.get(student=self.student, exercise_slug='deadlift')
        self.assertIsNone(created_history.previous_kg)
        self.assertEqual(created_history.new_kg, Decimal('100.00'))
        self.assertEqual(created_history.delta_kg, Decimal('0.00'))
        self.assertTrue(
            StudentAppActivity.objects.filter(
                student=self.student,
                kind=StudentAppActivityKind.RM_CREATED,
                source_object_id=record.id,
            ).exists()
        )

        update_response = self.client.post(
            reverse('student-app-rm-update', kwargs={'pk': record.id}),
            {'one_rep_max_kg': '105.00'},
            follow=False,
        )

        self.assertEqual(update_response.status_code, 302)
        latest_history = StudentExerciseMaxHistory.objects.filter(student=self.student, exercise_slug='deadlift').latest('created_at')
        self.assertEqual(latest_history.previous_kg, Decimal('100.00'))
        self.assertEqual(latest_history.new_kg, Decimal('105.00'))
        self.assertEqual(latest_history.delta_kg, Decimal('5.00'))
        self.assertTrue(
            StudentAppActivity.objects.filter(
                student=self.student,
                kind=StudentAppActivityKind.RM_UPDATED,
                source_object_id=record.id,
            ).exists()
        )

    def test_student_session_attendees_renders_for_visible_session(self):
        session = ClassSession.objects.create(
            title='Cross visivel',
            scheduled_at=timezone.now() + timedelta(hours=2),
            status='scheduled',
        )
        mate = Student.objects.create(
            full_name='Colega de Box',
            phone='5511999990001',
            email='colega@example.com',
        )
        Attendance.objects.create(
            student=mate,
            session=session,
            status=AttendanceStatus.BOOKED,
        )

        response = self.client.get(reverse('student-app-session-attendees', kwargs={'session_id': session.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cross visivel')
        self.assertContains(response, 'Colega')

    def test_student_session_attendees_blocks_session_outside_visible_dashboard(self):
        for offset in range(5):
            ClassSession.objects.create(
                title=f'Cross visivel {offset}',
                scheduled_at=timezone.now() + timedelta(hours=offset + 1),
                status='scheduled',
            )
        hidden_session = ClassSession.objects.create(
            title='Cross fora do radar',
            scheduled_at=timezone.now() + timedelta(hours=12),
            status='scheduled',
        )

        response = self.client.get(
            reverse('student-app-session-attendees', kwargs={'session_id': hidden_session.id}),
            follow=False,
        )

        self.assertEqual(response.status_code, 404)

    def test_student_wod_route_keeps_workout_calculator_inside_new_shell(self):
        StudentExerciseMax.objects.create(
            student=self.student,
            exercise_slug='deadlift',
            exercise_label='Deadlift',
            one_rep_max_kg=Decimal('100.00'),
        )

        response = self.client.get(reverse('student-app-wod'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'WOD ainda nao publicado.')
        self.assertContains(response, 'Percentual')
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
        self.assertContains(response, 'Forca principal')
        self.assertContains(response, 'Deadlift')
        self.assertContains(response, '70.00 kg')
        self.assertContains(response, '70,00% do seu RM 100,00 kg')
        workout_view = StudentWorkoutView.objects.get(student=self.student, workout=workout)
        self.assertEqual(workout_view.view_count, 1)
        self.assertTrue(
            StudentAppActivity.objects.filter(
                student=self.student,
                kind=StudentAppActivityKind.WOD_VIEWED,
                source_object_id=workout.id,
            ).exists()
        )
        dashboard = GetStudentDashboard().execute(identity=self.identity)
        self.assertEqual(dashboard.primary_action.kind, 'open_wod')
        self.assertEqual(dashboard.rm_of_the_day.exercise_slug, 'deadlift')
        self.assertEqual(dashboard.rm_of_the_day.recommended_load_kg, Decimal('70.00'))
        self.assertEqual(len(dashboard.progress_days), 7)
        self.assertTrue(any(day.is_complete for day in dashboard.progress_days))
        self.assertEqual(dashboard.next_useful_context, 'WOD ativo agora')

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
        self.assertContains(response, 'WOD ainda nao publicado.')

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
        self.assertIn('/static/js/student_app/theme.js', sw_response.content.decode('utf-8'))
        self.assertIn('/static/css/student_app/shell/shell.css', sw_response.content.decode('utf-8'))
        self.assertIn('/static/css/student_app/primitives/card.css', sw_response.content.decode('utf-8'))
        self.assertIn('/static/css/design-system/tokens.css', sw_response.content.decode('utf-8'))

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

    def test_student_home_renders_pwa_activation_rail(self):
        response = self.client.get(reverse('student-app-home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-ui="student-pwa-activation"', html=False)
        self.assertContains(response, 'Instale o OctoBox no celular e libere as notificacoes.', html=False)
        self.assertContains(response, 'data-ui="student-pwa-install-action"', html=False)
        self.assertContains(response, 'data-ui="student-pwa-notification-action"', html=False)

    def test_student_topbar_profile_lives_inside_avatar(self):
        response = self.client.get(reverse('student-app-home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="student-avatar student-avatar-link"', html=False)
        self.assertContains(response, 'aria-label="Abrir perfil e configuracoes"', html=False)
        self.assertContains(response, '<svg class="theme-toggle-icon"', html=False)
        self.assertNotContains(response, 'class="student-topbar-link">Perfil</a>', html=False)

    @override_settings(
        STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY='test-public-key',
        STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY='test-private-key',
        STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT='mailto:teste@octoboxfit.com.br',
    )
    @patch('student_app.views.pwa_views.send_student_web_push_notification', return_value=True)
    def test_student_push_subscribe_persists_subscription(self, send_push_mock):
        response = self.client.post(
            reverse('student-app-push-subscribe'),
            data=json.dumps(
                {
                    'subscription': {
                        'endpoint': 'https://push.example.test/subscription-1',
                        'expirationTime': None,
                        'keys': {
                            'p256dh': 'test-p256dh',
                            'auth': 'test-auth',
                        },
                    }
                }
            ),
            content_type='application/json',
            HTTP_USER_AGENT='OctoBox Browser Teste',
        )

        self.assertEqual(response.status_code, 200)
        subscription = StudentPushSubscription.objects.get(endpoint='https://push.example.test/subscription-1')
        self.assertEqual(subscription.identity, self.identity)
        self.assertEqual(subscription.box_root_slug, 'control')
        self.assertEqual(subscription.subscription['keys']['auth'], 'test-auth')
        send_push_mock.assert_called_once()

    def test_student_push_unsubscribe_revokes_subscription(self):
        subscription = StudentPushSubscription.objects.create(
            identity=self.identity,
            box_root_slug='control',
            endpoint='https://push.example.test/subscription-2',
            subscription={
                'endpoint': 'https://push.example.test/subscription-2',
                'keys': {'p256dh': 'key-a', 'auth': 'key-b'},
            },
        )

        response = self.client.post(
            reverse('student-app-push-unsubscribe'),
            data=json.dumps({'endpoint': subscription.endpoint}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        subscription.refresh_from_db()
        self.assertIsNotNone(subscription.revoked_at)

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


class PublicWorkoutPwaTests(TestCase):
    def test_public_workout_pages_are_open_without_login(self):
        juliana_response = self.client.get('/renan/juliana')
        bruno_response = self.client.get('/renan/bruno')

        self.assertEqual(juliana_response.status_code, 200)
        self.assertEqual(bruno_response.status_code, 200)
        self.assertContains(juliana_response, 'Juliana Alves')
        self.assertContains(bruno_response, 'Bruno Fulas')
        self.assertContains(juliana_response, "/renan/juliana/manifest.webmanifest")
        self.assertContains(bruno_response, "/renan/bruno/manifest.webmanifest")
        self.assertContains(juliana_response, "/renan/sw.js")
        self.assertContains(bruno_response, "/renan/sw.js")

    def test_public_workout_manifest_is_dynamic_per_slug(self):
        response = self.client.get(reverse('public-workout-manifest', kwargs={'plan_slug': 'juliana'}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/manifest+json')
        payload = json.loads(response.content.decode('utf-8'))
        self.assertEqual(payload['name'], 'Treino Juliana')
        self.assertEqual(payload['id'], '/renan/juliana')
        self.assertEqual(payload['short_name'], 'Juliana')
        self.assertEqual(payload['start_url'], '/renan/juliana?source=pwa')
        self.assertEqual(payload['scope'], '/renan/')
        self.assertEqual(len(payload['icons']), 3)

    def test_public_workout_service_worker_and_offline_route_are_available(self):
        sw_response = self.client.get(reverse('public-workout-sw'))
        offline_response = self.client.get(reverse('public-workout-offline'))
        sw_content = sw_response.content.decode('utf-8')

        self.assertEqual(sw_response.status_code, 200)
        self.assertEqual(sw_response['Service-Worker-Allowed'], '/renan/')
        self.assertIn('/renan/juliana', sw_content)
        self.assertIn('/renan/juliana/manifest.webmanifest', sw_content)
        self.assertIn('/renan/bruno', sw_content)
        self.assertIn('/renan/bruno/manifest.webmanifest', sw_content)
        self.assertIn('/renan/offline/', sw_content)
        self.assertIn('const PAGE_CACHE', sw_content)
        self.assertIn('normalizedWorkoutPath', sw_content)
        self.assertIn("'/renan/juliana?source=pwa'", sw_content)
        self.assertEqual(offline_response.status_code, 200)
        self.assertContains(offline_response, 'Sem conexão agora.')

    def test_public_workout_page_renders_install_cta(self):
        response = self.client.get('/renan/juliana')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'public-workout-install')
        self.assertContains(response, 'beforeinstallprompt')
        self.assertContains(response, 'Adicionar à Tela de Início')

    def test_juliana_week_order_reflects_rest_on_friday(self):
        response = self.client.get('/renan/juliana')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "goDay('qua',this)")
        self.assertContains(response, '<div class="dn">Qua</div><div class="dt">Superior</div>', html=True)
        self.assertContains(response, '<div class="dn">Qui</div><div class="dt">Lower</div>', html=True)
        self.assertContains(response, '<div class="dn">Sex</div><div class="dt">Rest</div>', html=True)
        self.assertContains(response, 'Quarta · ~55 min · Peito, Costas, Ombros, Bíceps, Tríceps')
        self.assertContains(response, 'Quinta · ~60 min · Quad, Posterior, Glúteo, Panturrilha, Core')


class StudentAuthMiddlewareTests(TestCase):
    def setUp(self):
        self.anonymous_client = Client()

    def test_anonymous_access_to_student_app_root_redirects_to_student_login(self):
        response = self.anonymous_client.get(reverse('student-app-home'))
        self.assertRedirects(response, reverse('student-identity-login'))
        self.assertTrue(
            AuditEvent.objects.filter(action='student_app.anonymous_access_redirected').exists()
        )

    def test_anonymous_access_to_student_onboarding_redirects_with_message(self):
        response = self.anonymous_client.get(reverse('student-app-onboarding'), follow=True)
        self.assertRedirects(response, reverse('student-identity-login'))
        page_messages = [str(m) for m in response.context['messages']]
        self.assertTrue(any('login' in m.lower() for m in page_messages))

    def test_student_login_url_distinct_from_staff_login_url(self):
        from django.conf import settings
        student_login = getattr(settings, 'STUDENT_LOGIN_URL', None)
        staff_login = getattr(settings, 'LOGIN_URL', '/login/')
        self.assertIsNotNone(student_login)
        self.assertNotEqual(student_login, staff_login)
