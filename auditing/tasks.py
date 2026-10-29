"""Tenant-scoped background writer for audit events.

This task is retained for compatibility with deployments that add Celery
outside the repository's requirements. Callers must pass an explicit tenant
schema and the normalizer fields below; legacy unscoped payloads fail closed.
"""

import logging
import re

try:
    from celery import shared_task
except ImportError:
    def shared_task(*args, **kwargs):
        def decorator(func):
            def wrapper(*wargs, **wkwargs):
                return func(*wargs, **wkwargs)

            wrapper.delay = func
            wrapper.run = func
            return wrapper

        return decorator


logger = logging.getLogger(__name__)
_TENANT_SCHEMA_RE = re.compile(r'^box_[a-z0-9_-]{1,59}$')
_ACTION_RE = re.compile(r'^[A-Za-z0-9_.-]{1,80}$')
_MODEL_RE = re.compile(r'^[A-Za-z0-9_.]{1,120}$')
_ALLOWED_PAYLOAD_KEYS = {
    'tenant_schema',
    'actor_id',
    'action',
    'target_model',
    'target_id',
    'target_label',
    'description',
    'metadata',
}


def _audit_payload_value(data, key, *, default='', max_length=None, pattern=None):
    value = data.get(key, default)
    if not isinstance(value, str):
        raise ValueError('audit-payload-invalid')
    if max_length is not None and len(value) > max_length:
        raise ValueError('audit-payload-invalid')
    if pattern is not None and value and not pattern.fullmatch(value):
        raise ValueError('audit-payload-invalid')
    return value


@shared_task()
def async_log_audit_event(data, tenant_schema=None):
    """Write through the shared sanitizer inside an explicit tenant fence.

    ``description`` is a caller-owned fixed summary/closed enum. Free text is
    not a supported payload. ``target_label`` is deliberately ignored so that
    this legacy corridor cannot persist an arbitrary object string.
    """
    if not isinstance(data, dict) or set(data) - _ALLOWED_PAYLOAD_KEYS:
        raise ValueError('audit-payload-invalid')

    payload_schema = data.get('tenant_schema')
    if tenant_schema and payload_schema and tenant_schema != payload_schema:
        raise ValueError('audit-tenant-schema-mismatch')
    tenant_schema = tenant_schema or payload_schema
    if not isinstance(tenant_schema, str) or not _TENANT_SCHEMA_RE.fullmatch(tenant_schema):
        raise ValueError('tenant-schema-required-for-audit-write')

    actor_id = data.get('actor_id')
    if actor_id is not None and (isinstance(actor_id, bool) or not isinstance(actor_id, int)):
        raise ValueError('audit-payload-invalid')

    action = _audit_payload_value(data, 'action', max_length=80, pattern=_ACTION_RE)
    if not action:
        raise ValueError('audit-payload-invalid')
    target_model = _audit_payload_value(data, 'target_model', max_length=120, pattern=_MODEL_RE)
    target_id = data.get('target_id', '')
    if isinstance(target_id, bool) or not isinstance(target_id, (str, int)):
        raise ValueError('audit-payload-invalid')
    target_id = str(target_id)
    if len(target_id) > 64:
        raise ValueError('audit-payload-invalid')
    description = _audit_payload_value(data, 'description', max_length=500)
    metadata = data.get('metadata', {})
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise ValueError('audit-payload-invalid')

    from auditing.services import _write_audit_event
    from control.tenant_write_fence import tenant_write_guard
    from django_tenants.utils import schema_context

    try:
        with schema_context(tenant_schema):
            with tenant_write_guard(tenant_schema):
                return _write_audit_event(
                    actor_id=actor_id,
                    action=action,
                    target_model=target_model,
                    target_id=target_id,
                    target_label=target_model.rsplit('.', 1)[-1],
                    description=description,
                    metadata=metadata,
                )
    except Exception as exc:
        logger.error('async_audit_event_write_failed error_type=%s', type(exc).__name__)
        raise RuntimeError('async_audit_event_write_failed') from None


__all__ = ['async_log_audit_event']
