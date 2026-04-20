"""
ARQUIVO: acoes de entrega da central operacional de ativacao do aluno.

POR QUE ELE EXISTE:
- separa o corredor de entrega de e-mail e WhatsApp da view monolitica.

O QUE ESTE ARQUIVO FAZ:
1. envia convite por e-mail.
2. abre handoff de WhatsApp com auditoria e evento de onboarding.
"""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from shared_support.box_runtime import get_box_runtime_slug

from .delivery_audit import record_student_invitation_whatsapp_handoff
from .delivery_gateways import StudentEmailDeliveryError
from .funnel_events import record_student_onboarding_event
from .models import StudentAppInvitation
from .notifications import build_invitation_whatsapp_url, send_invitation_email


class StudentInvitationDeliveryActionsMixin:
    def _handle_send_email(self, request):
        invitation = (
            StudentAppInvitation.objects.select_related('student')
            .filter(pk=request.POST.get('invitation_id'), box_root_slug=get_box_runtime_slug())
            .first()
        )
        if invitation is None:
            messages.error(request, 'O convite escolhido nao foi encontrado.')
            return redirect('student-invitation-operations')
        if invitation.accepted_at:
            messages.info(request, 'Esse convite ja foi aceito pelo aluno.')
            return redirect('student-invitation-operations')
        if invitation.is_expired:
            messages.error(request, 'Esse convite expirou. Gere um novo antes de enviar.')
            return redirect('student-invitation-operations')
        if not invitation.invited_email:
            messages.error(request, 'Esse convite nao possui e-mail de destino.')
            return redirect('student-invitation-operations')

        invite_url = request.build_absolute_uri(
            reverse('student-identity-invite', kwargs={'token': invitation.token})
        )
        try:
            result = send_invitation_email(invitation=invitation, invite_url=invite_url, actor=request.user)
        except StudentEmailDeliveryError:
            messages.error(request, 'Nao foi possivel enviar o e-mail agora. Revise a configuracao do provedor transacional.')
            return redirect('student-invitation-operations')

        messages.success(
            request,
            f'E-mail de convite enviado para {invitation.invited_email} via {result.provider}.',
        )
        return redirect('student-invitation-operations')

    def _handle_open_whatsapp(self, request):
        invitation = (
            StudentAppInvitation.objects.select_related('student')
            .filter(pk=request.POST.get('invitation_id'), box_root_slug=get_box_runtime_slug())
            .first()
        )
        if invitation is None:
            messages.error(request, 'O convite escolhido nao foi encontrado.')
            return redirect('student-invitation-operations')
        if invitation.accepted_at:
            messages.info(request, 'Esse convite ja foi aceito pelo aluno.')
            return redirect('student-invitation-operations')
        if invitation.is_expired:
            messages.error(request, 'Esse convite expirou. Gere um novo antes de enviar mensagem.')
            return redirect('student-invitation-operations')

        invite_url = request.build_absolute_uri(
            reverse('student-identity-invite', kwargs={'token': invitation.token})
        )
        whatsapp_url = build_invitation_whatsapp_url(invitation=invitation, invite_url=invite_url)
        if not whatsapp_url:
            messages.error(request, 'Esse aluno nao possui telefone valido para abrir o WhatsApp.')
            return redirect('student-invitation-operations')

        record_student_invitation_whatsapp_handoff(
            invitation=invitation,
            actor=request.user,
            recipient=invitation.student.phone,
            metadata={'invite_url': invite_url},
        )
        record_student_onboarding_event(
            actor=request.user,
            actor_role=self._get_actor_role_slug(request),
            journey=invitation.onboarding_journey,
            event='whatsapp_handoff_opened',
            target_model='student_identity.StudentAppInvitation',
            target_id=str(invitation.id),
            target_label=invitation.student.full_name,
            description='Handoff de WhatsApp aberto para o convite do onboarding.',
            metadata={
                'box_root_slug': invitation.box_root_slug,
                'student_id': invitation.student_id,
                'invitation_id': invitation.id,
            },
        )
        return redirect(whatsapp_url)
