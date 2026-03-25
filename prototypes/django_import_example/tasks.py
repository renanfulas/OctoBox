from celery import shared_task


@shared_task(bind=True)
def process_import_job_task(self, job_id):
    """Celery task para processar ImportJob criado no app de exemplo.

    A task replica a lógica de `process_import_job` em views.py mas evitando salvar
    o modelo a cada linha (faz saves em batches) para reduzir I/O.
    """
    from .models import ImportJob
    import csv
    import io
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

        batch_interval = 20
        for i, row in enumerate(rows, start=1):
            # Simula validação/processing
            time.sleep(0.01)
            if "email" in row and row.get("email") and "@" not in row.get("email"):
                job.errors.append({"row": i, "error": "email inválido"})

            job.processed_rows = i
            # salva a cada batch_interval para reduzir writes
            if i % batch_interval == 0:
                job.save()

        job.status = "done"
        job.save()
    except Exception as e:
        job.status = "failed"
        job.errors = (job.errors or []) + [{"error": str(e)}]
        job.save()

    return {"job_id": job_id, "status": job.status}
