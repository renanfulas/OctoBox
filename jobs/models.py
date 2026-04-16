from django.db import models
from django.utils import timezone

from model_support.base import TimeStampedModel


class JobStatus(models.TextChoices):
    PENDING = 'pending', 'Pendente'
    RUNNING = 'running', 'Em execucao'
    COMPLETED = 'completed', 'Concluido'
    FAILED = 'failed', 'Falha'


class AsyncJob(TimeStampedModel):
    """
    EPIC 13 (Enterprise Scale): rastreamento de tarefas assincronas.
    """

    job_type = models.CharField(max_length=64, blank=True, default='', db_index=True)
    created_by_id = models.IntegerField(null=True, blank=True, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=JobStatus.choices,
        default=JobStatus.PENDING,
        db_index=True,
    )
    attempts = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    last_failure_kind = models.CharField(max_length=32, blank=True, default='')
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'boxcore'
        ordering = ['-created_at']

    def start(self):
        if self.status == JobStatus.RUNNING:
            return False

        self.status = JobStatus.RUNNING
        self.next_retry_at = None
        self.started_at = timezone.now()
        self.save()
        return True

    def finish(self, result=None):
        self.status = JobStatus.COMPLETED
        self.result = result
        self.next_retry_at = None
        self.last_failure_kind = ''
        self.finished_at = timezone.now()
        self.save()

    def schedule_retry(self, *, result=None, next_retry_at=None, attempt_number=None, failure_kind=''):
        self.status = JobStatus.PENDING
        self.result = result
        self.error = ''
        self.next_retry_at = next_retry_at
        self.last_failure_kind = failure_kind
        if attempt_number is not None:
            self.attempts = attempt_number
        self.finished_at = None
        self.save()

    def mark_retry_dispatched(self, *, result=None):
        self.result = result
        self.next_retry_at = None
        self.save(update_fields=['result', 'next_retry_at'])

    def fail(self, error=None, *, result=None, failure_kind=''):
        self.status = JobStatus.FAILED
        self.result = result
        self.error = str(error)
        self.next_retry_at = None
        self.last_failure_kind = failure_kind
        self.finished_at = timezone.now()
        self.save()


__all__ = ['AsyncJob', 'JobStatus']
