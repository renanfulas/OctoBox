"""Atribuicao first/last touch e eventos server-side do funil Curva."""

from __future__ import annotations

import re
import uuid
import logging
from urllib.parse import urlparse

from django.conf import settings
from django.core import signing
from django.db import IntegrityError, transaction
from django.utils import timezone

from .contracts import current_contract_versions
from .models import PublicWorkoutAcquisitionSession, PublicWorkoutFunnelEvent


ACQUISITION_COOKIE_NAME = 'curva_acquisition'
ACQUISITION_COOKIE_MAX_AGE = 60 * 60 * 24 * 90
_COOKIE_SALT = 'public-workouts-acquisition-v1'
_SAFE_VALUE = re.compile(r'[^a-zA-Z0-9._:@+\-/ ]')
_KNOWN_BOT = re.compile(r'bot\b|spider|crawler|facebookexternalhit|headlesschrome', re.I)
SERVER_EVENT_TYPES = frozenset({
    'landing_viewed', 'tier_selected', 'checkout_started', 'checkout_authorized',
    'invoice_paid', 'checkout_canceled', 'training_intake_completed',
    'nutrition_intake_completed', 'program_published', 'meal_plan_published',
    'program_opened', 'meal_plan_opened', 'subscription_canceled',
    'waitlist_joined',
    'cta_clicked', 'faq_opened', 'pricing_viewed', 'signup_started',
    'signup_submitted', 'signup_invalid', 'signup_failed', 'checkout_redirected',
    'login_required', 'checkout_failed', 'payment_failed',
})
logger = logging.getLogger(__name__)


def tracking_enabled() -> bool:
    return bool(getattr(settings, 'PUBLIC_WORKOUT_FUNNEL_TRACKING_ENABLED', False))


def request_tracking_enabled(request) -> bool:
    return (
        tracking_enabled()
        and not getattr(getattr(request, 'user', None), 'is_staff', False)
        and not _KNOWN_BOT.search(request.META.get('HTTP_USER_AGENT', ''))
    )


def _clean(value: str | None, max_length: int) -> str:
    value = (value or '').strip()[:max_length]
    return _SAFE_VALUE.sub('', value)


def _safe_referrer(request) -> str:
    raw = (request.META.get('HTTP_REFERER') or '').strip()
    if not raw:
        return ''
    parsed = urlparse(raw)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        return ''
    if parsed.hostname == request.get_host().split(':')[0]:
        return ''
    # Only the external host: paths and query strings may contain personal data.
    return _clean(f'{parsed.scheme}://{parsed.hostname}', 180)


def _touch_from_request(request) -> dict[str, str]:
    source = _clean(request.GET.get('utm_source'), 80)
    medium = _clean(request.GET.get('utm_medium'), 80)
    campaign = _clean(request.GET.get('utm_campaign'), 120)
    referrer = _safe_referrer(request)
    if not source and referrer:
        source = _clean(urlparse(referrer).netloc, 80)
        medium = medium or 'referral'
    return {'source': source, 'medium': medium, 'campaign': campaign, 'referrer': referrer}


def _decode_cookie(request) -> uuid.UUID | None:
    value = request.COOKIES.get(ACQUISITION_COOKIE_NAME)
    if not value:
        return None
    try:
        return uuid.UUID(signing.loads(value, salt=_COOKIE_SALT, max_age=ACQUISITION_COOKIE_MAX_AGE))
    except (ValueError, signing.BadSignature, signing.SignatureExpired):
        return None


def get_acquisition_session(request) -> PublicWorkoutAcquisitionSession | None:
    if not request_tracking_enabled(request):
        return None
    session_id = _decode_cookie(request)
    if session_id is None:
        return None
    return PublicWorkoutAcquisitionSession.objects.filter(pk=session_id).first()


def ensure_acquisition_session(request) -> tuple[PublicWorkoutAcquisitionSession | None, bool]:
    if not request_tracking_enabled(request):
        return None, False
    now = timezone.now()
    touch = _touch_from_request(request)
    session = get_acquisition_session(request)
    created = session is None
    if session is None:
        session = PublicWorkoutAcquisitionSession.objects.create(
            first_source=touch['source'], first_medium=touch['medium'],
            first_campaign=touch['campaign'], first_referrer=touch['referrer'],
            last_source=touch['source'], last_medium=touch['medium'],
            last_campaign=touch['campaign'], last_referrer=touch['referrer'],
            landing_variant='curva3-tracking-v1',
            offer_version=current_contract_versions()['offer_version'],
            first_seen_at=now, last_seen_at=now,
        )
    else:
        # Um retorno direto sem UTM nao apaga o ultimo toque conhecido.
        if any(touch.values()):
            session.last_source = touch['source'] or session.last_source
            session.last_medium = touch['medium'] or session.last_medium
            session.last_campaign = touch['campaign'] or session.last_campaign
            session.last_referrer = touch['referrer'] or session.last_referrer
        session.last_seen_at = now
        session.save(update_fields=[
            'last_source', 'last_medium', 'last_campaign', 'last_referrer', 'last_seen_at',
        ])
    return session, created


def attach_acquisition_cookie(response, session: PublicWorkoutAcquisitionSession | None) -> None:
    if session is None:
        return
    response.set_cookie(
        ACQUISITION_COOKIE_NAME,
        signing.dumps(str(session.pk), salt=_COOKIE_SALT, compress=True),
        max_age=ACQUISITION_COOKIE_MAX_AGE,
        httponly=True,
        secure=not settings.DEBUG,
        samesite='Lax',
    )


@transaction.atomic
def bind_acquisition_session(session, *, account, subscription):
    if session is None:
        return None
    # Preserve the original acquisition on returns from another browser.
    # The subscription is OneToOne; blindly rebinding used to raise IntegrityError.
    type(subscription).objects.select_for_update().get(pk=subscription.pk)
    original = PublicWorkoutAcquisitionSession.objects.filter(subscription=subscription).first()
    if original is not None and original.pk != session.pk:
        return original
    session.account = account
    session.subscription = subscription
    session.last_seen_at = timezone.now()
    session.save(update_fields=['account', 'subscription', 'last_seen_at'])
    return session


def record_funnel_event(
    event_type: str,
    *,
    acquisition_session=None,
    account=None,
    subscription=None,
    tier: str = '',
    client_event_id=None,
    correlation_id=None,
) -> PublicWorkoutFunnelEvent | None:
    if not tracking_enabled():
        return None
    if event_type not in SERVER_EVENT_TYPES:
        logger.warning('curva_funnel_event_rejected event_type=%s reason=not_allowlisted', event_type)
        return None
    touch = acquisition_session
    try:
        # Savepoint isolado: uma duplicata nao "envenena" a transacao da
        # view/webhook antes da consulta que recupera o evento existente.
        with transaction.atomic():
            return PublicWorkoutFunnelEvent.objects.create(
                event_type=event_type,
                acquisition_session=acquisition_session,
                account=account,
                subscription=subscription,
                tier=tier or (getattr(subscription, 'tier', '') if subscription else ''),
                channel=(touch.last_medium or touch.first_medium)[:32] if touch else '',
                source=(touch.last_source or touch.first_source) if touch else '',
                medium=(touch.last_medium or touch.first_medium) if touch else '',
                campaign=(touch.last_campaign or touch.first_campaign) if touch else '',
                client_event_id=client_event_id,
                correlation_id=correlation_id,
            )
    except IntegrityError:
        if client_event_id:
            logger.info(
                'curva_funnel_event_duplicate event_type=%s client_event_id=%s',
                event_type, client_event_id,
            )
            return PublicWorkoutFunnelEvent.objects.filter(client_event_id=client_event_id).first()
        raise


__all__ = [
    'ACQUISITION_COOKIE_NAME', 'attach_acquisition_cookie', 'bind_acquisition_session',
    'ensure_acquisition_session', 'get_acquisition_session', 'record_funnel_event',
]
