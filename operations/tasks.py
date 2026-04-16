import logging
import os
from datetime import datetime

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

from integrations.mesh import SignalEnvelope, build_signal_envelope
from integrations.mesh import classify_duplicate, classify_retryable, decide_retry
from jobs.base import build_job_result
from jobs.models import AsyncJob
from operations.services.contact_importer import import_contacts_from_stream
from operations.services.student_importer import StudentImporter

logger = logging.getLogger('octobox.jobs')


def _hydrate_signal_envelope(payload: dict | None, *, fallback_source_channel: str) -> SignalEnvelope:
    payload = payload or {}
    occurred_at = payload.get('occurred_at')
    if occurred_at:
        from datetime import datetime

        occurred_at = datetime.fromisoformat(occurred_at)
    return build_signal_envelope(
        correlation_id=payload.get('correlation_id', ''),
        idempotency_key=payload.get('idempotency_key', ''),
        source_channel=payload.get('source_channel', '') or fallback_source_channel,
        occurred_at=occurred_at,
        raw_reference=payload.get('raw_reference', ''),
    )


def _build_completed_job_payload(*, report, envelope: SignalEnvelope, message: str) -> dict:
    result = build_job_result(
        success=True,
        message=message,
        metadata={'report': report},
        envelope=envelope,
    )
    return {
        'status': 'completed',
        'message': result.message,
        'report': report,
        'signal_envelope': result.metadata['signal_envelope'],
    }


def _build_already_running_payload(*, envelope: SignalEnvelope) -> dict:
    failure = classify_duplicate(reason='already-running')
    result = build_job_result(
        success=False,
        message='already_running',
        metadata={'failure_kind': failure.kind, 'retryable': failure.retryable},
        envelope=envelope,
    )
    return {
        'status': 'already_running',
        'message': result.message,
        'failure_kind': failure.kind,
        'retryable': failure.retryable,
        'signal_envelope': result.metadata['signal_envelope'],
    }


def _build_failed_job_payload(
    *,
    envelope: SignalEnvelope,
    error: Exception,
    attempts: int = 0,
    max_attempts: int = 3,
) -> dict:
    failure = classify_retryable(reason=error.__class__.__name__.lower())
    decision = decide_retry(
        failure_kind=failure.kind,
        attempts=attempts,
        max_attempts=max_attempts,
        reason=failure.reason,
        base_delay_seconds=30,
        cooldown_seconds=30,
    )
    result = build_job_result(
        success=False,
        message='failed',
        metadata={
            'error': str(error),
            'failure_kind': failure.kind,
            'retryable': decision.should_retry,
            **decision.to_metadata(),
        },
        envelope=envelope,
    )
    return {
        'status': 'failed',
        'message': result.message,
        'error': str(error),
        'failure_kind': failure.kind,
        'retryable': decision.should_retry,
        'retry_action': decision.action,
        'attempt_number': decision.attempt_number,
        'max_attempts': decision.max_attempts,
        'next_retry_at': decision.next_retry_at.isoformat() if decision.next_retry_at else '',
        'signal_envelope': result.metadata['signal_envelope'],
    }


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=30,
    retry_kwargs={'max_retries': 3},
)
def run_csv_contact_import_job(self, file_path, actor_id=None, job_id=None, signal_envelope=None):
    job = AsyncJob.objects.filter(pk=job_id).first() if job_id else None
    envelope = _hydrate_signal_envelope(signal_envelope, fallback_source_channel='operations.contact_import')

    if job and not job.start():
        return _build_already_running_payload(envelope=envelope)

    try:
        with open(file_path, 'rb') as stream:
            report = import_contacts_from_stream(stream, source_platform='tecnofit', actor=actor_id)

        if 'octobox_import_' in file_path:
            os.remove(file_path)

        payload = _build_completed_job_payload(
            report=report,
            envelope=envelope,
            message='completed',
        )
        if job:
            job.finish(result=payload)

        return payload
    except Exception as exc:
        retry_count = getattr(getattr(self, 'request', None), 'retries', 0) if self else 0
        max_attempts = (getattr(self, 'max_retries', 3) + 1) if self else 3
        failed_payload = _build_failed_job_payload(
            envelope=envelope,
            error=exc,
            attempts=retry_count,
            max_attempts=max_attempts,
        )
        logger.error(
            'Falha no Job %s (corr=%s): %s',
            job_id,
            envelope.correlation_id,
            str(exc),
            exc_info=True,
        )
        if job:
            if failed_payload['retryable'] and failed_payload['retry_action'] == 'retry':
                next_retry_at = (
                    datetime.fromisoformat(failed_payload['next_retry_at'])
                    if failed_payload['next_retry_at']
                    else None
                )
                job.schedule_retry(
                    result=failed_payload,
                    next_retry_at=next_retry_at,
                    attempt_number=failed_payload['attempt_number'],
                    failure_kind=failed_payload['failure_kind'],
                )
            else:
                job.fail(
                    error=exc,
                    result=failed_payload,
                    failure_kind=failed_payload['failure_kind'],
                )
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=60,
    retry_kwargs={'max_retries': 3},
)
def run_csv_student_import_job(self, file_path, actor_id=None, job_id=None, signal_envelope=None):
    job = AsyncJob.objects.filter(pk=job_id).first() if job_id else None
    envelope = _hydrate_signal_envelope(signal_envelope, fallback_source_channel='operations.student_import')

    if job and not job.start():
        return _build_already_running_payload(envelope=envelope)

    try:
        importer = StudentImporter()
        report = importer.import_from_file(file_path)

        if 'octobox_import_' in file_path:
            os.remove(file_path)

        payload = _build_completed_job_payload(
            report=report,
            envelope=envelope,
            message='completed',
        )
        if job:
            job.finish(result=payload)

        return payload
    except Exception as exc:
        retry_count = getattr(getattr(self, 'request', None), 'retries', 0) if self else 0
        max_attempts = (getattr(self, 'max_retries', 3) + 1) if self else 3
        failed_payload = _build_failed_job_payload(
            envelope=envelope,
            error=exc,
            attempts=retry_count,
            max_attempts=max_attempts,
        )
        logger.error(
            'Student Import Job Failed %s (corr=%s): %s',
            job_id,
            envelope.correlation_id,
            str(exc),
            exc_info=True,
        )
        if job:
            if failed_payload['retryable'] and failed_payload['retry_action'] == 'retry':
                next_retry_at = (
                    datetime.fromisoformat(failed_payload['next_retry_at'])
                    if failed_payload['next_retry_at']
                    else None
                )
                job.schedule_retry(
                    result=failed_payload,
                    next_retry_at=next_retry_at,
                    attempt_number=failed_payload['attempt_number'],
                    failure_kind=failed_payload['failure_kind'],
                )
            else:
                job.fail(
                    error=exc,
                    result=failed_payload,
                    failure_kind=failed_payload['failure_kind'],
                )
        raise
