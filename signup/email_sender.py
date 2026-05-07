"""
ARQUIVO: sender de email transacional (HTML + texto) para o fluxo Early Adopter.

POR QUE ELE EXISTE:
- O gateway compartilhado em student_identity/delivery_gateways.py so envia texto plano.
- Onboarding pos-pagamento merece HTML bonito (alto sinal de qualidade da marca).
- Isolamos aqui para nao impactar fluxos existentes do gateway compartilhado.

O QUE ESTE ARQUIVO FAZ:
1. Le STUDENT_EMAIL_PROVIDER (smtp ou resend) do settings — mesma config existente.
2. Envia text + html via Django EmailMultiAlternatives (SMTP) ou Resend HTTP API.
3. Reusa STUDENT_EMAIL_FROM e STUDENT_RESEND_API_KEY ja configurados.

PONTOS CRITICOS:
- Em SMTP: usa EmailMultiAlternatives com text fallback + HTML (multipart/alternative).
- Em Resend: payload tem 'text' (fallback) e 'html'.
- Fallback de texto sempre presente — clientes legacy nao deixam de receber.
- Erros de envio levantam StudentEmailDeliveryError (interface compartilhada).
"""
from __future__ import annotations

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from student_identity.delivery_gateways import (
    StudentEmailDeliveryError,
    StudentEmailDeliveryResult,
)


logger = logging.getLogger(__name__)


_RESEND_ENDPOINT = 'https://api.resend.com/emails'


def send_html_email(*, subject: str, text_body: str, html_body: str, to_email: str) -> StudentEmailDeliveryResult:
    """Despacha email com HTML alternativo, escolhendo o provider via settings.

    Mesma interface do gateway compartilhado (retorna StudentEmailDeliveryResult,
    levanta StudentEmailDeliveryError em falha).
    """
    provider = (getattr(settings, 'STUDENT_EMAIL_PROVIDER', 'smtp') or 'smtp').strip().lower()
    if provider == 'resend':
        return _send_via_resend(subject=subject, text_body=text_body, html_body=html_body, to_email=to_email)
    return _send_via_smtp(subject=subject, text_body=text_body, html_body=html_body, to_email=to_email)


def _send_via_smtp(*, subject, text_body, html_body, to_email) -> StudentEmailDeliveryResult:
    from_email = (getattr(settings, 'STUDENT_EMAIL_FROM', '') or '').strip() or None
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=[to_email],
    )
    msg.attach_alternative(html_body, 'text/html')
    try:
        sent_count = msg.send(fail_silently=False)
    except Exception as exc:
        raise StudentEmailDeliveryError(f'smtp-send-error:{exc}') from exc
    if sent_count <= 0:
        raise StudentEmailDeliveryError('smtp-send-returned-zero')
    return StudentEmailDeliveryResult(
        provider='smtp',
        recipient=to_email,
        metadata={'sent_count': sent_count, 'has_html': True},
    )


def _send_via_resend(*, subject, text_body, html_body, to_email) -> StudentEmailDeliveryResult:
    api_key = (getattr(settings, 'STUDENT_RESEND_API_KEY', '') or '').strip()
    from_email = (getattr(settings, 'STUDENT_EMAIL_FROM', '') or '').strip()
    if not api_key or not from_email:
        raise StudentEmailDeliveryError('resend-not-configured')

    payload = {
        'from': from_email,
        'to': [to_email],
        'subject': subject,
        'text': text_body,
        'html': html_body,
    }
    request = Request(
        _RESEND_ENDPOINT,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urlopen(request, timeout=15) as response:
            body = response.read().decode('utf-8') or '{}'
            response_payload = json.loads(body)
    except HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='ignore') if hasattr(exc, 'read') else ''
        raise StudentEmailDeliveryError(f'resend-http-error:{exc.code}:{detail}') from exc
    except URLError as exc:
        raise StudentEmailDeliveryError('resend-network-error') from exc

    return StudentEmailDeliveryResult(
        provider='resend',
        recipient=to_email,
        provider_message_id=str(response_payload.get('id', '')).strip(),
        metadata={'response': response_payload, 'has_html': True},
    )


__all__ = ['send_html_email']
