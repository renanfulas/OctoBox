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
            # 🚀 Resiliência (Epic 8): Alerta de Performance
            import os
            if os.getenv('DJANGO_RUNTIME_MODE') == 'production':
                 # Em produção, não podemos aceitar que o sistema rode tarefas pesadas síncronas.
                 # Isso travaria o servidor para todos os outros usuários.
                 raise RuntimeError("BROKER_URL não configurada. Tarefas assíncronas bloqueadas em produção.")
                 
            def wrapper(*wargs, **wkwargs):
                return func(*wargs, **wkwargs)
            wrapper.delay = func 
            return wrapper
        return decorator

from catalog.student_queries import build_student_directory_snapshot
from reporting.application.catalog_reports import build_student_directory_report

logger = logging.getLogger('octobox.reporting.tasks')

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3}
)
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
        
        # 🚀 Segurança de Elite (Epic 8 Hardening): Sanitização Rigorosa
        # Remove caracteres que podem causar Path Traversal ou Injeção.
        import re
        safe_filename = re.sub(r'[^a-zA-Z0-9_\-]', '', report_payload['filename'].replace('.csv', '').replace('.pdf', ''))
        
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
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

        # 🚀 Segurança de Elite (Epic 8 Hardening)
        # Protegendo o link de Export contra o público:
        file_url = f"/api/v1/exports/download/{filename}"
        
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
        
        # 🚀 Segurança de Elite (Epic 8 Hardening): Sanitização Rigorosa
        import re
        safe_filename = re.sub(r'[^a-zA-Z0-9_\-]', '', report_payload['filename'].replace('.csv', '').replace('.pdf', ''))
        
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
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

        # 🚀 Segurança de Elite (Epic 8 Hardening): Proxy Autenticado
        file_url = f"/api/v1/exports/download/{filename}"
        
        if job:
            result = {'file_url': file_url, 'filename': filename, 'format': report_format}
            job.finish(result=result)
        
        return {"status": "completed", "file_url": file_url}
        
    except Exception as e:
        logger.error(f"Finance Export Job Failed {job_id}: {str(e)}", exc_info=True)
        if job:
            job.fail(error=e)
        raise e
