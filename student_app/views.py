from __future__ import annotations

import json
import re
from pathlib import Path
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.template.loader import render_to_string
from django.views.generic import FormView, TemplateView, View

from finance.models import Enrollment, EnrollmentStatus
from operations.models import Attendance, AttendanceStatus, ClassSession, SessionStatus
from shared_support.box_runtime import get_box_runtime_slug
from student_identity.funnel_events import record_student_onboarding_event
from student_app.application.use_cases import GetStudentDashboard, GetStudentWorkoutDay, GetStudentWorkoutPrescription
from student_app.forms import (
    ImportedLeadOnboardingForm,
    MassInviteOnboardingForm,
    StudentProfileEditForm,
    WorkoutPrescriptionForm,
)
from student_app.models import SessionWorkout, SessionWorkoutStatus, StudentExerciseMax, StudentWorkoutView
from student_identity.models import (
    StudentBoxInviteLink,
    StudentBoxMembership,
    StudentBoxMembershipStatus,
    StudentOnboardingJourney,
)
from student_identity.infrastructure.repositories import DjangoStudentIdentityRepository
from student_identity.security import build_student_device_fingerprint
from student_identity.infrastructure.session import (
    attach_student_session_cookie,
    get_student_session_cookie_name,
    read_student_session_value,
    clear_student_session_cookie,
)
from student_app.onboarding_state import clear_pending_student_onboarding, read_pending_student_onboarding
from students.models import Student, StudentStatus


STUDENT_APP_SCOPE = '/aluno/'
STUDENT_APP_START_URL = '/aluno/'
STUDENT_APP_THEME_COLOR = '#0f172a'
STUDENT_APP_BACKGROUND_COLOR = '#f5efe4'
STUDENT_APP_ICON_192 = '/static/images/student-app-icon-192.png'
STUDENT_APP_ICON_512 = '/static/images/student-app-icon-512.png'
STUDENT_APP_ICON_MASKABLE_512 = '/static/images/student-app-icon-maskable-512.png'
STUDENT_APP_APPLE_TOUCH_ICON = '/static/images/student-app-apple-touch-icon.png'
UUID_TOKEN_PATTERN = re.compile(r'(?P<token>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})')
PUBLIC_WORKOUT_SCOPE = '/renan/'
PUBLIC_WORKOUT_SW_URL = '/renan/sw.js'
PUBLIC_WORKOUT_OFFLINE_URL = '/renan/offline/'
PUBLIC_WORKOUT_ICON_192 = STUDENT_APP_ICON_192
PUBLIC_WORKOUT_ICON_512 = STUDENT_APP_ICON_512
PUBLIC_WORKOUT_ICON_MASKABLE_512 = STUDENT_APP_ICON_MASKABLE_512
PUBLIC_WORKOUT_APPLE_TOUCH_ICON = STUDENT_APP_APPLE_TOUCH_ICON
PUBLIC_WORKOUT_LIBRARY = {
    'juliana': {
        'title': 'Treino Juliana',
        'theme_color': '#0f172a',
        'background_color': '#f5efe4',
        'template_file': 'juliana.html',
    },
    'bruno': {
        'title': 'Treino Bruno',
        'theme_color': '#11203b',
        'background_color': '#f4efe6',
        'template_file': 'bruno.html',
    },
}
PUBLIC_WORKOUT_TEMPLATE_DIR = Path(settings.BASE_DIR) / 'templates' / 'public_workouts'


def _get_public_workout_entry(plan_slug: str) -> dict[str, str]:
    normalized_slug = (plan_slug or '').strip().lower()
    entry = PUBLIC_WORKOUT_LIBRARY.get(normalized_slug)
    if entry is None:
        raise Http404('Treino publico nao encontrado.')
    return {'slug': normalized_slug, **entry}


def _build_public_workout_manifest_url(plan_slug: str) -> str:
    return f'/renan/{plan_slug}/manifest.webmanifest'


def _render_public_workout_html(plan_slug: str) -> str:
    entry = _get_public_workout_entry(plan_slug)
    template_path = PUBLIC_WORKOUT_TEMPLATE_DIR / entry['template_file']
    if not template_path.exists():
        raise Http404('Arquivo de treino publico indisponivel.')

    html = template_path.read_text(encoding='utf-8')
    if html.startswith('{% load static %}'):
        html = html.split('\n', 1)[1]

    viewport_markers = (
        '<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
    )
    head_injection = (
        f'<meta name="theme-color" content="{entry["theme_color"]}">\n'
        '<meta name="mobile-web-app-capable" content="yes">\n'
        '<meta name="apple-mobile-web-app-capable" content="yes">\n'
        '<meta name="apple-mobile-web-app-status-bar-style" content="default">\n'
        f'<meta name="apple-mobile-web-app-title" content="{entry["title"]}">\n'
        f'<link rel="manifest" href="{_build_public_workout_manifest_url(entry["slug"])}">\n'
        f'<link rel="apple-touch-icon" href="{PUBLIC_WORKOUT_APPLE_TOUCH_ICON}">\n'
        f'<link rel="icon" href="/static/images/student-app-icon.svg" type="image/svg+xml">\n'
        f'<link rel="icon" href="{PUBLIC_WORKOUT_ICON_192}" sizes="192x192" type="image/png">'
    )
    for marker in viewport_markers:
        if marker in html:
            html = html.replace(marker, f'{marker}\n{head_injection}', 1)
            break

    sw_registration_script = """
<script>
(function () {
  if (!('serviceWorker' in navigator)) {
    return;
  }
  window.addEventListener('load', function () {
    navigator.serviceWorker.register('/renan/sw.js', { scope: '/renan/' }).catch(function () {
      // O treino continua abrindo mesmo sem o service worker.
    });
  });
})();
</script>
""".strip()
    if "navigator.serviceWorker.register('/renan/sw.js'" not in html:
        html = html.replace('</body>', f'{sw_registration_script}\n</body>', 1)
    return html


def _ensure_pending_enrollment(*, student: Student, plan, source_note: str):
    if plan is None:
        return None
    enrollment = (
        Enrollment.objects.filter(
            student=student,
            plan=plan,
            status__in=[EnrollmentStatus.PENDING, EnrollmentStatus.ACTIVE],
        )
        .order_by('-created_at')
        .first()
    )
    if enrollment is not None:
        return enrollment
    return Enrollment.objects.create(
        student=student,
        plan=plan,
        status=EnrollmentStatus.PENDING,
        notes=source_note,
    )


class StudentIdentityRequiredMixin:
    identity_repository_class = DjangoStudentIdentityRepository
    membership_statuses = (StudentBoxMembershipStatus.ACTIVE,)
    requires_active_membership = True

    def _get_runtime_memberships(self, *, identity):
        all_memberships = list(StudentBoxMembership.objects.filter(identity=identity).order_by('box_root_slug'))
        if not all_memberships:
            fallback_membership = StudentBoxMembership.objects.create(
                identity=identity,
                student=identity.student,
                box_root_slug=identity.primary_box_root_slug or identity.box_root_slug,
                status=StudentBoxMembershipStatus.ACTIVE,
            )
            return [fallback_membership]
        if self.membership_statuses is None:
            return all_memberships
        return [membership for membership in all_memberships if membership.status in self.membership_statuses]

    def _attach_student_shell_context(self, context):
        context['student_identity'] = self.request.student_identity
        context['student_active_box_root_slug'] = self.request.student_active_box_root_slug
        context['student_primary_box_root_slug'] = self.request.student_identity.primary_box_root_slug
        context['student_memberships'] = list(self.request.student_box_memberships)
        context.setdefault('student_shell_nav', 'home')
        context.setdefault('student_shell_title', 'Inicio')
        context['student_box_choices'] = [
            {
                'box_root_slug': membership.box_root_slug,
                'is_active': membership.box_root_slug == self.request.student_active_box_root_slug,
                'is_primary': membership.box_root_slug == self.request.student_identity.primary_box_root_slug,
            }
            for membership in self.request.student_box_memberships
        ]
        context['student_can_switch_box'] = len(context['student_box_choices']) > 1
        return context

    def _resolve_student_runtime(self, request):
        payload = read_student_session_value(request.COOKIES.get(get_student_session_cookie_name()))
        if payload is None:
            return None, None, None
        identity = self.identity_repository_class().find_identity_by_id(payload.get('identity_id', 0))
        if identity is None:
            return None, None, None
        memberships = self._get_runtime_memberships(identity=identity)
        if not memberships:
            return identity, [], None
        active_box_root_slug = (
            payload.get('active_box_root_slug')
            or payload.get('box_root_slug')
            or identity.primary_box_root_slug
            or identity.box_root_slug
        )
        active_membership = next((membership for membership in memberships if membership.box_root_slug == active_box_root_slug), None)
        if active_membership is None:
            active_membership = next((membership for membership in memberships if membership.box_root_slug == identity.primary_box_root_slug), None)
        if active_membership is None:
            active_membership = memberships[0]
        return identity, memberships, active_membership

    def dispatch(self, request, *args, **kwargs):
        identity, memberships, active_membership = self._resolve_student_runtime(request)
        if identity is None:
            return redirect('student-identity-login')
        pending_onboarding = read_pending_student_onboarding(request)
        if pending_onboarding is not None and request.path != reverse('student-app-onboarding'):
            return redirect('student-app-onboarding')
        current_device_fingerprint = build_student_device_fingerprint(request)
        payload = read_student_session_value(request.COOKIES.get(get_student_session_cookie_name()))
        if payload is not None and payload.get('device_fingerprint') and payload.get('device_fingerprint') != current_device_fingerprint:
            messages.error(request, 'Detectamos mudanca forte de dispositivo ou rede nesta sessao. Entre novamente para continuar com seguranca.')
            response = redirect('student-identity-login')
            clear_student_session_cookie(response)
            return response
        if active_membership is None and self.requires_active_membership:
            runtime_memberships = list(StudentBoxMembership.objects.filter(identity=identity).order_by('box_root_slug'))
            suspended_memberships = [
                membership
                for membership in runtime_memberships
                if membership.status == StudentBoxMembershipStatus.SUSPENDED_FINANCIAL
            ]
            if runtime_memberships and len(suspended_memberships) == len(runtime_memberships):
                return redirect('student-app-suspended-financial')
            return redirect('student-app-no-active-box')
        request.student_identity = identity
        request.student_box_memberships = memberships
        request.student_active_box_root_slug = active_membership.box_root_slug if active_membership is not None else ''
        response = super().dispatch(request, *args, **kwargs)
        attach_student_session_cookie(
            response,
            identity_id=identity.id,
            box_root_slug=identity.box_root_slug,
            active_box_root_slug=request.student_active_box_root_slug,
            device_fingerprint=current_device_fingerprint,
        )
        return response


class StudentSessionIdentityMixin(StudentIdentityRequiredMixin):
    membership_statuses = (
        StudentBoxMembershipStatus.ACTIVE,
        StudentBoxMembershipStatus.PENDING_APPROVAL,
    )


class StudentAnyMembershipMixin(StudentIdentityRequiredMixin):
    membership_statuses = None
    requires_active_membership = False


class StudentHomeView(StudentIdentityRequiredMixin, TemplateView):
    template_name = 'student_app/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dashboard = GetStudentDashboard().execute(identity=self.request.student_identity)
        context['dashboard'] = dashboard
        context['student_shell_nav'] = 'home'
        context['student_shell_title'] = 'Inicio'
        context['student_home_mode'] = dashboard.home_mode
        context['student_next_session'] = dashboard.focal_session
        context['student_active_wod_session'] = dashboard.active_wod_session
        return self._attach_student_shell_context(context)


class StudentGradeView(StudentIdentityRequiredMixin, TemplateView):
    template_name = 'student_app/grade.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dashboard = GetStudentDashboard().execute(identity=self.request.student_identity)
        context['dashboard'] = dashboard
        context['student_shell_nav'] = 'grade'
        context['student_shell_title'] = 'Grade'
        context['student_next_session'] = dashboard.next_sessions[0] if dashboard.next_sessions else None
        return self._attach_student_shell_context(context)


class StudentWodView(StudentIdentityRequiredMixin, FormView):
    template_name = 'student_app/wod.html'
    form_class = WorkoutPrescriptionForm

    def _track_workout_view(self, *, workout):
        view, created = StudentWorkoutView.objects.get_or_create(
            student=self.request.student_identity.student,
            workout=workout,
            defaults={
                'first_viewed_at': timezone.now(),
                'last_viewed_at': timezone.now(),
                'view_count': 1,
            },
        )
        if created:
            return
        StudentWorkoutView.objects.filter(pk=view.pk).update(
            last_viewed_at=timezone.now(),
            view_count=F('view_count') + 1,
            updated_at=timezone.now(),
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['student'] = self.request.student_identity.student
        return kwargs

    def form_valid(self, form):
        result = GetStudentWorkoutPrescription().execute(
            student=self.request.student_identity.student,
            exercise_slug=form.cleaned_data['exercise_slug'],
            percentage=form.cleaned_data['percentage'],
        )
        context = self.get_context_data(form=form, prescription=result)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dashboard = GetStudentDashboard().execute(identity=self.request.student_identity)
        context['dashboard'] = dashboard
        context['student_shell_nav'] = 'wod'
        context['student_shell_title'] = 'WOD'
        context['student_next_session'] = dashboard.next_sessions[0] if dashboard.next_sessions else None
        target_session = dashboard.active_wod_session or dashboard.focal_session
        context['student_workout_day'] = (
            GetStudentWorkoutDay().execute(
                student=self.request.student_identity.student,
                session_id=target_session.session_id,
            )
            if target_session is not None else None
        )
        if target_session is not None and context['student_workout_day'] is not None:
            workout = (
                SessionWorkout.objects.filter(session_id=target_session.session_id, status=SessionWorkoutStatus.PUBLISHED)
                .only('id')
                .first()
            )
            if workout is not None:
                self._track_workout_view(workout=workout)
        context['student_rm_preview'] = (
            StudentExerciseMax.objects.filter(student=self.request.student_identity.student).order_by('exercise_label').first()
        )
        return self._attach_student_shell_context(context)


class StudentRmView(StudentIdentityRequiredMixin, TemplateView):
    template_name = 'student_app/rm.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_shell_nav'] = 'rm'
        context['student_shell_title'] = 'RM'
        context['rm_records'] = tuple(
            StudentExerciseMax.objects.filter(student=self.request.student_identity.student).order_by('exercise_label')
        )
        return self._attach_student_shell_context(context)


class StudentSettingsView(StudentIdentityRequiredMixin, FormView):
    template_name = 'student_app/settings.html'
    form_class = StudentProfileEditForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        student = self.request.student_identity.student
        kwargs['instance'] = student
        initial = kwargs.setdefault('initial', {})
        initial.setdefault('email', self.request.student_identity.email or student.email)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['box_runtime_slug'] = get_box_runtime_slug()
        context['student_shell_nav'] = 'settings'
        context['student_shell_title'] = 'Perfil'
        return self._attach_student_shell_context(context)

    def form_valid(self, form):
        student = form.save(commit=False)
        email = form.cleaned_data.get('email', '')
        student.email = email
        student.save()
        if self.request.student_identity.email != email and email:
            self.request.student_identity.email = email
            self.request.student_identity.save(update_fields=['email', 'updated_at'])
        messages.success(self.request, 'Seu perfil foi atualizado.')
        return redirect('student-app-settings')


class StudentOnboardingWizardView(FormView):
    template_name = 'student_app/onboarding_wizard.html'

    def dispatch(self, request, *args, **kwargs):
        self.pending_onboarding = read_pending_student_onboarding(request)
        if self.pending_onboarding is None:
            messages.info(request, 'Nenhum onboarding pendente foi encontrado por aqui.')
            return redirect('student-app-home')
        if not self.pending_onboarding.get('wizard_started_recorded'):
            record_student_onboarding_event(
                actor=None,
                actor_role='',
                journey=self.pending_onboarding.get('journey', ''),
                event='wizard_started',
                target_model='student_app.StudentOnboardingWizard',
                target_label=self.pending_onboarding.get('journey', ''),
                description='Wizard do onboarding do aluno iniciado.',
                metadata={
                    'box_root_slug': self.pending_onboarding.get('box_root_slug') or get_box_runtime_slug(),
                    'student_id': self.pending_onboarding.get('student_id'),
                    'identity_id': self.pending_onboarding.get('identity_id'),
                    'invitation_id': self.pending_onboarding.get('invitation_id'),
                    'box_invite_link_id': self.pending_onboarding.get('box_invite_link_id'),
                },
            )
            self.pending_onboarding['wizard_started_recorded'] = True
            store = request.session.get('student_pending_onboarding') or {}
            store.update(self.pending_onboarding)
            request.session['student_pending_onboarding'] = store
            request.session.modified = True
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        journey = self.pending_onboarding.get('journey')
        if journey == StudentOnboardingJourney.IMPORTED_LEAD_INVITE:
            return ImportedLeadOnboardingForm
        return MassInviteOnboardingForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        initial = kwargs.setdefault('initial', {})
        journey = self.pending_onboarding.get('journey')
        initial.setdefault('email', self.pending_onboarding.get('email', ''))
        if journey == StudentOnboardingJourney.IMPORTED_LEAD_INVITE:
            student = self._get_existing_student()
            if student is not None:
                initial.setdefault('full_name', student.full_name)
                initial.setdefault('phone', student.phone)
                initial.setdefault('email', student.email or self.pending_onboarding.get('email', ''))
                initial.setdefault('birth_date', student.birth_date)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        journey = self.pending_onboarding.get('journey')
        context['journey'] = journey
        context['journey_title'] = (
            'Complete seu cadastro no app'
            if journey == StudentOnboardingJourney.MASS_BOX_INVITE
            else 'Revise seus dados para entrar no app'
        )
        context['journey_copy'] = (
            'Aqui a gente pega os dados essenciais para seu acesso nascer redondo.'
            if journey == StudentOnboardingJourney.MASS_BOX_INVITE
            else 'Ja puxamos o que o box sabia sobre voce. Agora falta so uma revisao curta.'
        )
        return context

    def form_valid(self, form):
        journey = self.pending_onboarding.get('journey')
        if journey == StudentOnboardingJourney.IMPORTED_LEAD_INVITE:
            return self._complete_imported_lead_onboarding(form)
        return self._complete_mass_onboarding(form)

    def _get_existing_student(self):
        student_id = self.pending_onboarding.get('student_id')
        if not student_id:
            identity = self._get_pending_identity()
            return identity.student if identity is not None else None
        return Student.objects.filter(pk=student_id).first()

    def _get_pending_identity(self):
        identity_id = self.pending_onboarding.get('identity_id')
        return DjangoStudentIdentityRepository().find_identity_by_id(identity_id) if identity_id else None

    @transaction.atomic
    def _complete_mass_onboarding(self, form):
        repository = DjangoStudentIdentityRepository()
        student = Student.objects.create(
            full_name=form.cleaned_data['full_name'],
            phone=form.cleaned_data['phone'],
            email=form.cleaned_data['email'],
            birth_date=form.cleaned_data.get('birth_date'),
            status=StudentStatus.LEAD,
        )
        identity = repository.save_identity(
            student=student,
            box_root_slug=self.pending_onboarding['box_root_slug'],
            provider=self.pending_onboarding['provider'],
            provider_subject=self.pending_onboarding['provider_subject'],
            email=form.cleaned_data['email'],
            invitation=None,
        )
        _ensure_pending_enrollment(
            student=student,
            plan=form.cleaned_data.get('selected_plan'),
            source_note='Capturado via link em massa do onboarding do aluno.',
        )
        record_student_onboarding_event(
            actor=None,
            actor_role='',
            journey=StudentOnboardingJourney.MASS_BOX_INVITE,
            event='wizard_completed',
            target_model='student_identity.StudentIdentity',
            target_id=str(identity.id),
            target_label=student.full_name,
            description='Wizard completo do link em massa concluido.',
            metadata={
                'box_root_slug': identity.box_root_slug,
                'student_id': student.id,
                'identity_id': identity.id,
                'box_invite_link_id': self.pending_onboarding.get('box_invite_link_id'),
            },
        )
        record_student_onboarding_event(
            actor=None,
            actor_role='',
            journey=StudentOnboardingJourney.MASS_BOX_INVITE,
            event='app_entry_completed',
            target_model='student_identity.StudentIdentity',
            target_id=str(identity.id),
            target_label=student.full_name,
            description='Entrada no app concluida apos onboarding em massa.',
            metadata={
                'box_root_slug': identity.box_root_slug,
                'student_id': student.id,
                'identity_id': identity.id,
                'box_invite_link_id': self.pending_onboarding.get('box_invite_link_id'),
            },
        )
        clear_pending_student_onboarding(self.request)
        response = redirect('student-app-home')
        attach_student_session_cookie(
            response,
            identity_id=identity.id,
            box_root_slug=identity.box_root_slug,
            device_fingerprint=build_student_device_fingerprint(self.request),
        )
        messages.success(self.request, 'Cadastro concluido. Seu app do aluno ja esta pronto para uso.')
        return response

    @transaction.atomic
    def _complete_imported_lead_onboarding(self, form):
        identity = self._get_pending_identity()
        if identity is None:
            messages.error(self.request, 'Nao conseguimos localizar a identidade ligada a este onboarding.')
            clear_pending_student_onboarding(self.request)
            return redirect('student-app-home')
        student = self._get_existing_student()
        if student is None:
            messages.error(self.request, 'Nao conseguimos localizar o aluno vinculado a este convite.')
            clear_pending_student_onboarding(self.request)
            return redirect('student-app-home')
        student.full_name = form.cleaned_data['full_name']
        student.phone = form.cleaned_data['phone']
        student.email = form.cleaned_data['email']
        student.birth_date = form.cleaned_data.get('birth_date')
        if student.status == StudentStatus.LEAD:
            student.status = StudentStatus.ACTIVE
        student.save()
        if identity.email != student.email and student.email:
            identity.email = student.email
            identity.save(update_fields=['email', 'updated_at'])
        _ensure_pending_enrollment(
            student=student,
            plan=form.cleaned_data.get('selected_plan'),
            source_note='Capturado via convite individual de lead importado.',
        )
        record_student_onboarding_event(
            actor=None,
            actor_role='',
            journey=StudentOnboardingJourney.IMPORTED_LEAD_INVITE,
            event='wizard_completed',
            target_model='student_identity.StudentIdentity',
            target_id=str(identity.id),
            target_label=student.full_name,
            description='Wizard reduzido do lead importado concluido.',
            metadata={
                'box_root_slug': identity.box_root_slug,
                'student_id': student.id,
                'identity_id': identity.id,
                'invitation_id': self.pending_onboarding.get('invitation_id'),
            },
        )
        record_student_onboarding_event(
            actor=None,
            actor_role='',
            journey=StudentOnboardingJourney.IMPORTED_LEAD_INVITE,
            event='app_entry_completed',
            target_model='student_identity.StudentIdentity',
            target_id=str(identity.id),
            target_label=student.full_name,
            description='Entrada no app concluida apos convite de lead importado.',
            metadata={
                'box_root_slug': identity.box_root_slug,
                'student_id': student.id,
                'identity_id': identity.id,
                'invitation_id': self.pending_onboarding.get('invitation_id'),
            },
        )
        clear_pending_student_onboarding(self.request)
        messages.success(self.request, 'Dados revisados. Agora voce pode usar o app normalmente.')
        return redirect('student-app-home')


class StudentMembershipPendingView(StudentSessionIdentityMixin, TemplateView):
    template_name = 'student_app/membership_pending.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pending_membership = next(
            (
                membership
                for membership in self.request.student_box_memberships
                if membership.box_root_slug == self.request.student_active_box_root_slug
            ),
            None,
        )
        context['pending_membership'] = pending_membership
        return self._attach_student_shell_context(context)


class StudentNoActiveBoxView(StudentAnyMembershipMixin, TemplateView):
    template_name = 'student_app/no_active_box.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['inactive_memberships'] = [
            membership
            for membership in self.request.student_box_memberships
            if membership.status != StudentBoxMembershipStatus.ACTIVE
        ]
        return self._attach_student_shell_context(context)


class StudentSuspendedFinancialView(StudentAnyMembershipMixin, TemplateView):
    template_name = 'student_app/suspended_financial.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['suspended_memberships'] = [
            membership
            for membership in self.request.student_box_memberships
            if membership.status == StudentBoxMembershipStatus.SUSPENDED_FINANCIAL
        ]
        return self._attach_student_shell_context(context)


class StudentInviteEntryView(StudentAnyMembershipMixin, View):
    def post(self, request, *args, **kwargs):
        raw_value = (request.POST.get('invite_token_or_url') or '').strip()
        if not raw_value:
            messages.error(request, 'Cole um link de convite ou o token do box para continuar.')
            return redirect(request.META.get('HTTP_REFERER') or 'student-app-settings')

        match = UUID_TOKEN_PATTERN.search(raw_value)
        if match is None:
            messages.error(request, 'Nao consegui reconhecer um token de convite valido nesse texto.')
            return redirect(request.META.get('HTTP_REFERER') or 'student-app-settings')

        return redirect('student-identity-invite', token=match.group('token'))


class StudentSwitchBoxView(StudentIdentityRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        target_box_root_slug = (request.POST.get('box_root_slug') or '').strip()
        if not target_box_root_slug:
            messages.error(request, 'Escolha um box valido para trocar o contexto.')
            return redirect('student-app-home')

        target_membership = next(
            (membership for membership in request.student_box_memberships if membership.box_root_slug == target_box_root_slug),
            None,
        )
        if target_membership is None:
            messages.error(request, 'Este box nao esta disponivel para esta identidade de aluno.')
            return redirect('student-app-home')

        target_membership.last_access_at = target_membership.last_access_at or None
        target_membership.mark_active()
        target_membership.save(update_fields=['status', 'approved_at', 'last_access_at', 'updated_at'])
        request.student_active_box_root_slug = target_membership.box_root_slug
        response = redirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or 'student-app-home')
        attach_student_session_cookie(
            response,
            identity_id=request.student_identity.id,
            box_root_slug=request.student_identity.box_root_slug,
            active_box_root_slug=request.student_active_box_root_slug,
            device_fingerprint=build_student_device_fingerprint(request),
        )
        messages.success(request, f'Agora voce esta no contexto do box {target_membership.box_root_slug}.')
        return response


class StudentConfirmAttendanceView(StudentIdentityRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        session_id = request.POST.get('session_id')
        if not session_id:
            messages.error(request, 'Nao consegui identificar a aula para confirmar sua presenca.')
            return redirect('student-app-grade')

        session = get_object_or_404(
            ClassSession.objects.select_related('coach'),
            pk=session_id,
            status__in=[SessionStatus.SCHEDULED, SessionStatus.OPEN],
        )
        attendance, created = Attendance.objects.get_or_create(
            student=request.student_identity.student,
            session=session,
            defaults={
                'status': AttendanceStatus.BOOKED,
                'reservation_source': 'student_app',
            },
        )
        if not created and attendance.status in {AttendanceStatus.ABSENT, AttendanceStatus.CANCELED}:
            attendance.status = AttendanceStatus.BOOKED
            attendance.reservation_source = 'student_app'
            attendance.save(update_fields=['status', 'reservation_source', 'updated_at'])

        messages.success(
            request,
            f'Sua presenca em {session.title} foi confirmada. Quando a janela do treino abrir, o WOD sobe para o Inicio.',
        )
        return redirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or 'student-app-grade')


class StudentManifestView(View):
    def get(self, request, *args, **kwargs):
        manifest = {
            'name': 'OctoBox Aluno',
            'short_name': 'OctoBox',
            'start_url': STUDENT_APP_START_URL,
            'scope': STUDENT_APP_SCOPE,
            'display': 'standalone',
            'orientation': 'portrait',
            'background_color': STUDENT_APP_BACKGROUND_COLOR,
            'theme_color': STUDENT_APP_THEME_COLOR,
            'icons': [
                {
                    'src': STUDENT_APP_ICON_192,
                    'sizes': '192x192',
                    'type': 'image/png',
                    'purpose': 'any',
                },
                {
                    'src': STUDENT_APP_ICON_512,
                    'sizes': '512x512',
                    'type': 'image/png',
                    'purpose': 'any',
                },
                {
                    'src': STUDENT_APP_ICON_MASKABLE_512,
                    'sizes': '512x512',
                    'type': 'image/png',
                    'purpose': 'maskable',
                },
            ]
        }
        return HttpResponse(json.dumps(manifest), content_type='application/manifest+json')


class StudentServiceWorkerView(View):
    def get(self, request, *args, **kwargs):
        js = render_to_string(
            'student_app/sw.js',
            {
                'asset_version': getattr(settings, 'STATIC_ASSET_VERSION', '1'),
                'student_app_scope': STUDENT_APP_SCOPE,
                'student_app_manifest_url': '/aluno/manifest.webmanifest',
                'student_app_offline_url': '/aluno/offline/',
                'student_app_css_url': '/static/css/student_app/app.css',
                'student_app_js_url': '/static/js/student_app/pwa.js',
                'student_app_icon_192_url': STUDENT_APP_ICON_192,
                'student_app_icon_512_url': STUDENT_APP_ICON_512,
                'student_app_icon_maskable_url': STUDENT_APP_ICON_MASKABLE_512,
                'student_app_apple_touch_icon_url': STUDENT_APP_APPLE_TOUCH_ICON,
            },
        )
        response = HttpResponse(js, content_type='application/javascript')
        response['Service-Worker-Allowed'] = STUDENT_APP_SCOPE
        return response


class StudentOfflineView(TemplateView):
    template_name = 'student_app/offline.html'


class PublicWorkoutDetailView(View):
    def get(self, request, plan_slug, *args, **kwargs):
        html = _render_public_workout_html(plan_slug)
        return HttpResponse(html)


class PublicWorkoutManifestView(View):
    def get(self, request, plan_slug, *args, **kwargs):
        entry = _get_public_workout_entry(plan_slug)
        manifest = {
            'name': entry['title'],
            'short_name': 'OctoFit',
            'start_url': f'/renan/{entry["slug"]}',
            'scope': PUBLIC_WORKOUT_SCOPE,
            'display': 'standalone',
            'orientation': 'portrait',
            'background_color': entry['background_color'],
            'theme_color': entry['theme_color'],
            'icons': [
                {
                    'src': PUBLIC_WORKOUT_ICON_192,
                    'sizes': '192x192',
                    'type': 'image/png',
                    'purpose': 'any',
                },
                {
                    'src': PUBLIC_WORKOUT_ICON_512,
                    'sizes': '512x512',
                    'type': 'image/png',
                    'purpose': 'any',
                },
                {
                    'src': PUBLIC_WORKOUT_ICON_MASKABLE_512,
                    'sizes': '512x512',
                    'type': 'image/png',
                    'purpose': 'maskable',
                },
            ],
        }
        return HttpResponse(json.dumps(manifest), content_type='application/manifest+json')


class PublicWorkoutServiceWorkerView(View):
    def get(self, request, *args, **kwargs):
        routes = ''.join([f"  '/renan/{slug}',\n" for slug in PUBLIC_WORKOUT_LIBRARY])
        js = f"""const VERSION = 'public-workouts-{getattr(settings, 'STATIC_ASSET_VERSION', '1')}';
const STATIC_CACHE = `${{VERSION}}-static`;
const OFFLINE_URL = '{PUBLIC_WORKOUT_OFFLINE_URL}';
const APP_SCOPE = '{PUBLIC_WORKOUT_SCOPE}';
const ALLOWLIST = [
{routes}  OFFLINE_URL,
  '{PUBLIC_WORKOUT_ICON_192}',
  '{PUBLIC_WORKOUT_ICON_512}',
  '{PUBLIC_WORKOUT_ICON_MASKABLE_512}',
  '{PUBLIC_WORKOUT_APPLE_TOUCH_ICON}',
  '/static/images/student-app-icon.svg',
];

function isAllowedStaticAsset(requestUrl) {{
  if (requestUrl.origin !== self.location.origin) {{
    return false;
  }}
  return ALLOWLIST.includes(requestUrl.pathname);
}}

self.addEventListener('install', (event) => {{
  event.waitUntil(caches.open(STATIC_CACHE).then((cache) => cache.addAll(ALLOWLIST)));
  self.skipWaiting();
}});

self.addEventListener('activate', (event) => {{
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== STATIC_CACHE).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
}});

self.addEventListener('fetch', (event) => {{
  const request = event.request;
  const requestUrl = new URL(request.url);

  if (request.method !== 'GET') {{
    return;
  }}

  if (request.mode === 'navigate') {{
    if (!requestUrl.pathname.startsWith(APP_SCOPE)) {{
      return;
    }}
    event.respondWith(
      fetch(request).catch(async () => {{
        const cache = await caches.open(STATIC_CACHE);
        return cache.match(request, {{ ignoreSearch: true }}) || cache.match(OFFLINE_URL, {{ ignoreSearch: true }});
      }})
    );
    return;
  }}

  if (!isAllowedStaticAsset(requestUrl)) {{
    return;
  }}

  event.respondWith(
    caches.open(STATIC_CACHE).then(async (cache) => {{
      const cached = await cache.match(request, {{ ignoreSearch: true }});
      const networkFetch = fetch(request).then((response) => {{
        if (response.ok) {{
          cache.put(request, response.clone());
        }}
        return response;
      }});
      return cached || networkFetch;
    }})
  );
}});
"""
        response = HttpResponse(js, content_type='application/javascript')
        response['Service-Worker-Allowed'] = PUBLIC_WORKOUT_SCOPE
        return response


class PublicWorkoutOfflineView(View):
    def get(self, request, *args, **kwargs):
        html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Treinos offline</title>
  <style>
    body{margin:0;font-family:Manrope,system-ui,sans-serif;background:#f4efe6;color:#11203b;min-height:100vh;display:grid;place-items:center;padding:24px}
    main{width:min(100%,560px);background:rgba(255,255,255,.92);border:1px solid rgba(17,32,59,.12);border-radius:28px;padding:28px;box-shadow:0 24px 60px rgba(17,32,59,.12)}
    h1{margin:0 0 12px;font-size:clamp(1.8rem,4vw,2.4rem)}
    p{margin:0 0 12px;line-height:1.6;color:#52627e}
    a{display:inline-flex;margin-top:12px;padding:12px 16px;border-radius:999px;background:#11203b;color:#fff;text-decoration:none;font-weight:700}
  </style>
</head>
<body>
  <main>
    <h1>Sem conexão agora.</h1>
    <p>Quando a internet voltar, os links públicos de treino da Juliana e do Bruno voltam a abrir normalmente.</p>
    <p>Se você já abriu um dos treinos antes neste aparelho, tente novamente em alguns segundos.</p>
    <a href="/renan/juliana">Abrir treino da Juliana</a>
  </main>
</body>
</html>"""
        return HttpResponse(html)
