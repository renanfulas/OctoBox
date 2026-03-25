from django.db import models


class ImportJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("done", "Done"),
        ("failed", "Failed"),
    ]

    file = models.FileField(upload_to="imports/")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    total_rows = models.IntegerField(null=True, blank=True)
    processed_rows = models.IntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ImportJob({self.pk}) status={self.status} rows={self.total_rows}\n"
