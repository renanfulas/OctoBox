from django.conf import settings
from django.db import DatabaseError

from guide.models import OperationalRuntimeSetting


WHATSAPP_REPEAT_BLOCK_HOURS_KEY = 'whatsapp_repeat_block_hours'
ALLOWED_WHATSAPP_REPEAT_BLOCK_HOURS = (0, 12, 24)


def get_default_operational_whatsapp_repeat_block_hours():
    return max(0, int(getattr(settings, 'OPERATIONAL_WHATSAPP_REPEAT_BLOCK_HOURS', 24)))


def get_operational_whatsapp_repeat_block_hours():
    default_value = get_default_operational_whatsapp_repeat_block_hours()
    try:
        raw_value = (
            OperationalRuntimeSetting.objects.filter(key=WHATSAPP_REPEAT_BLOCK_HOURS_KEY)
            .values_list('value', flat=True)
            .first()
        )
    except DatabaseError:
        return default_value

    if raw_value in (None, ''):
        return default_value

    try:
        parsed_value = int(raw_value)
    except (TypeError, ValueError):
        return default_value

    if parsed_value not in ALLOWED_WHATSAPP_REPEAT_BLOCK_HOURS:
        return default_value
    return parsed_value


def set_operational_whatsapp_repeat_block_hours(*, hours, actor=None):
    normalized_hours = int(hours)
    if normalized_hours not in ALLOWED_WHATSAPP_REPEAT_BLOCK_HOURS:
        raise ValueError('invalid-repeat-block-hours')

    setting, _ = OperationalRuntimeSetting.objects.update_or_create(
        key=WHATSAPP_REPEAT_BLOCK_HOURS_KEY,
        defaults={
            'value': str(normalized_hours),
            'updated_by': actor,
        },
    )
    return setting