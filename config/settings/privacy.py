"""Build private-data feature settings from the shared environment parsers."""


def build_privacy_settings(env_bool, env_list_alias, env_str):
    """Return settings that gate blind indexes and versioned encryption."""
    return {
        'PHONE_BLIND_INDEX_KEY': env_str('PHONE_BLIND_INDEX_KEY', 'dev-default-blind-index-key'),
        'CPF_LOOKUP_INDEX_READY': env_bool('CPF_LOOKUP_INDEX_READY', False),
        'CPF_LOOKUP_INDEX_READY_BOXES': env_list_alias(('CPF_LOOKUP_INDEX_READY_BOXES',), ''),
        'PII_ENCRYPTION_KEYRING_JSON': env_str('PII_ENCRYPTION_KEYRING_JSON', ''),
        'PII_ENCRYPTION_ACTIVE_KEY_ID': env_str('PII_ENCRYPTION_ACTIVE_KEY_ID', ''),
        'WHATSAPP_POLL_WEBHOOK_INSTANCES_JSON': env_str('WHATSAPP_POLL_WEBHOOK_INSTANCES_JSON', ''),
    }


__all__ = ['build_privacy_settings']
