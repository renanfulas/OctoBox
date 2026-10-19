"""Entrega de push da Curva para contas do corredor publico."""

import json
import ipaddress
from urllib.parse import urlsplit

from django.conf import settings
from django.utils import timezone

from .models import PublicWorkoutPushSubscription


# Sem timeout o requests espera para sempre: um gateway pendurado travaria a
# outbox e o worker do descanso, que envia em série.
PUSH_TIMEOUT_SECONDS = 10


def configured():
    return bool(_allowed_hosts()) and all(getattr(settings, key, '').strip() for key in (
        'STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY',
        'STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY',
        'STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT',
    ))


def _allowed_hosts():
    return [
        host.strip().lower().lstrip('.')
        for host in str(getattr(settings, 'PUBLIC_WORKOUT_PUSH_ALLOWED_HOSTS', '') or '').split(',')
        if '.' in host.strip().lstrip('.')
    ]


def subscribe(*, account_id, data, user_agent=''):
    if not isinstance(data, dict):
        raise ValueError('invalid-subscription')
    endpoint = str(data.get('endpoint') or '').strip()
    keys = data.get('keys')
    if not isinstance(keys, dict) or not endpoint or len(endpoint) > 2048 or not keys.get('p256dh') or not keys.get('auth'):
        raise ValueError('invalid-subscription')
    try:
        parsed = urlsplit(endpoint)
    except ValueError as exc:
        raise ValueError('invalid-subscription-endpoint') from exc
    try:
        host = (parsed.hostname or '').lower()
        port = parsed.port
    except ValueError as exc:
        raise ValueError('invalid-subscription-endpoint') from exc
    if parsed.scheme != 'https' or not host or port not in (None, 443) or parsed.username or parsed.password or host.endswith(('.localhost', '.local', '.internal')):
        raise ValueError('invalid-subscription-endpoint')
    if not any(host == allowed or host.endswith('.' + allowed) for allowed in _allowed_hosts()):
        raise ValueError('subscription-host-not-allowed')
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError('invalid-subscription-endpoint')
    existing = PublicWorkoutPushSubscription.objects.filter(endpoint=endpoint).first()
    if existing and existing.account_id != account_id and existing.revoked_at is None:
        raise ValueError('subscription-owned-by-another-account')
    row, _ = PublicWorkoutPushSubscription.objects.get_or_create(
        endpoint=endpoint, defaults={'account_id': account_id},
    )
    if row.account_id != account_id and row.revoked_at is None:
        raise ValueError('subscription-owned-by-another-account')
    row.account_id = account_id
    row.subscription = data
    row.user_agent = user_agent[:255]
    row.revoked_at = None
    row.last_error = ''
    row.save(update_fields=['account', 'subscription', 'user_agent', 'revoked_at', 'last_error', 'updated_at'])
    return row


def send(*, subscription, title, body, url, tag, ttl=60, urgency=None, extra=None, timeout=PUSH_TIMEOUT_SECONDS):
    """Envia um push para um aparelho; False quando o gateway não aceita.

    `extra` entra no payload que o service worker lê (ex.: `renotify`, `vibrate`).
    `urgency` vira o cabeçalho `Urgency` do Web Push: `high` pede entrega
    imediata mesmo com o aparelho em economia de bateria.
    """
    if not configured():
        return False
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        subscription.last_error = 'webpush-unavailable'
        subscription.save(update_fields=['last_error', 'updated_at'])
        return False

    try:
        from student_identity.push_notifications import _build_vapid_private_key

        message = {**(extra or {}), 'title': title, 'body': body, 'url': url, 'tag': tag}
        webpush(
            subscription_info=subscription.subscription,
            data=json.dumps(message),
            vapid_private_key=_build_vapid_private_key(),
            vapid_claims={'sub': settings.STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT},
            ttl=ttl,
            headers={'Urgency': urgency} if urgency else None,
            timeout=timeout,
        )
    except WebPushException as exc:
        status = getattr(getattr(exc, 'response', None), 'status_code', 0)
        if status in (404, 410):
            subscription.revoked_at = timezone.now()
        subscription.last_error = f'webpush-failed:{status or "unknown"}'
        subscription.save(update_fields=['revoked_at', 'last_error', 'updated_at'])
        return False
    except Exception as exc:
        subscription.last_error = f'webpush-error:{type(exc).__name__}'
        subscription.save(update_fields=['last_error', 'updated_at'])
        return False
    subscription.last_push_sent_at = timezone.now()
    subscription.last_error = ''
    subscription.save(update_fields=['last_push_sent_at', 'last_error', 'updated_at'])
    return True


def notify_account(*, account_id, title, body, url, tag):
    results = [
        send(subscription=row, title=title, body=body, url=url, tag=tag)
        for row in PublicWorkoutPushSubscription.objects.filter(account_id=account_id, revoked_at__isnull=True)
    ]
    return all(results)
