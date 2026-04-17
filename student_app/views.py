from __future__ import annotations

import json
import re

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.views.generic import FormView, TemplateView, View

from shared_support.box_runtime import get_box_runtime_slug
from student_app.application.use_cases import GetStudentDashboard, GetStudentWorkoutPrescription
from student_app.forms import WorkoutPrescriptionForm
from student_identity.models import StudentBoxMembership, StudentBoxMembershipStatus
from student_identity.infrastructure.repositories import DjangoStudentIdentityRepository
from student_identity.security import build_student_device_fingerprint
from student_identity.infrastructure.session import (
    attach_student_session_cookie,
    get_student_session_cookie_name,
    read_student_session_value,
    clear_student_session_cookie,
)


STUDENT_APP_SCOPE = '/aluno/'
STUDENT_APP_START_URL = '/aluno/'
STUDENT_APP_THEME_COLOR = '#0f172a'
STUDENT_APP_BACKGROUND_COLOR = '#f5efe4'
STUDENT_APP_ICON_192 = '/static/images/student-app-icon-192.png'
STUDENT_APP_ICON_512 = '/static/images/student-app-icon-512.png'
STUDENT_APP_ICON_MASKABLE_512 = '/static/images/student-app-icon-maskable-512.png'
STUDENT_APP_APPLE_TOUCH_ICON = '/static/images/student-app-apple-touch-icon.png'
UUID_TOKEN_PATTERN = re.compile(r'(?P<token>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})')


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
        context['dashboard'] = GetStudentDashboard().execute(identity=self.request.student_identity)
        context['page_title'] = 'Meu Box'
        return self._attach_student_shell_context(context)


class StudentWorkoutView(StudentIdentityRequiredMixin, FormView):
    template_name = 'student_app/workout.html'
    form_class = WorkoutPrescriptionForm

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
        return self._attach_student_shell_context(context)


class StudentSettingsView(StudentIdentityRequiredMixin, TemplateView):
    template_name = 'student_app/settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['box_runtime_slug'] = get_box_runtime_slug()
        return self._attach_student_shell_context(context)


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
