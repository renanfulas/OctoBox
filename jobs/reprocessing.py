"""
ARQUIVO: reprocessamento programado de jobs vencidos.

POR QUE ELE EXISTE:
- transforma `next_retry_at` em corredor oficial da malha.
- evita depender apenas do executor local de cada task para retentar.
"""

from django.utils import timezone

from jobs.dispatcher import dispatch_async_job, get_registered_job
from jobs.models import AsyncJob, JobStatus
from monitoring.alert_siren import get_alert_siren_defense_policy
from monitoring.signal_mesh_metrics import record_retry_sweep
from monitoring.signal_mesh_runtime import remember_signal_mesh_sweep


def reprocess_due_async_jobs(*, limit: int = 25, now=None) -> dict[str, object]:
    current_time = now or timezone.now()
    defense_policy = get_alert_siren_defense_policy()
    effective_limit = limit
    if defense_policy.get('job_limit_cap') is not None:
        effective_limit = min(limit, defense_policy['job_limit_cap'])

    due_queryset = AsyncJob.objects.filter(
            status=JobStatus.PENDING,
            next_retry_at__isnull=False,
            next_retry_at__lte=current_time,
        )
    due_backlog = due_queryset.count()
    due_jobs = list(due_queryset.order_by('next_retry_at', 'created_at')[:effective_limit])

    dispatched = []
    skipped = []

    for job in due_jobs:
        result = job.result or {}
        dispatch_context = result.get('dispatch_context') or {}
        registered_job = get_registered_job(job.job_type)

        if registered_job is None:
            skipped.append({'job_id': job.id, 'reason': 'unregistered-job-type'})
            continue

        if not dispatch_context:
            skipped.append({'job_id': job.id, 'reason': 'missing-dispatch-context'})
            continue

        previous_retry_at = job.next_retry_at
        updated_result = {
            **result,
            'retry_dispatch_in_flight': True,
            'last_requeue_at': current_time.isoformat(),
        }
        job.mark_retry_dispatched(result=updated_result)

        try:
            task = dispatch_async_job(job=job, dispatch_context=dispatch_context)
        except Exception:
            job.result = result
            job.next_retry_at = previous_retry_at
            job.save(update_fields=['result', 'next_retry_at'])
            raise

        dispatched.append(
            {
                'job_id': job.id,
                'task_id': getattr(task, 'id', ''),
                'job_type': registered_job.job_type,
            }
        )

    result = {
        'checked_at': current_time.isoformat(),
        'due_backlog': due_backlog,
        'dispatched_count': len(dispatched),
        'skipped_count': len(skipped),
        'dispatched': dispatched,
        'skipped': skipped,
        'alert_siren_level': defense_policy.get('level', ''),
        'effective_limit': effective_limit,
    }
    record_retry_sweep(
        channel='jobs',
        due_backlog=due_backlog,
        dispatched_count=len(dispatched),
        skipped=skipped,
    )
    remember_signal_mesh_sweep(channel='jobs', result=result)
    return result


__all__ = ['reprocess_due_async_jobs']
