"""
ARQUIVO: tasks operacionais do corredor oficial de jobs.

POR QUE ELE EXISTE:
- expõe o reprocessamento programado como task institucional da malha.
"""

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


@shared_task
def run_due_async_job_retries(limit=25):
    return reprocess_due_async_jobs(limit=limit)


__all__ = ['run_due_async_job_retries']
