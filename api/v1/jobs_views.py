import logging
import os
import tempfile

from django.http import JsonResponse
from django.views import View

from access.permissions.mixins import RoleRequiredMixin
from access.roles import ROLE_MANAGER, ROLE_OWNER
from integrations.mesh import build_correlation_id, build_signal_envelope, resolve_idempotency_key
from jobs.dispatcher import build_dispatch_context, dispatch_async_job
from jobs.models import AsyncJob
from monitoring.alert_siren import get_alert_siren_defense_policy

logger = logging.getLogger(__name__)


def _build_request_correlation_id(request) -> str:
    return build_correlation_id(
        request.headers.get('X-Correlation-ID') or request.headers.get('X-Request-ID') or ''
    )


def _persist_upload_to_tempfile(uploaded_file) -> str:
    if hasattr(uploaded_file, 'temporary_file_path'):
        return uploaded_file.temporary_file_path()

    fd, file_path = tempfile.mkstemp(suffix='.csv', prefix='octobox_import_')
    with os.fdopen(fd, 'wb') as tmp:
        for chunk in uploaded_file.chunks():
            tmp.write(chunk)
    return file_path


class SecureExportDownloadView(RoleRequiredMixin, View):
    """
    Endpoint seguro para download de relatorios.
    """

    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def get(self, request, filename, *args, **kwargs):
        from django.conf import settings
        from django.http import FileResponse, Http404

        safe_filename = os.path.basename(filename)
        file_path = os.path.join(settings.MEDIA_ROOT, 'exports', safe_filename)

        if not os.path.exists(file_path):
            raise Http404('Arquivo nao encontrado ou expirado.')

        response = FileResponse(open(file_path, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
        return response


class AsyncImportJobView(RoleRequiredMixin, View):
    """
    Endpoint recebendo CSV e retornando HTTP 202 com tracking id.
    """

    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def post(self, request, *args, **kwargs):
        correlation_id = _build_request_correlation_id(request)
        defense_policy = get_alert_siren_defense_policy()
        if defense_policy.get('pause_non_essential_job_submissions'):
            response = JsonResponse(
                {
                    'error': 'alert_siren_containment',
                    'message': 'Imports assincronos foram temporariamente contidos para proteger a operacao.',
                    'correlation_id': correlation_id,
                    'alert_siren_level': defense_policy.get('level', ''),
                },
                status=503,
            )
            response['X-OctoBox-Correlation-Id'] = correlation_id
            return response

        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file uploaded'}, status=400)

        csv_file = request.FILES['file']
        file_path = _persist_upload_to_tempfile(csv_file)
        envelope = build_signal_envelope(
            correlation_id=correlation_id,
            idempotency_key=resolve_idempotency_key(
                explicit_key=request.headers.get('X-Idempotency-Key', ''),
            ),
            source_channel='api.v1.jobs',
            raw_reference=f'upload:{getattr(csv_file, "name", "")}',
        )
        dispatch_context = build_dispatch_context(
            job_type='student_import_csv',
            file_path=file_path,
            actor_id=request.user.id,
            signal_envelope=envelope.to_metadata(),
        )

        job = AsyncJob.objects.create(
            job_type='student_import_csv',
            created_by_id=request.user.id,
            status='pending',
            result={
                'signal_envelope': envelope.to_metadata(),
                'dispatch_context': dispatch_context,
            },
        )

        task = dispatch_async_job(job=job, dispatch_context=dispatch_context)

        response = JsonResponse(
            {
                'status': 'accepted',
                'job_id': job.id,
                'task_id': task.id,
                'correlation_id': correlation_id,
                'message': 'Arquivo processado via streaming e enfileirado com sucesso.',
            },
            status=202,
        )
        response['X-OctoBox-Correlation-Id'] = correlation_id
        return response


class AsyncImportJobStatusView(RoleRequiredMixin, View):
    """
    Endpoint para front-end consultar status do job.
    """

    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def get(self, request, task_id, *args, **kwargs):
        correlation_id = _build_request_correlation_id(request)
        job = AsyncJob.objects.filter(pk=task_id).first()
        if job is None:
            response = JsonResponse(
                {
                    'error': 'job_not_found',
                    'correlation_id': correlation_id,
                },
                status=404,
            )
            response['X-OctoBox-Correlation-Id'] = correlation_id
            return response

        result = job.result or {}
        response = JsonResponse(
            {
                'job_id': job.id,
                'task_id': str(task_id),
                'job_type': job.job_type,
                'status': job.status,
                'attempts': job.attempts,
                'max_retries': job.max_retries,
                'next_retry_at': job.next_retry_at.isoformat() if job.next_retry_at else '',
                'last_failure_kind': job.last_failure_kind,
                'result': result,
                'error': job.error,
                'correlation_id': correlation_id,
            },
            status=200,
        )
        response['X-OctoBox-Correlation-Id'] = correlation_id
        return response
