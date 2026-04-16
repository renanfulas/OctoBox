from __future__ import annotations

from django.utils import timezone

from auditing.services import log_audit_event
from .models import StudentAppInvitation, StudentInvitationChannel, StudentInvitationDelivery, StudentInvitationDeliveryStatus


def record_student_invitation_delivery_success(
    *,
    invitation: StudentAppInvitation,
    actor,
    channel: str,
    provider: str,
    recipient: str,
    provider_message_id: str = '',
    metadata: dict | None = None,
):
    delivery = StudentInvitationDelivery.objects.create(
        invitation=invitation,
        channel=channel,
        provider=provider,
        status=StudentInvitationDeliveryStatus.SENT,
        recipient=recipient,
        requested_by=actor,
        provider_message_id=provider_message_id,
        sent_at=timezone.now(),
        metadata=metadata or {},
    )
    log_audit_event(
        actor=actor,
        action='student_invitation.delivery.sent',
        target=invitation,
        description=f'Convite do app do aluno enviado por {channel}.',
        metadata={
            'channel': channel,
            'provider': provider,
            'recipient': recipient,
            'delivery_id': delivery.id,
            'provider_message_id': provider_message_id,
        },
    )
    return delivery


def record_student_invitation_delivery_failure(
    *,
    invitation: StudentAppInvitation,
    actor,
    channel: str,
    provider: str,
    recipient: str,
    error_message: str,
    metadata: dict | None = None,
):
    delivery = StudentInvitationDelivery.objects.create(
        invitation=invitation,
        channel=channel,
        provider=provider,
        status=StudentInvitationDeliveryStatus.FAILED,
        recipient=recipient,
        requested_by=actor,
        failed_at=timezone.now(),
        error_message=(error_message or '')[:255],
        metadata=metadata or {},
    )
    log_audit_event(
        actor=actor,
        action='student_invitation.delivery.failed',
        target=invitation,
        description=f'Falha no envio do convite do app do aluno por {channel}.',
        metadata={
            'channel': channel,
            'provider': provider,
            'recipient': recipient,
            'delivery_id': delivery.id,
            'error_message': (error_message or '')[:255],
        },
    )
    return delivery


def record_student_invitation_whatsapp_handoff(
    *,
    invitation: StudentAppInvitation,
    actor,
    recipient: str,
    metadata: dict | None = None,
):
    delivery = StudentInvitationDelivery.objects.create(
        invitation=invitation,
        channel=StudentInvitationChannel.WHATSAPP,
        provider='whatsapp_link',
        status=StudentInvitationDeliveryStatus.SENT,
        recipient=recipient,
        requested_by=actor,
        sent_at=timezone.now(),
        metadata=metadata or {},
    )
    log_audit_event(
        actor=actor,
        action='student_invitation.whatsapp.handoff',
        target=invitation,
        description='Equipe encaminhou o convite do app do aluno para o fluxo manual via WhatsApp.',
        metadata={
            'channel': StudentInvitationChannel.WHATSAPP,
            'provider': 'whatsapp_link',
            'recipient': recipient,
            'delivery_id': delivery.id,
            **(metadata or {}),
        },
    )
    return delivery


__all__ = [
    'record_student_invitation_delivery_failure',
    'record_student_invitation_delivery_success',
    'record_student_invitation_whatsapp_handoff',
]
