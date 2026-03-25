from celery import shared_task
from auditing.models import AuditEvent
import logging

logger = logging.getLogger(__name__)

@shared_task
def async_log_audit_event(data):
    """
    Processa a escrita de auditoria no background.
    """
    try:
        AuditEvent.objects.create(**data)
    except Exception as e:
        logger.error(f"Failed to log async audit event: {str(e)}")
