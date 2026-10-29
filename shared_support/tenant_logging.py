"""Privacy-preserving correlation references for tenant operational logs."""

from __future__ import annotations

import hashlib
import hmac

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def tenant_log_ref(identifier) -> str:
    """Return a stable, non-reversible tenant reference for process logs.

    The HMAC uses Django's existing SECRET_KEY, so no additional deployment
    secret is introduced. Rotation of SECRET_KEY intentionally rotates refs.
    Pass the canonical Box primary key where available; schema names are a
    fallback for call sites that run before resolving a Box instance.
    """
    value = getattr(identifier, 'pk', None)
    if value is not None:
        material = f'box-pk:{value}'
    else:
        value = str(identifier or '').strip()
        if not value:
            return 'tenant:unknown'
        material = f'tenant-key:{value}'

    try:
        secret = str(getattr(settings, 'SECRET_KEY', '') or '').encode('utf-8')
    except ImproperlyConfigured:
        return 'tenant:unavailable'
    if not secret:
        return 'tenant:unavailable'
    digest = hmac.new(
        secret,
        f'octobox:tenant-log-ref:v1:{material}'.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()[:16]
    return f'tenant:{digest}'
