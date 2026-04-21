"""
ARQUIVO: acoes de convite da central operacional de ativacao do aluno.

POR QUE ELE EXISTE:
- separa o corredor de invites da view monolitica da central operacional.

O QUE ESTE ARQUIVO FAZ:
1. cria convite individual ou aberto para o aluno.
2. cria e pausa link em massa do box.
3. registra auditoria e eventos de onboarding ligados a convite.
"""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from auditing.models import AuditEvent
from shared_support.box_runtime import get_box_runtime_slug

from .application.commands import CreateStudentBoxInviteLinkCommand, CreateStudentInvitationCommand
from .application.use_cases import CreateStudentBoxInviteLink, CreateStudentInvitation
from .forms import StudentInvitationCreateForm
from .funnel_events import record_student_onboarding_event
from .infrastructure.repositories import DjangoStudentIdentityRepository
from .models import StudentBoxInviteLink, StudentOnboardingJourney


class StudentInvitationInviteActionsMixin:
    def _handle_create_invite(self, request):
        form = StudentInvitationCreateForm(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        student = form.cleaned_data['student']
        command = CreateStudentInvitationCommand(
            student_id=student.id,
            invited_email='',
            box_root_slug=get_box_runtime_slug(),
            invite_type=form.cleaned_data['invite_type'],
            onboarding_journey=form.cleaned_data['onboarding_journey'],
            expires_in_days=form.cleaned_data['expires_in_days'],
            actor_id=request.user.id,
        )
        result = CreateStudentInvitation(DjangoStudentIdentityRepository()).execute(command)
        if result.success and result.invitation is not None:
            invite_url = request.build_absolute_uri(
                reverse('student-identity-invite', kwargs={'token': result.invitation.token})
            )
            AuditEvent.objects.create(
                actor=request.user,
                actor_role=self._get_actor_role_slug(request),
                action='student_invitation.created',
                target_model='student_identity.StudentAppInvitation',
                target_id=str(result.invitation.id),
                target_label=result.invitation.student_name,
                description=f'Convite {result.invitation.invite_type} criado para o box {get_box_runtime_slug()}.',
                metadata={
                    'student_id': result.invitation.student_id,
                    'box_root_slug': result.invitation.box_root_slug,
                    'invite_type': result.invitation.invite_type,
                    'invited_email': result.invitation.invited_email,
                },
            )
            record_student_onboarding_event(
                actor=request.user,
                actor_role=self._get_actor_role_slug(request),
                journey=result.invitation.onboarding_journey,
                event='invite_created',
                target_model='student_identity.StudentAppInvitation',
                target_id=str(result.invitation.id),
                target_label=result.invitation.student_name,
                description='Convite do onboarding do aluno criado.',
                metadata={
                    'box_root_slug': result.invitation.box_root_slug,
                    'student_id': result.invitation.student_id,
                    'invitation_id': result.invitation.id,
                    'invite_type': result.invitation.invite_type,
                },
            )
            self._track_invite_creation_anomalies(request, invitation=result.invitation)
            messages.success(
                request,
                f"Convite pronto para {result.invitation.student_name}. Link gerado: {invite_url}",
            )
            return redirect('student-invitation-operations')

        if result.failure_reason == 'open-box-rate-limit-exceeded':
            AuditEvent.objects.create(
                actor=request.user,
                actor_role=self._get_actor_role_slug(request),
                action='student_invitation.rate_limit_blocked',
                target_model='student_identity.StudentAppInvitation',
                target_label=student.full_name,
                description='Tentativa bloqueada por rate limit de invite aberto do box.',
                metadata={
                    'student_id': student.id,
                    'box_root_slug': get_box_runtime_slug(),
                    'invite_type': form.cleaned_data['invite_type'],
                },
            )
        messages.error(request, self._map_failure_reason(result.failure_reason))
        return self.render_to_response(self.get_context_data(form=form))

    def _handle_create_box_link(self, request):
        result = CreateStudentBoxInviteLink(DjangoStudentIdentityRepository()).execute(
            CreateStudentBoxInviteLinkCommand(
                box_root_slug=get_box_runtime_slug(),
                expires_in_days=30,
                max_uses=200,
                actor_id=request.user.id,
            )
        )
        messages.success(
            request,
            f'Link em massa renovado para o box. Token pronto: {request.build_absolute_uri(reverse("student-identity-box-invite", kwargs={"token": result.token}))}',
        )
        record_student_onboarding_event(
            actor=request.user,
            actor_role=self._get_actor_role_slug(request),
            journey=StudentOnboardingJourney.MASS_BOX_INVITE,
            event='link_created',
            target_model='student_identity.StudentBoxInviteLink',
            target_id=str(result.id),
            target_label=get_box_runtime_slug(),
            description='Link em massa criado ou renovado para onboarding do box.',
            metadata={
                'box_root_slug': get_box_runtime_slug(),
                'box_invite_link_id': result.id,
                'box_invite_link_token': result.token,
                'max_uses': result.max_uses,
            },
        )
        return redirect('student-invitation-operations')

    def _handle_pause_box_link(self, request):
        link = (
            StudentBoxInviteLink.objects.filter(
                pk=request.POST.get('box_invite_link_id'),
                box_root_slug=get_box_runtime_slug(),
                revoked_at__isnull=True,
            )
            .first()
        )
        if link is None:
            messages.error(request, 'O link em massa nao foi encontrado para pausa.')
            return redirect('student-invitation-operations')
        link.paused_at = timezone.now()
        link.save(update_fields=['paused_at', 'updated_at'])
        messages.success(request, 'Link em massa pausado. Ele deixa de aceitar novos cadastros ate ser regenerado.')
        return redirect('student-invitation-operations')
