"""
ARQUIVO: execucao e persistencia do ciclo de jobs de importacao de leads.

POR QUE ELE EXISTE:
- centraliza a execucao real dos `LeadImportJob` fora da view HTTP.
- garante que sync, async_now e async_night compartilhem o mesmo contrato de persistencia.
- evita duplicar a logica de atualizar status, contadores e relatorios em varias tasks.

O QUE ESTE ARQUIVO FAZ:
1. mapeia `source_type` para o parser/importador correto.
2. executa um `LeadImportJob` e persiste o relatorio completo.
3. marca falhas estruturadas quando o arquivo some ou a execucao explode.
4. despacha jobs noturnos vencidos usando a janela `scheduled_for`.

PONTOS CRITICOS:
- o job precisa ir para `running` antes da leitura do arquivo para nao haver ambiguidade operacional.
- duplicatas e erros estruturados devem ser gravados mesmo em trilhos assincronos.
- o arquivo temporario deve ser removido ao final para nao acumular lixo em disco.
"""

import os

from django.utils import timezone

from operations.models import LeadImportJob, LeadImportJobStatus, LeadImportProcessingMode, LeadImportSourceType
from operations.services.contact_importer import build_file_level_error_report, import_contacts_from_stream


SOURCE_TYPE_TO_PLATFORM = {
    LeadImportSourceType.WHATSAPP_LIST: 'whatsapp',
    LeadImportSourceType.TECNOFIT_EXPORT: 'tecnofit',
    LeadImportSourceType.NEXTFIT_EXPORT: 'nextfit',
    LeadImportSourceType.IPHONE_VCF: 'ios_vcard',
}


def _resolve_source_platform(*, source_type: str) -> str:
    return SOURCE_TYPE_TO_PLATFORM.get(source_type, 'whatsapp')


def _resolve_completed_status(*, report: dict) -> str:
    if report.get('duplicates', 0) > 0 or report.get('errors', 0) > 0:
        return LeadImportJobStatus.COMPLETED_WITH_WARNINGS
    return LeadImportJobStatus.COMPLETED


def _persist_report(*, job: LeadImportJob, report: dict, status: str):
    job.success_count = report.get('success', 0)
    job.duplicate_count = report.get('duplicates', 0)
    job.error_count = report.get('errors', 0)
    job.duplicate_details = report.get('duplicate_details', [])
    job.error_details = report.get('error_details', [])
    job.status = status
    job.finished_at = timezone.now()
    job.save(
        update_fields=[
            'success_count',
            'duplicate_count',
            'error_count',
            'duplicate_details',
            'error_details',
            'status',
            'finished_at',
            'updated_at',
        ]
    )


def _mark_running(*, job: LeadImportJob):
    job.status = LeadImportJobStatus.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=['status', 'started_at', 'updated_at'])


def _remove_temp_file(*, file_path: str):
    if file_path and os.path.exists(file_path):
        os.remove(file_path)


def _build_missing_file_report(*, file_path: str) -> dict:
    return build_file_level_error_report(
        reason_code='missing_temp_file',
        reason_message=f'Arquivo temporario de importacao nao encontrado: {file_path}',
    )


def run_lead_import_job(*, job_id: int) -> LeadImportJob:
    job = LeadImportJob.objects.get(pk=job_id)
    _mark_running(job=job)

    if not job.file_path or not os.path.exists(job.file_path):
        report = _build_missing_file_report(file_path=job.file_path)
        _persist_report(job=job, report=report, status=LeadImportJobStatus.FAILED)
        return job

    source_platform = _resolve_source_platform(source_type=job.source_type)
    try:
        with open(job.file_path, 'rb') as stream:
            report = import_contacts_from_stream(
                stream,
                source_platform=source_platform,
                actor=job.created_by,
            )
    except Exception as exc:
        report = build_file_level_error_report(
            reason_code='unexpected_async_error',
            reason_message=str(exc),
        )
        _persist_report(job=job, report=report, status=LeadImportJobStatus.FAILED)
        _remove_temp_file(file_path=job.file_path)
        return job

    final_status = _resolve_completed_status(report=report)
    _persist_report(job=job, report=report, status=final_status)
    _remove_temp_file(file_path=job.file_path)
    return job


def count_due_nightly_lead_import_jobs(*, now=None) -> int:
    current_time = now or timezone.now()
    return LeadImportJob.objects.filter(
        processing_mode=LeadImportProcessingMode.ASYNC_NIGHT,
        status=LeadImportJobStatus.SCHEDULED,
        scheduled_for__isnull=False,
        scheduled_for__lte=current_time,
    ).count()


def dispatch_due_nightly_lead_import_jobs(*, now=None, limit: int = 25) -> dict:
    current_time = now or timezone.now()
    due_jobs = list(
        LeadImportJob.objects.filter(
            processing_mode=LeadImportProcessingMode.ASYNC_NIGHT,
            status=LeadImportJobStatus.SCHEDULED,
            scheduled_for__isnull=False,
            scheduled_for__lte=current_time,
        )
        .order_by('scheduled_for', 'created_at')[:limit]
    )

    processed_job_ids = []
    for job in due_jobs:
        run_lead_import_job(job_id=job.id)
        processed_job_ids.append(job.id)

    return {
        'dispatched_count': len(processed_job_ids),
        'processed_job_ids': processed_job_ids,
        'evaluated_at': current_time.isoformat(),
    }


__all__ = ['count_due_nightly_lead_import_jobs', 'dispatch_due_nightly_lead_import_jobs', 'run_lead_import_job']
