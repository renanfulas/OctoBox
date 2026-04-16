from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail import send_mail


class StudentEmailDeliveryError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class StudentEmailDeliveryResult:
    provider: str
    recipient: str
    provider_message_id: str = ''
    metadata: dict | None = None


class ResendStudentEmailGateway:
    provider_name = 'resend'
    endpoint = 'https://api.resend.com/emails'

    def send(self, *, subject: str, body: str, to_email: str) -> StudentEmailDeliveryResult:
        api_key = getattr(settings, 'STUDENT_RESEND_API_KEY', '').strip()
        from_email = getattr(settings, 'STUDENT_EMAIL_FROM', '').strip()
        if not api_key or not from_email:
            raise StudentEmailDeliveryError('resend-not-configured')

        payload = {
            'from': from_email,
            'to': [to_email],
            'subject': subject,
            'text': body,
        }
        request = Request(
            self.endpoint,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        try:
            with urlopen(request, timeout=15) as response:
                response_payload = json.loads(response.read().decode('utf-8') or '{}')
        except HTTPError as exc:
            detail = exc.read().decode('utf-8', errors='ignore') if hasattr(exc, 'read') else ''
            raise StudentEmailDeliveryError(f'resend-http-error:{exc.code}:{detail}') from exc
        except URLError as exc:
            raise StudentEmailDeliveryError('resend-network-error') from exc

        return StudentEmailDeliveryResult(
            provider=self.provider_name,
            recipient=to_email,
            provider_message_id=str(response_payload.get('id', '')).strip(),
            metadata={'response': response_payload},
        )


class DjangoSmtpStudentEmailGateway:
    provider_name = 'smtp'

    def send(self, *, subject: str, body: str, to_email: str) -> StudentEmailDeliveryResult:
        sent_count = send_mail(
            subject=subject,
            message=body,
            from_email=getattr(settings, 'STUDENT_EMAIL_FROM', '') or None,
            recipient_list=[to_email],
            fail_silently=False,
        )
        if sent_count <= 0:
            raise StudentEmailDeliveryError('smtp-send-returned-zero')
        return StudentEmailDeliveryResult(
            provider=self.provider_name,
            recipient=to_email,
            metadata={'sent_count': sent_count},
        )


def get_student_email_gateway():
    provider = getattr(settings, 'STUDENT_EMAIL_PROVIDER', 'smtp').strip().lower()
    if provider == 'resend':
        return ResendStudentEmailGateway()
    return DjangoSmtpStudentEmailGateway()


__all__ = [
    'DjangoSmtpStudentEmailGateway',
    'ResendStudentEmailGateway',
    'StudentEmailDeliveryError',
    'StudentEmailDeliveryResult',
    'get_student_email_gateway',
]
