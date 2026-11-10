"""Choose staff recipients for a newly active Curva subscription."""

from django.conf import settings

from .models import PublicWorkoutTier


def staff_alert_recipients(subscription):
    for email in getattr(settings, 'PUBLIC_WORKOUT_STAFF_ALERT_EMAILS', []):
        if (
            subscription.tier == PublicWorkoutTier.ESSENCIAL
            and email.strip().casefold() == 'giovannafontesrios@outlook.com'
        ):
            continue
        yield email
