from __future__ import annotations

import json

from django.conf import settings
from django.urls import reverse

from auditing.models import AuditEvent
from student_identity.models import StudentPushSubscription


def is_student_web_push_configured() -> bool:
    return bool(
        getattr(settings, 'STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY', '').strip()
        and getattr(settings, 'STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY', '').strip()
        and getattr(settings, 'STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT', '').strip()
    )


def _normalized_vapid_private_key() -> str:
    return getattr(settings, 'STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY', '').replace('\\n', '\n').strip()


def upsert_student_push_subscription(
    *,
    identity,
    box_root_slug: str,
    subscription_data: dict,
    device_fingerprint: str,
    user_agent: str,
) -> StudentPushSubscription:
    endpoint = str((subscription_data or {}).get('endpoint') or '').strip()
    if not endpoint:
        raise ValueError('subscription-endpoint-missing')
    record, _created = StudentPushSubscription.objects.get_or_create(
        endpoint=endpoint,
        defaults={
            'identity': identity,
            'box_root_slug': box_root_slug or identity.box_root_slug,
        },
    )
    record.identity = identity
    record.box_root_slug = box_root_slug or identity.box_root_slug
    record.subscription = subscription_data or {}
    record.device_fingerprint = (device_fingerprint or '').strip()
    record.user_agent = (user_agent or '')[:255]
    record.mark_seen()
    record.save(
        update_fields=[
            'identity',
            'box_root_slug',
            'subscription',
            'device_fingerprint',
            'user_agent',
            'last_seen_at',
            'revoked_at',
            'last_error_at',
            'last_error_message',
            'updated_at',
        ]
    )
    return record


def revoke_student_push_subscription(*, endpoint: str) -> bool:
    normalized_endpoint = (endpoint or '').strip()
    if not normalized_endpoint:
        return False
    record = StudentPushSubscription.objects.filter(endpoint=normalized_endpoint).first()
    if record is None:
        return False
    record.mark_revoked(error_message='revoked-by-client')
    record.save(update_fields=['revoked_at', 'last_error_at', 'last_error_message', 'updated_at'])
    return True


def send_student_web_push_notification(
    *,
    subscription: StudentPushSubscription,
    title: str,
    body: str,
    url: str,
    tag: str,
) -> bool:
    if not is_student_web_push_configured():
        return False

    from pywebpush import WebPushException, webpush

    payload = {
        'title': title,
        'body': body,
        'url': url,
        'tag': tag,
        'icon': '/static/images/student-app-icon-192.png',
        'badge': '/static/images/student-app-icon-192.png',
    }

    try:
        webpush(
            subscription_info=subscription.subscription,
            data=json.dumps(payload),
            vapid_private_key=_normalized_vapid_private_key(),
            vapid_claims={'sub': settings.STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT},
            ttl=60,
        )
    except WebPushException as exc:
        response = getattr(exc, 'response', None)
        status_code = getattr(response, 'status_code', 0)
        error_message = f'webpush-failed:{status_code or "unknown"}'
        if status_code in {404, 410}:
            subscription.mark_revoked(error_message=error_message)
            subscription.save(update_fields=['revoked_at', 'last_error_at', 'last_error_message', 'updated_at'])
        else:
            subscription.mark_push_failed(error_message=error_message)
            subscription.save(update_fields=['last_error_at', 'last_error_message', 'updated_at'])
        AuditEvent.objects.create(
            actor=None,
            actor_role='',
            action='student_push.delivery_failed',
            target_model='student_identity.StudentPushSubscription',
            target_id=str(subscription.id),
            target_label=subscription.identity.student.full_name,
            description='Falha ao enviar notificacao push para o app do aluno.',
            metadata={
                'box_root_slug': subscription.box_root_slug,
                'endpoint': subscription.endpoint[:180],
                'status_code': status_code,
                'tag': tag,
            },
        )
        return False

    subscription.mark_push_sent()
    subscription.save(update_fields=['last_push_sent_at', 'last_error_at', 'last_error_message', 'updated_at'])
    AuditEvent.objects.create(
        actor=None,
        actor_role='',
        action='student_push.delivered',
        target_model='student_identity.StudentPushSubscription',
        target_id=str(subscription.id),
        target_label=subscription.identity.student.full_name,
        description='Notificacao push enviada para o app do aluno.',
        metadata={
            'box_root_slug': subscription.box_root_slug,
            'endpoint': subscription.endpoint[:180],
            'tag': tag,
        },
    )
    return True


def build_student_push_welcome_url() -> str:
    return reverse('student-app-home')
