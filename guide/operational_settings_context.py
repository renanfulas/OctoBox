"""
Corredor de leitura/contexto da tela de configuracoes operacionais.
"""

from django.utils import timezone

from operations.models import LeadImportJob


def build_latest_lead_import_status(*, request, status_ttl_hours, status_ui):
    status_cutoff = timezone.now() - timezone.timedelta(hours=status_ttl_hours)
    latest_job = (
        LeadImportJob.objects.filter(
            created_by=request.user,
            created_at__gte=status_cutoff,
        )
        .order_by("-created_at")
        .first()
    )
    if latest_job is None:
        return None

    status_meta = status_ui.get(
        latest_job.status,
        {
            "title": "Status da importacao de leads",
            "summary": "Existe uma lista recente no pipeline operacional.",
            "tone": "info",
        },
    )
    return {
        "title": status_meta["title"],
        "summary": status_meta["summary"],
        "tone": status_meta["tone"],
        "job_id": latest_job.id,
        "source_type_label": latest_job.get_source_type_display(),
        "status_label": latest_job.get_status_display(),
        "processing_mode_label": latest_job.get_processing_mode_display(),
        "original_filename": latest_job.original_filename,
        "detected_lead_count": latest_job.detected_lead_count,
        "success_count": latest_job.success_count,
        "duplicate_count": latest_job.duplicate_count,
        "error_count": latest_job.error_count,
        "created_at": timezone.localtime(latest_job.created_at).strftime("%d/%m/%Y %H:%M"),
        "finished_at": (
            timezone.localtime(latest_job.finished_at).strftime("%d/%m/%Y %H:%M")
            if latest_job.finished_at
            else ""
        ),
    }
