"""Read-only capability diagnostics for payment notification channels.

This module reports configuration readiness only. It never sends a message,
loads recipient identities, or exposes provider credentials and raw errors.
"""

from django.conf import settings


def _receipt(*, status, reason_code, status_label):
    return {
        'status': status,
        'reason_code': reason_code,
        'status_label': status_label,
    }


def _channel(*, key, label, status, reason_code, status_label, delivery_receipt):
    return {
        'key': key,
        'label': label,
        'status': status,
        'status_label': status_label,
        'reason_code': reason_code,
        'recipient_scope': 'verified_per_payment',
        'delivery_receipt': delivery_receipt,
    }


def build_payment_notification_diagnostics():
    """Return a safe, tenant-independent matrix of configured channel capability."""
    provider = (getattr(settings, 'STUDENT_EMAIL_PROVIDER', 'smtp') or 'smtp').strip().lower()
    from_email = (getattr(settings, 'STUDENT_EMAIL_FROM', '') or '').strip()

    if provider == 'resend':
        email_ready = bool(
            (getattr(settings, 'STUDENT_RESEND_API_KEY', '') or '').strip()
            and from_email
        )
        email_reason = 'email_resend_configured' if email_ready else 'email_resend_configuration_missing'
        resend_receipt_secret = (getattr(settings, 'PAYMENT_NOTIFICATION_RESEND_WEBHOOK_SECRET', '') or '').strip()
        email_receipt = (
            _receipt(
                status='endpoint_unverified',
                reason_code='resend_webhook_secret_present_endpoint_unverified',
                status_label='Secret presente; cadastro do endpoint Resend ainda não verificado',
            )
            if resend_receipt_secret
            else _receipt(
                status='configuration_missing',
                reason_code='resend_webhook_secret_missing',
                status_label='Secret de assinatura ausente; callback de entrega indisponível',
            )
        )
    else:
        email_ready = bool(
            provider == 'smtp'
            and from_email
            and (getattr(settings, 'EMAIL_HOST', '') or '').strip().lower() not in {'', 'localhost'}
        )
        email_reason = (
            'email_smtp_configured'
            if email_ready
            else 'email_smtp_configuration_missing'
        )
        email_receipt = _receipt(
            status='not_supported',
            reason_code='email_delivery_receipt_not_supported',
            status_label='O sender atual não oferece callback de entrega nesta integração',
        )

    from student_identity.push_notifications import is_student_web_push_configured

    push_ready = is_student_web_push_configured()
    channels = [
        _channel(
            key='email',
            label='E-mail',
            status='configured' if email_ready else 'configuration_missing',
            status_label='Configurado; entrega ainda não comprovada' if email_ready else 'Configuração pendente',
            reason_code=email_reason,
            delivery_receipt=email_receipt,
        ),
        _channel(
            key='push',
            label='Push',
            status='configured' if push_ready else 'configuration_missing',
            status_label='Configurado; entrega ainda não comprovada' if push_ready else 'Configuração pendente',
            reason_code='push_vapid_configured' if push_ready else 'push_vapid_configuration_missing',
            delivery_receipt=_receipt(
                status='not_supported',
                reason_code='push_device_delivery_not_proven',
                status_label='Aceite do serviço não comprova exibição no aparelho',
            ),
        ),
        _channel(
            key='whatsapp',
            label='WhatsApp',
            status='not_implemented',
            status_label='Indisponível',
            reason_code='whatsapp_sender_not_implemented',
            delivery_receipt=_receipt(
                status='not_implemented',
                reason_code='whatsapp_sender_not_implemented',
                status_label='Sem sender ou callback implementado',
            ),
        ),
    ]
    return {
        'title': 'Disponibilidade das confirmações de pagamento',
        'summary': 'Configuração de envio e confirmação de entrega são capacidades distintas; o callback também precisa de homologação.',
        'recipient_note': 'A elegibilidade do destinatário é verificada para cada pagamento; dados pessoais não são exibidos aqui.',
        'channels': channels,
    }


__all__ = ['build_payment_notification_diagnostics']
