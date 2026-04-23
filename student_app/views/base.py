"""
ARQUIVO: fundacao compartilhada do app do aluno.

POR QUE ELE EXISTE:
- separa runtime de identidade, cookie de sessao e contexto comum do shell das views de tela.

O QUE ESTE ARQUIVO FAZ:
1. define constantes compartilhadas do PWA do aluno.
2. centraliza mixins de identidade e membership.
3. oferece helper curto para enrollment pendente no onboarding.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from finance.models import Enrollment, EnrollmentStatus
from student_identity.infrastructure.repositories import DjangoStudentIdentityRepository
from student_identity.infrastructure.session import (
    attach_student_session_cookie,
    clear_student_session_cookie,
    get_student_session_cookie_name,
    read_student_session_value,
)
from student_identity.models import StudentBoxMembership, StudentBoxMembershipStatus
from student_identity.security import build_student_device_fingerprint
from student_app.onboarding_state import read_pending_student_onboarding


STUDENT_APP_SCOPE = '/aluno/'
STUDENT_APP_START_URL = '/aluno/'
STUDENT_APP_THEME_COLOR = '#091221'
STUDENT_APP_BACKGROUND_COLOR = '#f5f7fb'
STUDENT_APP_ICON_192 = '/static/images/student-app-icon-192.png'
STUDENT_APP_ICON_512 = '/static/images/student-app-icon-512.png'
STUDENT_APP_ICON_MASKABLE_512 = '/static/images/student-app-icon-maskable-512.png'
STUDENT_APP_APPLE_TOUCH_ICON = '/static/images/student-app-apple-touch-icon.png'


def ensure_pending_enrollment(*, student, plan, source_note: str):
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
        context['student_web_push_public_key'] = getattr(settings, 'STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY', '').strip()
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
            active_membership = next(
                (membership for membership in memberships if membership.box_root_slug == identity.primary_box_root_slug),
                None,
            )
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
