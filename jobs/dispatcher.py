"""
ARQUIVO: dispatcher oficial de jobs da Signal Mesh.

POR QUE ELE EXISTE:
- centraliza o mapeamento entre `job_type` e task concreta.
- permite reprocessamento programado sem espalhar `delay(...)` pela borda.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RegisteredAsyncJob:
    job_type: str
    source_channel: str
    task_name: str


def _registry() -> dict[str, RegisteredAsyncJob]:
    return {
        'student_import_csv': RegisteredAsyncJob(
            job_type='student_import_csv',
            source_channel='operations.student_import',
            task_name='run_csv_student_import_job',
        ),
        'contact_import_csv': RegisteredAsyncJob(
            job_type='contact_import_csv',
            source_channel='operations.contact_import',
            task_name='run_csv_contact_import_job',
        ),
        'project_knowledge_reindex': RegisteredAsyncJob(
            job_type='project_knowledge_reindex',
            source_channel='knowledge.reindex',
            task_name='run_project_knowledge_reindex',
        ),
    }


def list_registered_jobs() -> list[RegisteredAsyncJob]:
    return list(_registry().values())


def get_registered_job(job_type: str) -> RegisteredAsyncJob | None:
    return _registry().get(job_type or '')


def get_job_task(job_type: str):
    registered_job = get_registered_job(job_type)
    if registered_job is None:
        return None

    from knowledge.tasks import run_project_knowledge_reindex
    from operations.tasks import run_csv_contact_import_job, run_csv_student_import_job

    task_map = {
        'run_csv_student_import_job': run_csv_student_import_job,
        'run_csv_contact_import_job': run_csv_contact_import_job,
        'run_project_knowledge_reindex': run_project_knowledge_reindex,
    }
    return task_map[registered_job.task_name]


def build_dispatch_context(
    *,
    job_type: str,
    file_path: str = '',
    actor_id: int | None,
    signal_envelope: dict[str, Any],
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        'job_type': job_type,
        'file_path': file_path,
        'actor_id': actor_id,
        'signal_envelope': signal_envelope,
        'payload': payload or {},
    }


def dispatch_async_job(*, job, dispatch_context: dict[str, Any]):
    job_type = dispatch_context.get('job_type', '')
    task = get_job_task(job_type)
    if task is None:
        raise ValueError(f'unregistered-job-type:{job_type}')

    if job_type == 'project_knowledge_reindex':
        payload = dispatch_context.get('payload') or {}
        return task.delay(
            force=bool(payload.get('force')),
            with_embeddings=bool(payload.get('with_embeddings')),
            job_id=job.id,
            signal_envelope=dispatch_context.get('signal_envelope') or {},
        )

    return task.delay(
        file_path=dispatch_context.get('file_path', ''),
        actor_id=dispatch_context.get('actor_id'),
        job_id=job.id,
        signal_envelope=dispatch_context.get('signal_envelope') or {},
    )


__all__ = [
    'RegisteredAsyncJob',
    'build_dispatch_context',
    'dispatch_async_job',
    'get_job_task',
    'get_registered_job',
    'list_registered_jobs',
]
