"""
ARQUIVO: orquestrador do pipeline de importacao de leads.

POR QUE ELE EXISTE:
- junta inspecao, policy e persistencia do job em um unico ponto de coordenacao.

O QUE ESTE ARQUIVO FAZ:
1. inspeciona o arquivo recebido.
2. aplica a policy de frequencia e roteamento.
3. cria o LeadImportJob com status coerente.
4. persiste o arquivo temporario quando o pipeline aceita o processamento.

PONTOS CRITICOS:
- o arquivo temporario so deve ser salvo para jobs aceitos.
- o orquestrador nao executa a importacao real; ele apenas decide e prepara a trilha.
- o status inicial precisa refletir o trilho escolhido para evitar ambiguidade na view.
"""

from dataclasses import dataclass
from pathlib import Path
import os
import tempfile

from django.conf import settings
from django.utils import timezone

from operations.models import LeadImportJob, LeadImportJobStatus, LeadImportProcessingMode
from operations.services.lead_import_inspector import LeadImportInspectionResult, inspect_lead_import_stream
from operations.services.lead_import_policy import LeadImportPolicyDecision, evaluate_lead_import_policy


@dataclass(frozen=True)
class LeadImportOrchestrationResult:
    job: LeadImportJob
    inspection: LeadImportInspectionResult
    policy_decision: LeadImportPolicyDecision
    temp_file_created: bool


def _resolve_uploaded_stream(file_obj):
    return getattr(file_obj, 'file', file_obj)


def _build_initial_job_status(*, policy_decision: LeadImportPolicyDecision) -> str:
    if not policy_decision.allowed:
        return LeadImportJobStatus.REJECTED
    if policy_decision.processing_mode == LeadImportProcessingMode.ASYNC_NIGHT:
        return LeadImportJobStatus.SCHEDULED
    return LeadImportJobStatus.QUEUED


def _build_scheduled_for(*, policy_decision: LeadImportPolicyDecision, now=None):
    if not policy_decision.allowed or policy_decision.processing_mode != LeadImportProcessingMode.ASYNC_NIGHT:
        return None

    current_time = timezone.localtime(now or timezone.now())
    if current_time.hour < 4:
        return current_time

    next_window = (current_time + timezone.timedelta(days=1)).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    return next_window


def _build_temp_upload_dir() -> Path:
    temp_dir = Path(settings.BASE_DIR) / 'tmp' / 'lead_imports'
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def _persist_uploaded_file(*, file_obj) -> str:
    suffix = Path(getattr(file_obj, 'name', '')).suffix or '.tmp'
    temp_dir = _build_temp_upload_dir()
    with tempfile.NamedTemporaryFile(
        delete=False,
        dir=temp_dir,
        prefix='octobox_lead_import_',
        suffix=suffix,
    ) as temp_file:
        if hasattr(file_obj, 'chunks'):
            for chunk in file_obj.chunks():
                temp_file.write(chunk)
        else:
            stream = _resolve_uploaded_stream(file_obj)
            stream.seek(0)
            temp_file.write(stream.read())
            stream.seek(0)
        return os.path.abspath(temp_file.name)


def orchestrate_lead_import_submission(
    *,
    file_obj,
    source_type: str,
    declared_range: str,
    actor,
    today=None,
) -> LeadImportOrchestrationResult:
    stream = _resolve_uploaded_stream(file_obj)
    inspection = inspect_lead_import_stream(
        file_stream=stream,
        source_type=source_type,
        declared_range=declared_range,
    )
    policy_decision = evaluate_lead_import_policy(
        source_type=source_type,
        detected_lead_count=inspection.detected_lead_count,
        today=today,
    )

    temp_file_created = False
    file_path = ''
    if policy_decision.allowed:
        file_path = _persist_uploaded_file(file_obj=file_obj)
        temp_file_created = True

    job = LeadImportJob.objects.create(
        created_by=actor,
        source_type=source_type,
        declared_range=declared_range,
        processing_mode=policy_decision.processing_mode or LeadImportProcessingMode.SYNC,
        status=_build_initial_job_status(policy_decision=policy_decision),
        scheduled_for=_build_scheduled_for(policy_decision=policy_decision),
        original_filename=getattr(file_obj, 'name', ''),
        file_path=file_path,
        detected_lead_count=inspection.detected_lead_count,
        error_count=0 if policy_decision.allowed else 1,
        error_details=[] if policy_decision.allowed else [{'reason_code': policy_decision.reason_code, 'reason_message': policy_decision.reason_message}],
    )

    return LeadImportOrchestrationResult(
        job=job,
        inspection=inspection,
        policy_decision=policy_decision,
        temp_file_created=temp_file_created,
    )


__all__ = ['LeadImportOrchestrationResult', 'orchestrate_lead_import_submission']
