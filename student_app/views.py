from __future__ import annotations

import json

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.views.generic import FormView, TemplateView, View

from shared_support.box_runtime import get_box_runtime_slug
from student_app.application.use_cases import GetStudentDashboard, GetStudentWorkoutPrescription
from student_app.forms import WorkoutPrescriptionForm
from student_identity.infrastructure.repositories import DjangoStudentIdentityRepository
from student_identity.infrastructure.session import (
    attach_student_session_cookie,
    get_student_session_cookie_name,
    read_student_session_value,
)


STUDENT_APP_SCOPE = '/aluno/'
STUDENT_APP_START_URL = '/aluno/'
STUDENT_APP_THEME_COLOR = '#0f172a'
STUDENT_APP_BACKGROUND_COLOR = '#f5efe4'
STUDENT_APP_ICON_192 = '/static/images/student-app-icon-192.png'
STUDENT_APP_ICON_512 = '/static/images/student-app-icon-512.png'
STUDENT_APP_ICON_MASKABLE_512 = '/static/images/student-app-icon-maskable-512.png'
STUDENT_APP_APPLE_TOUCH_ICON = '/static/images/student-app-apple-touch-icon.png'


class StudentIdentityRequiredMixin:
    identity_repository_class = DjangoStudentIdentityRepository

    def dispatch(self, request, *args, **kwargs):
        payload = read_student_session_value(request.COOKIES.get(get_student_session_cookie_name()))
        if payload is None:
            return redirect('student-identity-login')
        identity = self.identity_repository_class().find_identity_by_id(payload.get('identity_id', 0))
        if identity is None or identity.box_root_slug != get_box_runtime_slug():
            return redirect('student-identity-login')
        request.student_identity = identity
        response = super().dispatch(request, *args, **kwargs)
        attach_student_session_cookie(
            response,
            identity_id=identity.id,
            box_root_slug=identity.box_root_slug,
        )
        return response


class StudentHomeView(StudentIdentityRequiredMixin, TemplateView):
    template_name = 'student_app/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dashboard'] = GetStudentDashboard().execute(identity=self.request.student_identity)
        context['student_identity'] = self.request.student_identity
        context['page_title'] = 'Meu Box'
        return context


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
        context['student_identity'] = self.request.student_identity
        return context


class StudentSettingsView(StudentIdentityRequiredMixin, TemplateView):
    template_name = 'student_app/settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_identity'] = self.request.student_identity
        context['box_runtime_slug'] = get_box_runtime_slug()
        return context


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
