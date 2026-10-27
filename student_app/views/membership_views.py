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
from django.db.models import Q
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import TemplateView, View

from auditing.models import AuditEvent
from student_identity.infrastructure.session import attach_student_session_cookie
from student_identity.models import StudentBoxMembershipStatus
from student_identity.security import build_student_device_fingerprint
from .base import StudentAnyMembershipMixin, StudentIdentityRequiredMixin, StudentSessionIdentityMixin


UUID_TOKEN_PATTERN = re.compile(r'(?P<token>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})')


class StudentMembershipPendingView(StudentSessionIdentityMixin, TemplateView):
    template_name = 'student_app/membership_pending.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_membership = getattr(self.request, 'student_active_membership', None)
        pending_membership = (
            active_membership
            if active_membership is not None
            and active_membership.status == StudentBoxMembershipStatus.PENDING_APPROVAL
            else None
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
            messages.error(request, 'Não consegui reconhecer um convite válido nesse texto. Cole o link inteiro que o box te enviou.')
            return redirect(request.META.get('HTTP_REFERER') or 'student-app-settings')

        # Link do grupo (/box-invite/<token>/) e convite individual (/invite/<token>/) vivem em
        # rotas diferentes; mandar o link do grupo para a rota individual dava "convite nao encontrado".
        route_name = 'student-identity-box-invite' if '/box-invite/' in raw_value else 'student-identity-invite'
        return redirect(route_name, token=match.group('token'))


class StudentSwitchBoxView(StudentIdentityRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        target_box_root_slug = (request.POST.get('box_root_slug') or '').strip()
        if not target_box_root_slug:
            messages.error(request, 'Escolha um box válido para trocar o contexto.')
            return redirect('student-app-home')

        from control.models import Box

        target_box = Box.objects.filter(
            Q(schema_name=target_box_root_slug) | Q(slug=target_box_root_slug)
        ).first()
        if target_box is not None:
            if target_box.status != Box.Status.ACTIVE:
                target_membership = None
            else:
                target_aliases = {target_box.schema_name, target_box.slug}
                target_membership = next(
                    (
                        membership
                        for membership in request.student_box_memberships
                        if membership.box_id == target_box.pk
                    ),
                    None,
                ) or next(
                    (
                        membership
                        for membership in request.student_box_memberships
                        if membership.box_id is None
                        and membership.box_root_slug in target_aliases
                    ),
                    None,
                )
        else:
            target_membership = next(
                (
                    membership
                    for membership in request.student_box_memberships
                    if membership.box_root_slug == target_box_root_slug
                ),
                None,
            )
        if target_membership is None:
            messages.error(request, 'Este box não está disponível para esta conta de aluno.')
            return redirect('student-app-home')

        target_membership.last_access_at = target_membership.last_access_at or None
        target_membership.mark_active()
        target_membership.save(update_fields=['status', 'approved_at', 'last_access_at', 'updated_at'])
        request.student_active_box_root_slug = target_membership.box_root_slug
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or ''
        if not url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            next_url = 'student-app-home'
        response = redirect(next_url)
        attach_student_session_cookie(
            response,
            identity_id=request.student_identity.id,
            box_root_slug=request.student_identity.box_root_slug,
            active_box_root_slug=request.student_active_box_root_slug,
            device_fingerprint=build_student_device_fingerprint(request),
        )
        messages.success(request, f'Agora voce esta no contexto do box {target_membership.box_root_slug}.')
        return response


class StudentRequestFreezeView(StudentIdentityRequiredMixin, View):
    """
    Aluno solicita congelamento de matrícula. Não executa o freeze diretamente —
    registra o pedido como AuditEvent para aprovação assíncrona pela recepção.
    """

    def post(self, request, *args, **kwargs):
        raw_days = (request.POST.get('days') or '').strip()
        if not raw_days.isdigit():
            messages.error(request, 'Informe um periodo entre 5 e 90 dias.')
            return redirect('student-app-settings')

        try:
            days = int(raw_days)
            if days < 5 or days > 90:
                messages.error(request, 'Informe um periodo entre 5 e 90 dias.')
                return redirect('student-app-settings')
        except (ValueError, TypeError):
            messages.error(request, 'Informe um período entre 7 e 90 dias.')
            return redirect('student-app-settings')

        student = request.student_identity.student

        AuditEvent.objects.create(
            actor=None,
            actor_role='student',
            action='student_app.freeze_requested',
            target_model='students.Student',
            target_id=str(student.id),
            target_label=student.full_name,
            description=f'Aluno solicitou congelamento de {days} dias via app.',
            metadata={
                'student_id': student.id,
                'box_root_slug': request.student_identity.box_root_slug,
                'days': days,
                'reason': (request.POST.get('reason') or '').strip()[:280],
            },
        )

        messages.success(
            request,
            f'Pedido de congelamento de {days} dias enviado. A recepção vai confirmar em breve.',
        )
        return redirect('student-app-settings')
