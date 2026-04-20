"""
ARQUIVO: corredor de membership e estados excepcionais do app do aluno.

POR QUE ELE EXISTE:
- organiza troca de box, entrada por convite e estados de acesso fora do fluxo principal.

O QUE ESTE ARQUIVO FAZ:
1. renderiza pendencia de aprovacao, suspensao financeira e ausencia de box ativo.
2. trata colagem de convite e troca de box ativa.
"""

from __future__ import annotations

import re

from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import TemplateView, View

from student_identity.infrastructure.session import attach_student_session_cookie
from student_identity.models import StudentBoxMembershipStatus
from student_identity.security import build_student_device_fingerprint
from .base import StudentAnyMembershipMixin, StudentIdentityRequiredMixin, StudentSessionIdentityMixin


UUID_TOKEN_PATTERN = re.compile(r'(?P<token>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})')


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
