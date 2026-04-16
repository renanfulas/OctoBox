from __future__ import annotations

from shared_support.whatsapp_links import build_whatsapp_message_href
from .delivery_audit import (
    record_student_invitation_delivery_failure,
    record_student_invitation_delivery_success,
)
from .delivery_gateways import StudentEmailDeliveryError, get_student_email_gateway
from .message_templates import (
    build_student_invitation_email_body,
    build_student_invitation_subject,
    build_student_invitation_whatsapp_body,
)
from .models import StudentAppInvitation


def _build_box_display_name(box_root_slug: str) -> str:
    cleaned = (box_root_slug or 'box').replace('-', ' ').strip()
    return cleaned.title() or 'Seu Box'


def _build_expires_label(invitation: StudentAppInvitation) -> str:
    return invitation.expires_at.strftime('%d/%m/%Y às %H:%M')


def build_invitation_whatsapp_url(*, invitation: StudentAppInvitation, invite_url: str) -> str:
    return build_whatsapp_message_href(
        phone=invitation.student.phone,
        message=build_student_invitation_whatsapp_body(
            student_name=invitation.student.full_name,
            invite_url=invite_url,
            box_name=_build_box_display_name(invitation.box_root_slug),
            expires_label=_build_expires_label(invitation),
        ),
    )


def send_invitation_email(*, invitation: StudentAppInvitation, invite_url: str, actor=None):
    subject = build_student_invitation_subject(box_name=_build_box_display_name(invitation.box_root_slug))
    body = build_student_invitation_email_body(
            student_name=invitation.student.full_name,
            invite_url=invite_url,
            box_name=_build_box_display_name(invitation.box_root_slug),
            expires_label=_build_expires_label(invitation),
    )
    gateway = get_student_email_gateway()
    try:
        result = gateway.send(subject=subject, body=body, to_email=invitation.invited_email)
    except StudentEmailDeliveryError as exc:
        record_student_invitation_delivery_failure(
            invitation=invitation,
            actor=actor,
            channel='email',
            provider=getattr(gateway, 'provider_name', 'email'),
            recipient=invitation.invited_email,
            error_message=str(exc),
        )
        raise

    record_student_invitation_delivery_success(
        invitation=invitation,
        actor=actor,
        channel='email',
        provider=result.provider,
        recipient=result.recipient,
        provider_message_id=result.provider_message_id,
        metadata=result.metadata or {},
    )
    return result


__all__ = ['build_invitation_whatsapp_url', 'send_invitation_email']
