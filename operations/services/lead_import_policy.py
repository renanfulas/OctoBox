"""
ARQUIVO: policy central do pipeline de importacao de leads.

POR QUE ELE EXISTE:
- concentra a regra de negocio de frequencia e roteamento da importacao de leads.

O QUE ESTE ARQUIVO FAZ:
1. conta uso diario e mensal por tipo de importacao.
2. decide o trilho de processamento pelo volume real detectado.
3. devolve um contrato explicito para a camada de orquestracao.

PONTOS CRITICOS:
- esta policy nao deve depender da selecao do usuario como verdade final.
- jobs rejeitados nao contam como upload aceito para frequencia.
- qualquer mudanca de faixa ou limite deve ser centralizada aqui.
"""

from dataclasses import dataclass
from datetime import date

from django.db.models import QuerySet
from django.utils import timezone

from operations.models import LeadImportJob, LeadImportJobStatus, LeadImportProcessingMode


MAX_SYNC_LEADS = 200
MAX_BACKGROUND_LEADS = 500
MAX_NIGHT_LEADS = 2000
DAILY_UPLOAD_LIMIT = 1
MONTHLY_UPLOAD_LIMIT = 3


@dataclass(frozen=True)
class LeadImportPolicyDecision:
    allowed: bool
    processing_mode: str
    reason_code: str
    reason_message: str
    detected_lead_count: int
    daily_usage: int
    monthly_usage: int


def _build_month_start(reference_date: date) -> date:
    return reference_date.replace(day=1)


def _build_accepted_jobs_queryset(*, source_type: str) -> QuerySet[LeadImportJob]:
    return LeadImportJob.objects.filter(source_type=source_type).exclude(status=LeadImportJobStatus.REJECTED)


def count_daily_import_usage(*, source_type: str, today: date | None = None) -> int:
    today = today or timezone.localdate()
    return _build_accepted_jobs_queryset(source_type=source_type).filter(created_at__date=today).count()


def count_monthly_import_usage(*, source_type: str, today: date | None = None) -> int:
    today = today or timezone.localdate()
    month_start = _build_month_start(today)
    return _build_accepted_jobs_queryset(source_type=source_type).filter(created_at__date__gte=month_start).count()


def decide_lead_import_processing_mode(*, detected_lead_count: int) -> str:
    if detected_lead_count <= MAX_SYNC_LEADS:
        return LeadImportProcessingMode.SYNC
    if detected_lead_count <= MAX_BACKGROUND_LEADS:
        return LeadImportProcessingMode.ASYNC_NOW
    if detected_lead_count <= MAX_NIGHT_LEADS:
        return LeadImportProcessingMode.ASYNC_NIGHT
    return ''


def evaluate_lead_import_policy(
    *,
    source_type: str,
    detected_lead_count: int,
    today: date | None = None,
) -> LeadImportPolicyDecision:
    today = today or timezone.localdate()
    daily_usage = count_daily_import_usage(source_type=source_type, today=today)
    monthly_usage = count_monthly_import_usage(source_type=source_type, today=today)

    if detected_lead_count <= 0:
        return LeadImportPolicyDecision(
            allowed=False,
            processing_mode='',
            reason_code='empty_or_invalid_count',
            reason_message='Nenhum lead valido foi encontrado no arquivo.',
            detected_lead_count=detected_lead_count,
            daily_usage=daily_usage,
            monthly_usage=monthly_usage,
        )

    if daily_usage >= DAILY_UPLOAD_LIMIT:
        return LeadImportPolicyDecision(
            allowed=False,
            processing_mode='',
            reason_code='daily_limit_reached',
            reason_message='Voce so pode fazer upload 1x por dia para este tipo de importacao.',
            detected_lead_count=detected_lead_count,
            daily_usage=daily_usage,
            monthly_usage=monthly_usage,
        )

    if monthly_usage >= MONTHLY_UPLOAD_LIMIT:
        return LeadImportPolicyDecision(
            allowed=False,
            processing_mode='',
            reason_code='monthly_limit_reached',
            reason_message='Voce atingiu o limite de 3 uploads no mes para este tipo de importacao.',
            detected_lead_count=detected_lead_count,
            daily_usage=daily_usage,
            monthly_usage=monthly_usage,
        )

    processing_mode = decide_lead_import_processing_mode(detected_lead_count=detected_lead_count)
    if not processing_mode:
        return LeadImportPolicyDecision(
            allowed=False,
            processing_mode='',
            reason_code='lead_limit_exceeded',
            reason_message='Este arquivo excede o limite de 2000 leads para importacao.',
            detected_lead_count=detected_lead_count,
            daily_usage=daily_usage,
            monthly_usage=monthly_usage,
        )

    return LeadImportPolicyDecision(
        allowed=True,
        processing_mode=processing_mode,
        reason_code='accepted',
        reason_message='',
        detected_lead_count=detected_lead_count,
        daily_usage=daily_usage,
        monthly_usage=monthly_usage,
    )


__all__ = [
    'DAILY_UPLOAD_LIMIT',
    'LeadImportPolicyDecision',
    'MAX_BACKGROUND_LEADS',
    'MAX_NIGHT_LEADS',
    'MAX_SYNC_LEADS',
    'MONTHLY_UPLOAD_LIMIT',
    'count_daily_import_usage',
    'count_monthly_import_usage',
    'decide_lead_import_processing_mode',
    'evaluate_lead_import_policy',
]
