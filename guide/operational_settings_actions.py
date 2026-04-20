"""
Corredor de ações operacionais da tela de configuracoes.
"""

from django.contrib import messages
from django.utils import timezone

from operations.models import LeadImportJobStatus, LeadImportProcessingMode
from operations.services.contact_importer import import_contacts_from_stream
from operations.services.lead_import_orchestrator import orchestrate_lead_import_submission
from operations.tasks import run_lead_import_job
from shared_support.operational_settings import set_operational_whatsapp_repeat_block_hours


def apply_sync_import_job(*, job, source_platform):
    with open(job.file_path, "rb") as stream:
        report = import_contacts_from_stream(
            stream,
            source_platform=source_platform,
            actor=job.created_by,
        )

    job.success_count = report["success"]
    job.duplicate_count = report["duplicates"]
    job.error_count = report["errors"]
    job.duplicate_details = report.get("duplicate_details", [])
    job.error_details = report.get(
        "error_details",
        [{"reason_message": detail} for detail in report.get("details", [])],
    )
    job.status = (
        LeadImportJobStatus.COMPLETED_WITH_WARNINGS
        if report["duplicates"] > 0 or report["errors"] > 0
        else LeadImportJobStatus.COMPLETED
    )
    job.finished_at = timezone.now()
    job.save(
        update_fields=[
            "success_count",
            "duplicate_count",
            "error_count",
            "duplicate_details",
            "error_details",
            "status",
            "finished_at",
            "updated_at",
        ]
    )
    return report


def emit_sync_import_messages(*, request, report):
    if report["success"] > 0:
        messages.success(request, f"{report['success']} contatos importados com sucesso.")
    if report["duplicates"] > 0:
        messages.warning(request, f"{report['duplicates']} contatos ja existiam no banco e foram ignorados.")
    if report["errors"] > 0:
        error_list = report["details"][:3]
        error_msg = f"Houve {report['errors']} erros de processamento: " + "; ".join(error_list)
        if len(report["details"]) > 3:
            error_msg += f" (...mais {len(report['details']) - 3} falhas)"
        messages.error(request, error_msg)
    if report["success"] == 0 and report["duplicates"] == 0 and report["errors"] == 0:
        messages.info(request, "Nenhum contato encontrado para processar no arquivo.")


def dispatch_async_now_import(*, job):
    run_lead_import_job.delay(job.id)


def handle_operational_settings_import_submission(
    *,
    request,
    file_obj,
    source_platform,
    source_type,
    declared_range,
    dispatch_async_now_import_fn=None,
):
    orchestration = orchestrate_lead_import_submission(
        file_obj=file_obj,
        source_type=source_type,
        declared_range=declared_range,
        actor=request.user,
    )

    if not orchestration.policy_decision.allowed:
        messages.error(request, orchestration.policy_decision.reason_message)
        return

    if orchestration.job.processing_mode == LeadImportProcessingMode.SYNC:
        report = apply_sync_import_job(
            job=orchestration.job,
            source_platform=source_platform,
        )
        emit_sync_import_messages(request=request, report=report)
    elif orchestration.job.processing_mode == LeadImportProcessingMode.ASYNC_NOW:
        if dispatch_async_now_import_fn is not None:
            dispatch_async_now_import_fn(orchestration.job)
        else:
            dispatch_async_now_import(job=orchestration.job)
        messages.info(
            request,
            "Sua importacao foi enviada para processamento em background. Voce pode continuar navegando normalmente.",
        )
    elif orchestration.job.processing_mode == LeadImportProcessingMode.ASYNC_NIGHT:
        messages.info(
            request,
            "Sua importacao foi agendada para processamento economico noturno.",
        )


def handle_operational_settings_repeat_window_update(*, request, raw_value):
    try:
        set_operational_whatsapp_repeat_block_hours(hours=raw_value, actor=request.user)
    except ValueError:
        messages.error(request, "Escolha apenas 24h, 12h ou 0h para a janela do WhatsApp.")
    else:
        messages.success(request, "Janela de bloqueio do WhatsApp atualizada com sucesso.")
