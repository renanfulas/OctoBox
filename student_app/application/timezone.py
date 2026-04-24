from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.utils import timezone


def resolve_box_timezone(*, box_root_slug: str | None = None) -> ZoneInfo:
    timezone_name = getattr(settings, 'TIME_ZONE', 'UTC')
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo('UTC')


def localize_box_datetime(value, *, box_root_slug: str | None = None):
    if value is None:
        return None
    return timezone.localtime(value, resolve_box_timezone(box_root_slug=box_root_slug))
