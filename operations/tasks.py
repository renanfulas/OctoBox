try:
    from celery import shared_task
except ImportError:
    # Fallback para ambientes sem Celery (Epic 7 Resilience)
    def shared_task(*args, **kwargs):
        def decorator(func):
            def wrapper(*wargs, **wkwargs):
                return func(*wargs, **wkwargs)
            wrapper.delay = func # Mock delay para não quebrar chamadas .delay()
            return wrapper
        return decorator
from operations.services.contact_importer import import_contacts_from_stream
from operations.services.student_importer import StudentImporter
from operations.models import AsyncJob
import io
import logging

logger = logging.getLogger('octobox.jobs')

@shared_task(bind=True)
def run_csv_contact_import_job(self, file_path, actor_id=None, job_id=None):
    """
    FIX 4 (Performance): Async Native Jobs with streaming file access.
    """
    import os
    job = None
    if job_id:
        job = AsyncJob.objects.filter(pk=job_id).first()
    
    if job:
        job.start()

    try:
        # EPIC 9: Abrir arquivo em modo stream diretamente do disco
        with open(file_path, 'rb') as stream:
            report = import_contacts_from_stream(stream, source_platform='tecnofit', actor=actor_id)
        
        # Limpeza opcional se for arquivo temporário gerado pelo OctoBox
        if 'octobox_import_' in file_path:
            os.remove(file_path)

        if job:
            job.finish(result=report)
        
        return {
            "status": "completed",
            "report": report
        }
    except Exception as e:
        logger.error(f"Falha no Job {job_id}: {str(e)}", exc_info=True)
        if job:
            job.fail(error=e)
        raise e

@shared_task(bind=True)
def run_csv_student_import_job(self, file_path, actor_id=None, job_id=None):
    """
    EPIC 9: Async Student Import with Bulk Operations
    """
    import os
    job = None
    if job_id:
        job = AsyncJob.objects.filter(pk=job_id).first()
    
    if job:
        job.start()

    try:
        importer = StudentImporter()
        report = importer.import_from_file(file_path)
        
        if 'octobox_import_' in file_path:
            os.remove(file_path)

        if job:
            job.finish(result=report)
        
        return {"status": "completed", "report": report}
    except Exception as e:
        logger.error(f"Student Import Job Failed {job_id}: {str(e)}", exc_info=True)
        if job:
            job.fail(error=e)
        raise e
