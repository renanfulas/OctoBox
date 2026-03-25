from django.shortcuts import get_object_or_404
from django.http import JsonResponse

from .models import ImportJob

import threading
import csv
import io
try:
    # tenta usar Celery task se disponível
    from .tasks import process_import_job_task as celery_process_task
except Exception:
    celery_process_task = None


def upload_import(request):
    """Recebe upload de CSV, cria ImportJob e dispara processamento em background.

    Uso (POST multipart/form-data): campo `file` com CSV.
    Retorna: { "job_id": <id> } com status 202.
    """
    if request.method != "POST":
        return JsonResponse({"detail": "method not allowed"}, status=405)

    f = request.FILES.get("file")
    if not f:
        return JsonResponse({"detail": "file is required"}, status=400)

    job = ImportJob.objects.create(file=f, status="pending")

    # Se Celery estiver configurado, enfileira a task; senão usa thread local para demo
    if celery_process_task:
        celery_process_task.delay(job.id)
    else:
        threading.Thread(target=process_import_job, args=(job.id,), daemon=True).start()

    return JsonResponse({"job_id": job.id}, status=202)


def job_status(request, job_id):
    job = get_object_or_404(ImportJob, pk=job_id)
    data = {
        "id": job.id,
        "status": job.status,
        "total_rows": job.total_rows,
        "processed_rows": job.processed_rows,
        "errors": job.errors,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }
    return JsonResponse(data)


def process_import_job(job_id):
    """Processamento simples: lê CSV, valida e atualiza contadores no modelo.

    Observação: esta função é didática — em produção use tasks assíncronas e evite salvar a cada linha.
    """
    from .models import ImportJob
    import time

    job = ImportJob.objects.get(pk=job_id)
    job.status = "processing"
    job.save()
    try:
        raw = job.file.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")

        stream = io.StringIO(raw)
        reader = csv.DictReader(stream)
        rows = list(reader)

        job.total_rows = len(rows)
        job.processed_rows = 0
        job.errors = []
        job.save()

        for i, row in enumerate(rows, start=1):
            # Simula trabalho e validação simples
            time.sleep(0.03)
            if "email" in row and row.get("email") and "@" not in row.get("email"):
                job.errors.append({"row": i, "error": "email inválido"})

            job.processed_rows = i
            job.save()

        job.status = "done"
        job.save()
    except Exception as e:
        job.status = "failed"
        # preserva erros anteriores se existirem
        job.errors = (job.errors or []) + [{"error": str(e)}]
        job.save()
