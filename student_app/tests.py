from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
import json
import uuid
from unittest.mock import patch

from django.core.cache import cache
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from auditing.models import AuditEvent
from finance.models import Enrollment, MembershipPlan
from operations.models import Attendance, AttendanceStatus, ClassSession
from student_app.application.cache_keys import (
    build_student_agenda_snapshot_cache_key,
    build_student_home_snapshot_cache_key,
    build_student_rm_snapshot_cache_key,
    build_student_wod_snapshot_cache_key,
)
from student_app.application.rm_snapshots import get_student_rm_snapshot
from student_app.application.use_cases import GetStudentDashboard, GetStudentWorkoutDay, GetStudentWorkoutPrescription
from student_app.models import (
    SessionWorkout,
    SessionWorkoutBlock,
    SessionWorkoutMovement,
    SessionWorkoutStatus,
    StudentAppActivity,
    StudentAppActivityKind,
    StudentExerciseMax,
    StudentExerciseMaxHistory,
    StudentProfileChangeRequest,
    StudentProfileChangeRequestStatus,
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
        cache.clear()
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

    def test_student_profile_edit_creates_pending_request_without_direct_write(self):
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
        self.assertEqual(self.student.full_name, 'Atleta App')
        self.assertEqual(self.student.email, 'app@example.com')
        self.assertEqual(self.identity.email, 'app@example.com')
        request = StudentProfileChangeRequest.objects.get(student=self.student, identity=self.identity)
        self.assertEqual(request.status, StudentProfileChangeRequestStatus.PENDING)
        self.assertEqual(request.requested_payload['full_name'], 'Atleta Atualizada')
        self.assertEqual(request.requested_payload['email'], 'nova@app.com')

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
        session = ClassSession.objects.create(
            title='Cross de terca',
            scheduled_at=timezone.now() + timedelta(days=1),
            status='scheduled',
        )
        response = self.client.get(reverse('student-app-home'), {'date': timezone.localtime(session.scheduled_at).date().isoformat()})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Inicio')
        self.assertNotContains(response, 'Abrir menu lateral')
        self.assertContains(response, 'Cross de terca')
        self.assertContains(response, 'Box atual: control')
        self.assertNotContains(response, 'Trocar box')
        self.assertContains(response, 'Grade')
        self.assertContains(response, 'WOD')
        self.assertContains(response, 'RM')
        self.assertContains(response, 'Proxima aula')
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

    def test_confirm_attendance_blocks_second_booking_while_other_reservation_is_active(self):
        base = timezone.localtime() + timedelta(hours=1)
        base = base.replace(minute=0, second=0, microsecond=0)
        first_session = ClassSession.objects.create(
            title='Primeira aula',
            scheduled_at=base,
            status='scheduled',
        )
        second_session = ClassSession.objects.create(
            title='Segunda aula',
            scheduled_at=base + timedelta(hours=2),
            status='scheduled',
        )
        Attendance.objects.create(
            student=self.student,
            session=first_session,
            status=AttendanceStatus.BOOKED,
            reservation_source='student_app',
        )

        response = self.client.post(
            reverse('student-app-confirm-attendance'),
            {
                'session_id': str(second_session.id),
                'next': reverse('student-app-grade'),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Voce ja tem uma reserva ativa. So pode reservar a proxima aula depois que a atual terminar.')
        self.assertFalse(Attendance.objects.filter(student=self.student, session=second_session).exists())

    def test_confirm_attendance_blocks_booking_beyond_tomorrow(self):
        session = ClassSession.objects.create(
            title='Aula distante',
            scheduled_at=timezone.now() + timedelta(days=2, hours=2),
            status='scheduled',
        )

        response = self.client.post(
            reverse('student-app-confirm-attendance'),
            {
                'session_id': str(session.id),
                'next': reverse('student-app-grade'),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Voce pode reservar apenas aulas de hoje ou amanha.')
        self.assertFalse(Attendance.objects.filter(student=self.student, session=session).exists())

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

    def test_student_grade_renders_booking_action_for_every_listed_session(self):
        for offset in (2, 4):
            ClassSession.objects.create(
                title=f'Aula {offset}',
                scheduled_at=timezone.now() + timedelta(hours=offset),
                status='scheduled',
            )

        response = self.client.get(reverse('student-app-grade'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Aqui voce acompanha sua rotina. Reserve na aba Agenda.')
        self.assertNotContains(response, 'class="student-secondary-action"', html=False)

    def test_cancel_attendance_sets_booking_as_canceled_until_one_hour_before_class(self):
        session = ClassSession.objects.create(
            title='Aula com cancelamento',
            scheduled_at=timezone.now() + timedelta(hours=3),
            status='scheduled',
        )
        Attendance.objects.create(
            student=self.student,
            session=session,
            status=AttendanceStatus.BOOKED,
            reservation_source='student_app',
        )

        response = self.client.post(
            reverse('student-app-cancel-attendance'),
            {
                'session_id': str(session.id),
                'next': reverse('student-app-grade'),
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        attendance = Attendance.objects.get(student=self.student, session=session)
        self.assertEqual(attendance.status, AttendanceStatus.CANCELED)

    def test_cancel_attendance_is_blocked_inside_one_hour_window(self):
        session = ClassSession.objects.create(
            title='Aula perto demais',
            scheduled_at=timezone.now() + timedelta(minutes=45),
            status='scheduled',
        )
        Attendance.objects.create(
            student=self.student,
            session=session,
            status=AttendanceStatus.BOOKED,
            reservation_source='student_app',
        )

        self.client.post(
            reverse('student-app-cancel-attendance'),
            {
                'session_id': str(session.id),
                'next': reverse('student-app-grade'),
            },
            follow=False,
        )

        attendance = Attendance.objects.get(student=self.student, session=session)
        self.assertEqual(attendance.status, AttendanceStatus.BOOKED)

    def test_cancel_attendance_is_blocked_after_check_in(self):
        session = ClassSession.objects.create(
            title='Aula com check-in',
            scheduled_at=timezone.now() + timedelta(hours=2),
            status='scheduled',
        )
        Attendance.objects.create(
            student=self.student,
            session=session,
            status=AttendanceStatus.CHECKED_IN,
            reservation_source='student_app',
        )

        response = self.client.post(
            reverse('student-app-cancel-attendance'),
            {
                'session_id': str(session.id),
                'next': reverse('student-app-grade'),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sua presenca ja foi confirmada nesta aula.')
        attendance = Attendance.objects.get(student=self.student, session=session)
        self.assertEqual(attendance.status, AttendanceStatus.CHECKED_IN)

    @override_settings(TIME_ZONE='America/Sao_Paulo')
    def test_student_schedule_renders_utc_input_in_box_local_timezone(self):
        session = ClassSession.objects.create(
            title='Aula UTC',
            scheduled_at=datetime(2026, 4, 24, 12, 0, tzinfo=dt_timezone.utc),
            status='scheduled',
        )

        dashboard = GetStudentDashboard().execute(
            identity=self.identity,
            selected_date=date(2026, 4, 24),
        )

        card = next(item for item in dashboard.next_sessions if item.session_id == session.id)
        self.assertEqual(card.scheduled_label, '24/04 09:00')

    def test_student_progress_week_starts_today(self):
        dashboard = GetStudentDashboard().execute(identity=self.identity)
        today = timezone.localdate()

        self.assertEqual(dashboard.progress_days[0].date, today)
        self.assertEqual(dashboard.progress_days[0].day_label, 'Hoje')

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
        self.assertContains(grade_response, 'Hoje')
        self.assertContains(grade_response, 'Amanha')
        self.assertContains(grade_response, 'Ver mes')
        self.assertContains(rm_response, 'Records')
        self.assertContains(rm_response, 'Deadlift')
        self.assertContains(rm_response, '100kg')

    def test_student_home_filters_day_by_query_param(self):
        today_session = ClassSession.objects.create(
            title='Hoje cedo',
            scheduled_at=timezone.now() + timedelta(hours=2),
            status='scheduled',
        )
        tomorrow_session = ClassSession.objects.create(
            title='Amanha cedo',
            scheduled_at=timezone.now() + timedelta(days=1, hours=2),
            status='scheduled',
        )

        response = self.client.get(reverse('student-app-home'), {'date': timezone.localtime(tomorrow_session.scheduled_at).date().isoformat()})

        self.assertContains(response, 'Amanha cedo')
        self.assertNotContains(response, 'Hoje cedo')

    def test_dashboard_focal_session_shows_next_class_when_student_has_no_reservation(self):
        first_session = ClassSession.objects.create(
            title='Cross 06h',
            scheduled_at=timezone.now() + timedelta(hours=2),
            status='scheduled',
            capacity=20,
        )
        ClassSession.objects.create(
            title='Cross 07h',
            scheduled_at=timezone.now() + timedelta(hours=3),
            status='scheduled',
            capacity=20,
        )

        dashboard = GetStudentDashboard().execute(identity=self.identity)

        self.assertIsNotNone(dashboard.focal_session)
        self.assertEqual(dashboard.focal_session.session_id, first_session.id)
        self.assertEqual(dashboard.primary_action.kind, 'book_session')

    def test_dashboard_focal_session_prioritizes_active_reserved_class(self):
        first_session = ClassSession.objects.create(
            title='Cross 06h',
            scheduled_at=timezone.now() + timedelta(hours=2),
            status='scheduled',
            capacity=20,
        )
        reserved_session = ClassSession.objects.create(
            title='Cross 08h',
            scheduled_at=timezone.now() + timedelta(hours=4),
            status='scheduled',
            capacity=20,
        )
        Attendance.objects.create(
            student=self.student,
            session=reserved_session,
            status=AttendanceStatus.BOOKED,
            reservation_source='student_app',
        )

        dashboard = GetStudentDashboard().execute(identity=self.identity)

        self.assertIsNotNone(dashboard.focal_session)
        self.assertEqual(dashboard.focal_session.session_id, reserved_session.id)
        self.assertEqual(dashboard.primary_action.kind, 'open_grade')
        self.assertNotEqual(dashboard.focal_session.session_id, first_session.id)

    def test_student_home_marks_selected_day_and_keeps_booking_block_reason(self):
        reserved_session = ClassSession.objects.create(
            title='Cross reservada',
            scheduled_at=timezone.now() + timedelta(hours=3),
            status='scheduled',
            capacity=20,
        )
        next_day_session = ClassSession.objects.create(
            title='Cross amanha',
            scheduled_at=timezone.now() + timedelta(days=1, hours=1),
            status='scheduled',
            capacity=20,
        )
        Attendance.objects.create(
            student=self.student,
            session=reserved_session,
            status=AttendanceStatus.BOOKED,
            reservation_source='student_app',
        )

        response = self.client.get(
            reverse('student-app-home'),
            {'date': timezone.localtime(next_day_session.scheduled_at).date().isoformat()},
        )

        self.assertContains(response, 'class="student-progress-day student-day-filter is-selected"', html=False)
        self.assertContains(response, 'Voce ja tem uma reserva ativa. Libere a proxima so depois que essa aula terminar.')

    def test_student_canceled_booking_shows_reservar_novamente(self):
        session = ClassSession.objects.create(
            title='Aula cancelada',
            scheduled_at=timezone.now() + timedelta(hours=3),
            status='scheduled',
        )
        Attendance.objects.create(
            student=self.student,
            session=session,
            status=AttendanceStatus.CANCELED,
            reservation_source='student_app',
        )

        response = self.client.get(reverse('student-app-home'), {'date': timezone.localtime(session.scheduled_at).date().isoformat()})

        self.assertContains(response, 'Reservar novamente')

    def test_student_wod_opens_specific_session_from_query_param(self):
        first_session = ClassSession.objects.create(
            title='Turma 1',
            scheduled_at=timezone.now() + timedelta(hours=2),
            status='scheduled',
        )
        second_session = ClassSession.objects.create(
            title='Turma 2',
            scheduled_at=timezone.now() + timedelta(hours=4),
            status='scheduled',
        )
        first_workout = SessionWorkout.objects.create(session=first_session, title='WOD 1', status=SessionWorkoutStatus.PUBLISHED)
        second_workout = SessionWorkout.objects.create(session=second_session, title='WOD 2', status=SessionWorkoutStatus.PUBLISHED)
        SessionWorkoutBlock.objects.create(workout=first_workout, kind=WorkoutBlockKind.STRENGTH, title='Forca 1', sort_order=1)
        SessionWorkoutBlock.objects.create(workout=second_workout, kind=WorkoutBlockKind.STRENGTH, title='Forca 2', sort_order=1)

        response = self.client.get(reverse('student-app-wod'), {'session_id': second_session.id})

        self.assertContains(response, 'WOD 2')
        self.assertNotContains(response, 'WOD 1')

    def test_student_rm_create_and_update_record_history_and_activity(self):
        add_response = self.client.post(
            reverse('student-app-rm-add'),
            {
                'exercise_label': 'Deadlift',
                'one_rep_max_kg': '100.5',
            },
            follow=False,
        )

        self.assertEqual(add_response.status_code, 302)
        record = StudentExerciseMax.objects.get(student=self.student, exercise_slug='deadlift')
        created_history = StudentExerciseMaxHistory.objects.get(student=self.student, exercise_slug='deadlift')
        self.assertIsNone(created_history.previous_kg)
        self.assertEqual(created_history.new_kg, Decimal('100.5'))
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
            {'one_rep_max_kg': '105.5'},
            follow=False,
        )

        self.assertEqual(update_response.status_code, 302)
        latest_history = StudentExerciseMaxHistory.objects.filter(student=self.student, exercise_slug='deadlift').latest('created_at')
        self.assertEqual(latest_history.previous_kg, Decimal('100.5'))
        self.assertEqual(latest_history.new_kg, Decimal('105.5'))
        self.assertEqual(latest_history.delta_kg, Decimal('5.00'))
        self.assertTrue(
            StudentAppActivity.objects.filter(
                student=self.student,
                kind=StudentAppActivityKind.RM_UPDATED,
                source_object_id=record.id,
            ).exists()
        )

    def test_student_rm_rejects_quarter_kg_precision(self):
        response = self.client.post(
            reverse('student-app-rm-add'),
            {
                'exercise_label': 'Front squat',
                'one_rep_max_kg': '100.25',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confira os dados e tente novamente.')
        self.assertFalse(StudentExerciseMax.objects.filter(student=self.student, exercise_slug='front-squat').exists())

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
        for offset in range(12):
            ClassSession.objects.create(
                title=f'Cross visivel {offset}',
                scheduled_at=timezone.now() + timedelta(hours=offset + 1),
                status='scheduled',
            )
        hidden_session = ClassSession.objects.create(
            title='Cross fora do radar',
            scheduled_at=timezone.now() + timedelta(hours=24),
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
        self.assertContains(response, 'Calculadora')
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
        self.assertContains(response, 'Deadlift')
        self.assertContains(response, '70,00% do seu RM')
        self.assertContains(response, '70,00 kg')
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

    def test_student_workout_day_uses_versioned_snapshot_without_caching_student_rm(self):
        cache.clear()
        exercise_max = StudentExerciseMax.objects.create(
            student=self.student,
            exercise_slug='deadlift',
            exercise_label='Deadlift',
            one_rep_max_kg=Decimal('100.00'),
        )
        session = ClassSession.objects.create(
            title='Cross com snapshot',
            scheduled_at=timezone.now() + timedelta(minutes=15),
            status='open',
        )
        workout = SessionWorkout.objects.create(
            session=session,
            title='Forca cacheada',
            coach_notes='Cache compartilhado do treino publicado.',
            status=SessionWorkoutStatus.PUBLISHED,
            version=3,
        )
        block = SessionWorkoutBlock.objects.create(
            workout=workout,
            kind=WorkoutBlockKind.STRENGTH,
            title='Forca',
            sort_order=1,
        )
        SessionWorkoutMovement.objects.create(
            block=block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sets=5,
            reps=3,
            load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            load_value=Decimal('70.00'),
            sort_order=1,
        )

        first_result = GetStudentWorkoutDay().execute(
            student=self.student,
            session_id=session.id,
            box_root_slug='control',
        )

        cache_key = build_student_wod_snapshot_cache_key(
            box_root_slug='control',
            session_id=session.id,
            workout_version=3,
        )
        cached_snapshot = cache.get(cache_key)
        self.assertIsNotNone(cached_snapshot)
        self.assertEqual(first_result.primary_recommendation.recommended_load_kg, Decimal('70.00'))
        self.assertNotIn('recommended_load_kg', json.dumps(cached_snapshot))

        exercise_max.one_rep_max_kg = Decimal('80.00')
        exercise_max.save(update_fields=['one_rep_max_kg', 'updated_at'])

        with CaptureQueriesContext(connection) as captured_queries:
            second_result = GetStudentWorkoutDay().execute(
                student=self.student,
                session_id=session.id,
                box_root_slug='control',
            )

        self.assertLessEqual(len(captured_queries), 3)
        self.assertEqual(second_result.primary_recommendation.recommended_load_kg, Decimal('55.00'))

    def test_student_dashboard_agenda_snapshot_keeps_attendance_personalized(self):
        cache.clear()
        session = ClassSession.objects.create(
            title='Cross compartilhado',
            scheduled_at=timezone.now() + timedelta(hours=2),
            status='scheduled',
            capacity=16,
        )

        first_dashboard = GetStudentDashboard().execute(identity=self.identity)
        first_session = next(item for item in first_dashboard.next_sessions if item.session_id == session.id)
        self.assertEqual(first_session.attendance_status, 'Sem reserva')

        cache_key = build_student_agenda_snapshot_cache_key(
            box_root_slug='control',
            start_date=timezone.localtime().date(),
            window_days=None,
            limit=12,
        )
        cached_snapshot = cache.get(cache_key)
        self.assertIsNotNone(cached_snapshot)
        self.assertNotIn('Reservado', json.dumps(cached_snapshot))

        second_student = Student.objects.create(
            full_name='Atleta Reservada',
            phone='5511777777799',
            email='reservada@example.com',
        )
        second_identity = StudentIdentity.objects.create(
            student=second_student,
            box_root_slug='control',
            primary_box_root_slug='control',
            provider=StudentIdentityProvider.GOOGLE,
            provider_subject='provider-subject-reserved',
            email='reservada@example.com',
            status=StudentIdentityStatus.ACTIVE,
        )
        StudentBoxMembership.objects.create(
            identity=second_identity,
            student=second_student,
            box_root_slug='control',
            status=StudentBoxMembershipStatus.ACTIVE,
        )
        Attendance.objects.create(
            student=second_student,
            session=session,
            status=AttendanceStatus.BOOKED,
        )

        with CaptureQueriesContext(connection) as captured_queries:
            second_dashboard = GetStudentDashboard().execute(identity=second_identity)

        second_session = next(item for item in second_dashboard.next_sessions if item.session_id == session.id)
        self.assertLessEqual(len(captured_queries), 8)
        self.assertEqual(second_session.attendance_status, 'Reservado')
        self.assertEqual(second_session.occupied_slots, 1)

    def test_student_home_snapshot_invalidates_when_student_books_session(self):
        cache.clear()
        session = ClassSession.objects.create(
            title='Cross para reservar',
            scheduled_at=timezone.now() + timedelta(hours=2),
            status='scheduled',
        )

        first_dashboard = GetStudentDashboard().execute(identity=self.identity)
        first_session = next(item for item in first_dashboard.next_sessions if item.session_id == session.id)
        self.assertEqual(first_session.attendance_status, 'Sem reserva')

        cache_key = build_student_home_snapshot_cache_key(
            box_root_slug='control',
            student_id=self.student.id,
            start_date=timezone.localtime().date(),
            window_days=None,
            limit=12,
        )
        self.assertIsNotNone(cache.get(cache_key))

        Attendance.objects.create(
            student=self.student,
            session=session,
            status=AttendanceStatus.BOOKED,
            reservation_source='student_app',
        )

        second_dashboard = GetStudentDashboard().execute(identity=self.identity)
        second_session = next(item for item in second_dashboard.next_sessions if item.session_id == session.id)
        self.assertEqual(second_session.attendance_status, 'Reservado')
        self.assertEqual(second_dashboard.focal_session.session_id, session.id)

    def test_student_home_snapshot_invalidates_when_rm_changes(self):
        cache.clear()
        StudentExerciseMax.objects.create(
            student=self.student,
            exercise_slug='deadlift',
            exercise_label='Deadlift',
            one_rep_max_kg=Decimal('100.00'),
        )
        session = ClassSession.objects.create(
            title='Cross com RM',
            scheduled_at=timezone.now() + timedelta(minutes=15),
            status='open',
        )
        Attendance.objects.create(
            student=self.student,
            session=session,
            status=AttendanceStatus.BOOKED,
            reservation_source='student_app',
        )
        workout = SessionWorkout.objects.create(
            session=session,
            title='WOD RM',
            status=SessionWorkoutStatus.PUBLISHED,
        )
        block = SessionWorkoutBlock.objects.create(
            workout=workout,
            kind=WorkoutBlockKind.STRENGTH,
            title='Forca',
            sort_order=1,
        )
        SessionWorkoutMovement.objects.create(
            block=block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            load_value=Decimal('70.00'),
            sort_order=1,
        )

        first_dashboard = GetStudentDashboard().execute(identity=self.identity)
        self.assertEqual(first_dashboard.rm_of_the_day.recommended_load_kg, Decimal('70.00'))

        record = StudentExerciseMax.objects.get(student=self.student, exercise_slug='deadlift')
        record.one_rep_max_kg = Decimal('80.00')
        record.save(update_fields=['one_rep_max_kg', 'updated_at'])

        second_dashboard = GetStudentDashboard().execute(identity=self.identity)
        self.assertEqual(second_dashboard.rm_of_the_day.recommended_load_kg, Decimal('55.00'))

    def test_student_home_snapshot_invalidates_when_plan_changes(self):
        cache.clear()
        plan = MembershipPlan.objects.create(
            name='Plano Ouro',
            price=Decimal('299.00'),
            sessions_per_week=5,
        )
        enrollment = Enrollment.objects.create(
            student=self.student,
            plan=plan,
            status='active',
        )

        first_dashboard = GetStudentDashboard().execute(identity=self.identity)
        self.assertEqual(first_dashboard.membership_label, 'Plano Ouro')

        enrollment.status = 'canceled'
        enrollment.save(update_fields=['status', 'updated_at'])

        second_dashboard = GetStudentDashboard().execute(identity=self.identity)
        self.assertEqual(second_dashboard.membership_label, 'Sem plano ativo')

    @override_settings(REQUEST_TIMING_EXPOSE_DEBUG_HEADERS=True)
    def test_student_home_emits_cache_telemetry_headers(self):
        cache.clear()
        ClassSession.objects.create(
            title='Cross telemetria',
            scheduled_at=timezone.now() + timedelta(hours=2),
            status='scheduled',
        )

        self.client.get(reverse('student-app-home'))
        response = self.client.get(reverse('student-app-home'))

        self.assertIn('student-home', response['Server-Timing'])
        self.assertIn('student-agenda', response['Server-Timing'])
        self.assertEqual(response['X-OctoBox-Student-Agenda-Cache-Hit'], '1')
        self.assertEqual(response['X-OctoBox-Student-Home-Cache-Hit'], '1')

    def test_student_rm_snapshot_reuses_cached_record_for_workout_prescription(self):
        cache.clear()
        StudentExerciseMax.objects.create(
            student=self.student,
            exercise_slug='deadlift',
            exercise_label='Deadlift',
            one_rep_max_kg=Decimal('100.00'),
        )

        first_result = GetStudentWorkoutPrescription().execute(
            student=self.student,
            exercise_slug='deadlift',
            percentage=Decimal('75'),
        )
        self.assertEqual(first_result.rounded_load_label, '75.00 kg')

        cache_key = build_student_rm_snapshot_cache_key(
            box_root_slug='control',
            student_id=self.student.id,
        )
        self.assertIsNotNone(cache.get(cache_key))

        with CaptureQueriesContext(connection) as captured_queries:
            second_result = GetStudentWorkoutPrescription().execute(
                student=self.student,
                exercise_slug='deadlift',
                percentage=Decimal('75'),
            )

        self.assertEqual(second_result.rounded_load_label, '75.00 kg')
        self.assertEqual(len(captured_queries), 0)

    def test_student_rm_snapshot_invalidates_after_rm_update(self):
        cache.clear()
        record = StudentExerciseMax.objects.create(
            student=self.student,
            exercise_slug='deadlift',
            exercise_label='Deadlift',
            one_rep_max_kg=Decimal('100.00'),
        )

        first_snapshot = get_student_rm_snapshot(student=self.student, box_root_slug='control')
        self.assertEqual(first_snapshot['cards'][0].record.one_rep_max_kg, Decimal('100.00'))

        record.one_rep_max_kg = Decimal('110.00')
        record.save(update_fields=['one_rep_max_kg', 'updated_at'])

        second_snapshot = get_student_rm_snapshot(student=self.student, box_root_slug='control')
        self.assertEqual(second_snapshot['cards'][0].record.one_rep_max_kg, Decimal('110.00'))

    @override_settings(REQUEST_TIMING_EXPOSE_DEBUG_HEADERS=True)
    def test_student_rm_route_emits_cache_telemetry_headers(self):
        cache.clear()
        StudentExerciseMax.objects.create(
            student=self.student,
            exercise_slug='deadlift',
            exercise_label='Deadlift',
            one_rep_max_kg=Decimal('100.00'),
        )

        self.client.get(reverse('student-app-rm'))
        response = self.client.get(reverse('student-app-rm'))

        self.assertIn('student-rm', response['Server-Timing'])
        self.assertEqual(response['X-OctoBox-Student-RM-Cache-Hit'], '1')

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
        self.assertContains(response, 'Ative o que falta no app.', html=False)
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
