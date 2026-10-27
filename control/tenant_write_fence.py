"""Per-tenant write fence shared by HTTP, jobs, and tenant-scoped webhooks.

The advisory lock is held for the full unit of work. A freeze transition takes
the matching exclusive transaction lock, so its commit means all prior guarded
work has drained and subsequent work will observe the durable frozen flag.
"""

from __future__ import annotations

import hashlib
import logging
from contextlib import contextmanager
from functools import wraps
import re

from django.db import connection, transaction
from django_tenants.utils import get_public_schema_name, schema_context

logger = logging.getLogger('control.tenant_write_fence')
_TENANT_SCHEMA_RE = re.compile(r'^box_[a-z0-9_-]{1,59}$')


class TenantWritesFrozen(RuntimeError):
    def __init__(self, schema_name: str, reason: str = ''):
        self.schema_name = schema_name
        self.reason = reason
        super().__init__(f'Tenant writes are frozen for {schema_name}')


class TenantFenceTargetMissing(RuntimeError):
    pass


def _lock_key(schema_name: str) -> int:
    digest = hashlib.sha256(f'octobox:tenant-write-fence:{schema_name}'.encode('utf-8')).digest()
    value = int.from_bytes(digest[:8], byteorder='big', signed=False)
    return value if value < 2**63 else value - 2**64


@contextmanager
def tenant_write_guard(schema_name: str):
    """Hold a shared session lock while work may read/write a tenant.

    Raises ``TenantWritesFrozen`` after taking the lock when the durable Box
    flag is active. The lock is still held while checking that flag, closing
    the race with a concurrent freeze transition.
    """
    if not schema_name or schema_name == get_public_schema_name():
        raise ValueError('tenant_write_guard exige um schema de box')

    key = _lock_key(schema_name)
    acquired = False
    # Avoid logging tenant identifiers here; the shared PII-safe reference
    # helper belongs to a later privacy package and is not a runtime dependency.
    box_ref = 'tenant'
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_lock_shared(%s)', [key])
        acquired = True

        from control.models import Box

        box = Box.objects.filter(schema_name=schema_name).only(
            'schema_name', 'write_frozen_at', 'write_freeze_reason',
        ).first()
        if box is None:
            raise TenantFenceTargetMissing(f'Box desconhecido para schema {schema_name}')
        if box.write_frozen_at is not None:
            raise TenantWritesFrozen(schema_name, box.write_freeze_reason)
        yield box
    finally:
        if acquired:
            try:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_advisory_unlock_shared(%s)', [key])
                    released = cursor.fetchone()[0]
                if not released:
                    logger.error('tenant_write_guard_unlock_missing box_ref=%s', box_ref)
            except Exception as exc:  # noqa: BLE001 — connection loss releases server-side session locks
                logger.error('tenant_write_guard_unlock_failed error_type=%s', type(exc).__name__)
                connection.close()


@contextmanager
def _freeze_transition_lock(schema_name: str):
    if not schema_name or schema_name == get_public_schema_name():
        raise ValueError('transição de fence exige um schema de box')

    from control.models import Box

    with schema_context(get_public_schema_name()):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_xact_lock(%s)', [_lock_key(schema_name)])
            box = Box.objects.select_for_update().filter(schema_name=schema_name).first()
            if box is None:
                raise TenantFenceTargetMissing(f'Box desconhecido para schema {schema_name}')
            yield box


@contextmanager
def tenant_write_exclusive(schema_name: str):
    """Drain guarded work while performing an unfrozen tenant lifecycle operation."""
    with _freeze_transition_lock(schema_name) as box:
        if box.write_frozen_at is not None:
            raise TenantWritesFrozen(schema_name, box.write_freeze_reason)
        yield box


def tenant_write_guarded_command(
    *,
    schema_option: str | None = 'schema',
    write_option: str | None = 'apply',
):
    """Fence an opt-in tenant-writing management-command handler.

    Read-only command modes stay unfenced. Invalid/missing schema input is
    delegated to the command's own argument validation.
    """
    def decorate(handle):
        @wraps(handle)
        def guarded(self, *args, **options):
            from django.core.management.base import CommandError

            if write_option is not None and not options.get(write_option):
                return handle(self, *args, **options)
            if schema_option is None:
                from django.db import connection
                from django_tenants.utils import get_public_schema_name

                schema_name = getattr(connection, 'schema_name', '')
                if not schema_name or schema_name == get_public_schema_name():
                    raise CommandError(
                        'Este comando grava dados tenant; execute-o dentro de um schema de box explícito.'
                    )
                if not _TENANT_SCHEMA_RE.fullmatch(schema_name):
                    raise CommandError(
                        'Este comando só pode gravar em um schema ativo no formato box_<slug>.'
                    )
            else:
                schema_name = options.get(schema_option)
            if not isinstance(schema_name, str):
                return handle(self, *args, **options)
            if not _TENANT_SCHEMA_RE.fullmatch(schema_name):
                return handle(self, *args, **options)

            try:
                with tenant_write_guard(schema_name):
                    return handle(self, *args, **options)
            except TenantWritesFrozen as exc:
                raise CommandError(
                    f'Box {schema_name} está congelado; a operação de escrita não foi iniciada.'
                ) from exc
            except TenantFenceTargetMissing as exc:
                raise CommandError(str(exc)) from exc

        return guarded

    return decorate


def set_tenant_write_fence(*, schema_name: str, frozen: bool, reason: str = '') -> tuple[object, bool]:
    """Freeze or unfreeze one Box, draining all guarded work before commit."""
    with _freeze_transition_lock(schema_name) as box:
        changed = False
        if frozen:
            normalized_reason = str(reason or '').strip()[:255]
            if box.write_frozen_at is None:
                from django.utils import timezone

                box.write_frozen_at = timezone.now()
                box.write_freeze_reason = normalized_reason
                changed = True
            elif box.write_freeze_reason != normalized_reason and normalized_reason:
                box.write_freeze_reason = normalized_reason
                changed = True
        elif box.write_frozen_at is not None or box.write_freeze_reason:
            box.write_frozen_at = None
            box.write_freeze_reason = ''
            changed = True

        if changed:
            box.save(update_fields=['write_frozen_at', 'write_freeze_reason'])
        return box, changed


__all__ = [
    'TenantFenceTargetMissing',
    'TenantWritesFrozen',
    'set_tenant_write_fence',
    'tenant_write_guard',
    'tenant_write_exclusive',
    'tenant_write_guarded_command',
]
