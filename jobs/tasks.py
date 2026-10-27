"""
ARQUIVO: tasks operacionais do corredor oficial de jobs.

POR QUE ELE EXISTE:
- expõe o reprocessamento programado como task institucional da malha.
"""

import re

try:
    from celery import shared_task
except ImportError:
    def shared_task(*args, **kwargs):
        def decorator(func):
            def wrapper(*wargs, **wkwargs):
                return func(*wargs, **wkwargs)

            wrapper.delay = func
            return wrapper

        return decorator

from .reprocessing import reprocess_due_async_jobs

_TENANT_SCHEMA_RE = re.compile(r'^box_[a-z0-9_-]{1,59}$')


@shared_task()
def run_due_async_job_retries(limit=25, tenant_schema=None):
    from control.tenant_write_fence import tenant_write_guard
    from django_tenants.utils import schema_context

    if not isinstance(tenant_schema, str) or not _TENANT_SCHEMA_RE.fullmatch(tenant_schema):
        raise ValueError('tenant-schema-required-for-job-reprocessing')

    with schema_context(tenant_schema):
        with tenant_write_guard(tenant_schema):
            return reprocess_due_async_jobs(limit=limit)


__all__ = ['run_due_async_job_retries']
