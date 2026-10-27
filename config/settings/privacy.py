"""Build private-data feature settings from the shared environment parsers."""

from django.core.exceptions import ImproperlyConfigured


def build_privacy_settings(env_bool, env_list_alias, env_str):
    """Return settings that gate blind indexes and versioned encryption."""
    settings = {
        'PHONE_BLIND_INDEX_KEY': env_str('PHONE_BLIND_INDEX_KEY', 'dev-default-blind-index-key'),
        'EMAIL_BLIND_INDEX_KEY': env_str('EMAIL_BLIND_INDEX_KEY', ''),
        'STUDENT_IDENTITY_EMAIL_LOOKUP_INDEX_READY': env_bool(
            'STUDENT_IDENTITY_EMAIL_LOOKUP_INDEX_READY', False,
        ),
        'PUBLIC_WORKOUT_ACCOUNT_EMAIL_LOOKUP_INDEX_READY': env_bool(
            'PUBLIC_WORKOUT_ACCOUNT_EMAIL_LOOKUP_INDEX_READY', False,
        ),
        'PUBLIC_WORKOUT_CHECKOUT_LEAD_EMAIL_LOOKUP_INDEX_READY': env_bool(
            'PUBLIC_WORKOUT_CHECKOUT_LEAD_EMAIL_LOOKUP_INDEX_READY', False,
        ),
        'PUBLIC_WORKOUT_WAITLIST_EMAIL_LOOKUP_INDEX_READY': env_bool(
            'PUBLIC_WORKOUT_WAITLIST_EMAIL_LOOKUP_INDEX_READY', False,
        ),
        'STUDENT_APP_INVITATION_EMAIL_LOOKUP_INDEX_READY': env_bool(
            'STUDENT_APP_INVITATION_EMAIL_LOOKUP_INDEX_READY', False,
        ),
        'STUDENT_APP_INVITATION_EMAIL_ENCRYPTION_WRITE_READY': env_bool(
            'STUDENT_APP_INVITATION_EMAIL_ENCRYPTION_WRITE_READY', False,
        ),
        'PENDING_SIGNUP_EMAIL_LOOKUP_INDEX_READY': env_bool(
            'PENDING_SIGNUP_EMAIL_LOOKUP_INDEX_READY', False,
        ),
        'PENDING_SIGNUP_EMAIL_ENCRYPTION_WRITE_READY': env_bool(
            'PENDING_SIGNUP_EMAIL_ENCRYPTION_WRITE_READY', False,
        ),
        'CPF_LOOKUP_INDEX_READY': env_bool('CPF_LOOKUP_INDEX_READY', False),
        'CPF_LOOKUP_INDEX_READY_BOXES': env_list_alias(('CPF_LOOKUP_INDEX_READY_BOXES',), ''),
        'PII_ENCRYPTION_KEYRING_JSON': env_str('PII_ENCRYPTION_KEYRING_JSON', ''),
        'PII_ENCRYPTION_ACTIVE_KEY_ID': env_str('PII_ENCRYPTION_ACTIVE_KEY_ID', ''),
        'WHATSAPP_POLL_WEBHOOK_INSTANCES_JSON': env_str('WHATSAPP_POLL_WEBHOOK_INSTANCES_JSON', ''),
    }
    validate_email_lookup_settings(settings)
    return settings


def validate_email_lookup_settings(settings):
    """Reject lookup/encryption rollout flags without the HMAC key or reader."""
    get = settings.get if hasattr(settings, 'get') else lambda name, default=False: getattr(settings, name, default)
    lookup_flags = (
        'STUDENT_IDENTITY_EMAIL_LOOKUP_INDEX_READY',
        'PUBLIC_WORKOUT_ACCOUNT_EMAIL_LOOKUP_INDEX_READY',
        'PUBLIC_WORKOUT_CHECKOUT_LEAD_EMAIL_LOOKUP_INDEX_READY',
        'PUBLIC_WORKOUT_WAITLIST_EMAIL_LOOKUP_INDEX_READY',
        'STUDENT_APP_INVITATION_EMAIL_LOOKUP_INDEX_READY',
        'PENDING_SIGNUP_EMAIL_LOOKUP_INDEX_READY',
    )
    writer_requirements = {
        'STUDENT_APP_INVITATION_EMAIL_ENCRYPTION_WRITE_READY':
            'STUDENT_APP_INVITATION_EMAIL_LOOKUP_INDEX_READY',
        'PENDING_SIGNUP_EMAIL_ENCRYPTION_WRITE_READY':
            'PENDING_SIGNUP_EMAIL_LOOKUP_INDEX_READY',
    }
    enabled = [name for name in lookup_flags if get(name, False)]
    if enabled and not get('EMAIL_BLIND_INDEX_KEY', ''):
        raise ImproperlyConfigured('EMAIL_BLIND_INDEX_KEY is required before enabling email lookup indexes')
    for writer_flag, reader_flag in writer_requirements.items():
        if get(writer_flag, False):
            if not get(reader_flag, False):
                raise ImproperlyConfigured(f'{reader_flag} must be enabled before {writer_flag}')
            if not get('EMAIL_BLIND_INDEX_KEY', ''):
                raise ImproperlyConfigured(f'EMAIL_BLIND_INDEX_KEY is required before {writer_flag}')


__all__ = ['build_privacy_settings', 'validate_email_lookup_settings']
