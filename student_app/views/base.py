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

from copy import copy

from django.conf import settings
from django.contrib import messages
from django.db import connection
from django.shortcuts import redirect
from django.urls import reverse

from finance.models import Enrollment, EnrollmentStatus
from student_identity.consent import has_current_consent
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
            # Sprint 2: student/box_root_slug eram cross-schema. Agora usa
            # student_id (referencia fraca) + student_name (denormalizado).
            # So auto-cria a membership legada quando a rota EXIGE membership
            # ativa — nas paredes de estado (StudentAnyMembershipMixin, ex.:
            # sem-box/suspenso-financeiro) isso mascarava "zero membership"
            # como ACTIVE e acionava o gate de consentimento por engano
            # (regressao coberta por test_no_active_box_route_is_never_gated).
            if not self.requires_active_membership:
                return []
            fallback_membership = StudentBoxMembership.objects.create(
                identity=identity,
                student_id=identity.student_id,
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
        context.setdefault('show_student_pwa_activation', context['student_shell_nav'] in {'home', 'settings'})
        context.setdefault('student_pwa_activation_location', context['student_shell_nav'])
        context.setdefault('student_pwa_activation_dismissible', context['student_shell_nav'] == 'home')
        context['student_box_choices'] = [
            {
                'box_root_slug': membership.box_root_slug,
                'is_active': membership.pk == self.request.student_active_membership.pk,
                'is_primary': (
                    membership.box_id == self.request.student_identity.primary_box_id
                    if membership.box_id and self.request.student_identity.primary_box_id
                    else membership.box_root_slug == self.request.student_identity.primary_box_root_slug
                ),
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
        active_box_id = payload.get('active_box_id')
        active_membership = next(
            (membership for membership in memberships if active_box_id and membership.box_id == active_box_id),
            None,
        )
        if active_membership is None:
            active_membership = next(
                (membership for membership in memberships if membership.box_root_slug == active_box_root_slug),
                None,
            )
        if active_membership is None and active_box_root_slug:
            from control.models import Box

            active_box = (
                Box.objects.filter(schema_name=active_box_root_slug).first()
                or Box.objects.filter(slug=active_box_root_slug).first()
            )
            if active_box is not None:
                active_membership = next(
                    (membership for membership in memberships if membership.box_id == active_box.pk),
                    None,
                )
        if active_membership is None:
            active_membership = next(
                (membership for membership in memberships if membership.box_root_slug == identity.primary_box_root_slug),
                None,
            )
        if active_membership is None:
            active_membership = memberships[0]
        return identity, memberships, active_membership

    def _bind_identity_to_active_membership(self, *, request, identity, membership):
        """Expose the per-box Student reference without mutating the shared identity row."""
        if membership is None:
            return identity

        from control.models import Box

        box = membership.box
        if box is None:
            box = (
                Box.objects.filter(schema_name=membership.box_root_slug).first()
                or Box.objects.filter(slug=membership.box_root_slug).first()
            )
        if box is None:
            # Older records may contain a root slug without a Box row. There
            # is no physical tenant to switch to; retain the legacy binding
            # instead of querying a missing schema in the request transaction.
            return identity

        connection.set_tenant(box)
        request.tenant = box
        active_box_root_slug = box.schema_name

        # StudentIdentity is global; its compatibility `student` property is
        # anchored to the primary box. Per-request consumers must instead use
        # the student_id carried by the selected StudentBoxMembership.
        active_identity = copy(identity)
        active_identity._state = copy(identity._state)
        active_identity._state.fields_cache = identity._state.fields_cache.copy()
        active_identity.student_id = membership.student_id
        active_identity.box_id = box.pk
        active_identity.box_root_slug = active_box_root_slug
        active_identity.box = box
        return active_identity

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
        identity = self._bind_identity_to_active_membership(
            request=request, identity=identity, membership=active_membership,
        )
        request.student_identity = identity
        request.student_box_memberships = memberships
        if active_membership is None:
            request.student_active_box_root_slug = ''
        elif active_membership.box_id and identity.box_id == active_membership.box_id:
            request.student_active_box_root_slug = identity.box_root_slug
        else:
            request.student_active_box_root_slug = active_membership.box_root_slug
        request.student_active_membership = active_membership
        # Gate de entrada (PAR-Q + termo, Onda B). So roda para membership ACTIVE
        # resolvido: telas-parede com StudentAnyMembershipMixin (active_membership
        # pode ser None) ou StudentSessionIdentityMixin (PENDING_APPROVAL) ficam de
        # fora por definicao — ver docs/plans/student-parq-waiver-entry-gate-corda.md
        # secao 6.1. As proprias rotas do gate sao excluidas para nao formar loop.
        if (
            getattr(settings, 'STUDENT_CONSENT_GATE_ENABLED', False)
            and active_membership is not None
            and active_membership.status == StudentBoxMembershipStatus.ACTIVE
            and request.path not in (reverse('student-app-consent'), reverse('student-app-clearance'))
        ):
            if not has_current_consent(
                identity=identity,
                box_root_slug=active_membership.box_root_slug,
                box=request.tenant,
            ):
                return redirect('student-app-consent')
            if active_membership.clearance_required and not active_membership.cleared_at:
                return redirect('student-app-clearance')
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
