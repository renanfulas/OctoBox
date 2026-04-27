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


def send_session_cancelled_push(*, session, box_root_slug: str) -> int:
    """
    Envia push de cancelamento para todos os alunos com reserva ativa na sessão.

    Callsite: chame esta função imediatamente após mudar ClassSession.status = 'canceled'
    e antes de salvar, ou em um sinal post_save. Exemplo:

        from student_identity.push_notifications import send_session_cancelled_push
        session.status = 'canceled'
        session.save(update_fields=['status', 'updated_at'])
        send_session_cancelled_push(session=session, box_root_slug=box_root_slug)

    Retorna o número de pushes enviados com sucesso.
    """
    if not is_student_web_push_configured():
        return 0

    from operations.models import Attendance, AttendanceStatus

    student_ids = list(
        Attendance.objects.filter(
            session=session,
            status__in=[AttendanceStatus.BOOKED, AttendanceStatus.CHECKED_IN],
        ).values_list('student_id', flat=True)
    )
    if not student_ids:
        return 0

    subscriptions = StudentPushSubscription.objects.filter(
        identity__student_id__in=student_ids,
        box_root_slug=box_root_slug,
        revoked_at__isnull=True,
    ).select_related('identity__student')

    session_time = session.scheduled_at.strftime('%d/%m %H:%M') if hasattr(session.scheduled_at, 'strftime') else str(session.scheduled_at)
    sent = 0
    for sub in subscriptions:
        ok = send_student_web_push_notification(
            subscription=sub,
            title='Aula cancelada',
            body=f'{session.title} de {session_time} foi cancelada. Fique à vontade para reservar outra.',
            url=reverse('student-app-grade'),
            tag=f'session-cancelled-{session.pk}',
        )
        if ok:
            sent += 1
    return sent
