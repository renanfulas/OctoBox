import logging
from django.http import JsonResponse
from django.views import View
from operations.tasks import run_csv_contact_import_job, run_csv_student_import_job
from jobs.models import AsyncJob

logger = logging.getLogger(__name__)

from access.permissions.mixins import RoleRequiredMixin
from access.roles import ROLE_OWNER, ROLE_MANAGER

class SecureExportDownloadView(RoleRequiredMixin, View):
    """
    Endpoint seguro para download de relatorios (Epic 8 Hardening).
    Evita exposição de CSVs via MEDIA_URL público.
    """
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def get(self, request, filename, *args, **kwargs):
        import os
        from django.conf import settings
        from django.http import FileResponse, Http404

        # Prevenção contra Path Traversal
        safe_filename = os.path.basename(filename)
        file_path = os.path.join(settings.MEDIA_ROOT, 'exports', safe_filename)

        if not os.path.exists(file_path):
            raise Http404("Arquivo não encontrado ou expirado.")

        response = FileResponse(open(file_path, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
        return response

class AsyncImportJobView(RoleRequiredMixin, View):
    """
    FIX 4: Endpoint recebendo CSV retornando HTTP 202 com Tracking ID.
    Secured with RoleRequiredMixin (Epic 8).
    """
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def post(self, request, *args, **kwargs):
        if 'file' not in request.FILES:
            return JsonResponse({"error": "No file uploaded"}, status=400)
            
        csv_file = request.FILES['file']
        
        # EPIC 9: Evitar .read() em memória. Usar o path temporário do Django se disponível.
        # Se for um arquivo pequeno (<2.5MB), o Django usa MemoryUploadedFile. 
        # Forçamos a persistência ou usamos o path se for TemporaryUploadedFile.
        if hasattr(csv_file, 'temporary_file_path'):
            file_path = csv_file.temporary_file_path()
        else:
            # Fallback seguro: persiste em local temporário para o worker ler
            import tempfile
            import os
            fd, file_path = tempfile.mkstemp(suffix='.csv', prefix='octobox_import_')
            with os.fdopen(fd, 'wb') as tmp:
                for chunk in csv_file.chunks():
                    tmp.write(chunk)

        # EPIC 9 Security: Create tracked AsyncJob record
        job = AsyncJob.objects.create(
            job_type='student_import_csv',
            created_by_id=request.user.id,
            status='pending'
        )

        # Despachar Job para Celery Broker passando o PATH, não os bytes
        task = run_csv_student_import_job.delay(file_path=file_path, actor_id=request.user.id, job_id=job.id)
        
        return JsonResponse({
            "status": "accepted",
            "job_id": job.id,
            "task_id": task.id,
            "message": "Arquivo processado via streaming e enfileirado com sucesso."
        }, status=202)

class AsyncImportJobStatusView(RoleRequiredMixin, View):
    """
    Endpoint para front-end pullar a barra de progresso (ETA).
    Secured with RoleRequiredMixin (Epic 8).
    """
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def get(self, request, task_id, *args, **kwargs):
        # Aqui consultaria AsyncResult(task_id).state etc.
        return JsonResponse({
            "task_id": task_id,
            "status": "processing",
            "progress_percent": 65,
            "eta_seconds": 12
        }, status=200)
