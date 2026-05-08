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


def _get_invitation_student_phone(invitation: StudentAppInvitation) -> str:
    """Busca o telefone do aluno usando schema_context se box estiver vinculado.

    Sprint 2: invitation.student.phone era cross-schema (public->tenant) e quebrava
    quando search_path nao incluia o schema do tenant correto.
    """
    if not invitation.student_id:
        return ''
    schema = invitation.box.schema_name if invitation.box_id else None
    try:
        from students.models import Student
        if schema:
            from django_tenants.utils import schema_context
            with schema_context(schema):
                student = Student.objects.filter(pk=invitation.student_id).first()
        else:
            # Legado: sem box FK, assume tenant ativo no request
            student = Student.objects.filter(pk=invitation.student_id).first()
        return student.phone if student else ''
    except Exception:
        return ''


def build_invitation_whatsapp_url(*, invitation: StudentAppInvitation, invite_url: str) -> str:
    # Sprint 2: invitation.student.phone era cross-schema — agora via _get_invitation_student_phone
    phone = _get_invitation_student_phone(invitation)
    return build_whatsapp_message_href(
        phone=phone,
        message=build_student_invitation_whatsapp_body(
            student_name=invitation.student_name,  # Sprint 2: denormalizado
            invite_url=invite_url,
            box_name=_build_box_display_name(invitation.box_root_slug),
            expires_label=_build_expires_label(invitation),
        ),
    )


def send_invitation_email(*, invitation: StudentAppInvitation, invite_url: str, actor=None):
    subject = build_student_invitation_subject(box_name=_build_box_display_name(invitation.box_root_slug))
    body = build_student_invitation_email_body(
            student_name=invitation.student_name,  # Sprint 2: denormalizado
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
