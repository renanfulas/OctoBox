import csv
import logging
import os
from django.apps import apps
from django.conf import settings
from django.utils import timezone

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

from catalog.student_queries import build_student_directory_snapshot
from reporting.application.catalog_reports import build_student_directory_report

logger = logging.getLogger('octobox.reporting.tasks')

@shared_task(bind=True)
def run_student_directory_export_task(self, query_params, report_format, actor_id=None, job_id=None):
    """
    EPIC 13 (Enterprise Scale): Motor de exportação assíncrona para 1M+ registros.
    """
    from django.http import QueryDict
    AsyncJob = apps.get_model('boxcore', 'AsyncJob')
    
    job = None
    if job_id:
        job = AsyncJob.objects.filter(pk=job_id).first()
    
    if job:
        job.start()

    try:
        # Reconstroi o snapshot com os mesmos filtros da request original
        # Suporta tanto dict quanto urlencoded string
        params = query_params
        if isinstance(query_params, str):
            params = QueryDict(query_params)
            
        snapshot = build_student_directory_snapshot(params)
        students = snapshot['students']
        
        # Gera o payload do relatório (usando generators/iterators internamente)
        report_payload = build_student_directory_report(students=students, report_format=report_format)
        
        # Preparar diretório de saída
        export_dir = os.path.join(settings.MEDIA_ROOT, 'exports')
        os.makedirs(export_dir, exist_ok=True)
        
        # Nome único para o arquivo
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = report_payload['filename'].replace('.csv', '').replace('.pdf', '')
        filename = f"{safe_filename}_{timestamp}.{report_format}"
        file_path = os.path.join(export_dir, filename)
        
        if report_format == 'csv':
            # Escrita eficiente via streaming
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(report_payload['headers'])
                for row in report_payload['rows']:
                    writer.writerow(row)
        else:
            # Placeholder para PDF (seria necessário integrar ferramenta de PDF aqui)
            # Para o escopo de performance 1M+, o CSV é o foco principal.
            with open(file_path, 'w') as f:
                f.write("PDF Export not yet implemented for 1M+ background tasks.")

        file_url = f"{settings.MEDIA_URL}exports/{filename}"
        
        if job:
            result = {
                'file_url': file_url,
                'filename': filename,
                'format': report_format,
                'count': students.count() if hasattr(students, 'count') else 0
            }
            job.finish(result=result)
        
        return {"status": "completed", "file_url": file_url}
        
    except Exception as e:
        logger.error(f"Export Job Failed {job_id}: {str(e)}", exc_info=True)
        if job:
            job.fail(error=e)
        raise e

@shared_task(bind=True)
def run_finance_report_export_task(self, query_params, report_format, actor_id=None, job_id=None):
    """
    EPIC 13 (Enterprise Scale): Motor de exportação financeira assíncrona.
    """
    from django.http import QueryDict
    from catalog.finance_queries import build_finance_snapshot
    from reporting.application.catalog_reports import build_finance_report
    
    AsyncJob = apps.get_model('boxcore', 'AsyncJob')
    
    job = None
    if job_id:
        job = AsyncJob.objects.filter(pk=job_id).first()
    
    if job:
        job.start()

    try:
        params = query_params
        if isinstance(query_params, str):
            params = QueryDict(query_params)

        snapshot = build_finance_snapshot(params)
        report_payload = build_finance_report(snapshot=snapshot, report_format=report_format)
        
        export_dir = os.path.join(settings.MEDIA_ROOT, 'exports')
        os.makedirs(export_dir, exist_ok=True)
        
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = report_payload['filename'].replace('.csv', '').replace('.pdf', '')
        filename = f"{safe_filename}_{timestamp}.{report_format}"
        file_path = os.path.join(export_dir, filename)
        
        if report_format == 'csv':
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(report_payload['headers'])
                for row in report_payload['rows']:
                    writer.writerow(row)
        else:
            with open(file_path, 'w') as f:
                f.write("PDF Export not yet implemented for 1M+ background tasks.")

        file_url = f"{settings.MEDIA_URL}exports/{filename}"
        
        if job:
            result = {'file_url': file_url, 'filename': filename, 'format': report_format}
            job.finish(result=result)
        
        return {"status": "completed", "file_url": file_url}
        
    except Exception as e:
        logger.error(f"Finance Export Job Failed {job_id}: {str(e)}", exc_info=True)
        if job:
            job.fail(error=e)
        raise e
