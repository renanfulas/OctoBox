from django.db import models
from django.utils import timezone
from model_support.base import TimeStampedModel

class JobStatus(models.TextChoices):
    PENDING = 'pending', 'Pendente'
    RUNNING = 'running', 'Em execução'
    COMPLETED = 'completed', 'Concluido'
    FAILED = 'failed', 'Falha'

class AsyncJob(TimeStampedModel):
    """
    EPIC 13 (Enterprise Scale): Rastreamento de tarefas assíncronas.
    """
    status = models.CharField(
        max_length=16,
        choices=JobStatus.choices,
        default=JobStatus.PENDING,
        db_index=True
    )
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'boxcore' # Mantemos boxcore para não quebrar o schema legado
        ordering = ['-created_at']

    def start(self):
        # 🛡️ Segurança de Elite (Fintech Hardening): Idempotency Guard
        # Evita que um Job já rodando seja reiniciado por engano ou ataque.
        if self.status == JobStatus.RUNNING:
             return False
             
        self.status = JobStatus.RUNNING
        self.started_at = timezone.now()
        self.save()
        return True

    def finish(self, result=None):
        self.status = JobStatus.COMPLETED
        self.result = result
        self.finished_at = timezone.now()
        self.save()

    def fail(self, error=None):
        self.status = JobStatus.FAILED
        self.error = str(error)
        self.finished_at = timezone.now()
        self.save()
