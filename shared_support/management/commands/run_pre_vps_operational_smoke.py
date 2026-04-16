"""
ARQUIVO: smoke test operacional curto para pre-VPS.

POR QUE ELE EXISTE:
- valida os corredores criticos antes de subir para servidor real.
- transforma a revisao manual de dashboard, AsyncJob, Beacon e sweeps em passo executavel.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from dashboard.dashboard_snapshot_queries import build_dashboard_snapshot
from jobs.models import AsyncJob, JobStatus
from jobs.reprocessing import reprocess_due_async_jobs
from integrations.whatsapp.reprocessing import reprocess_due_webhook_events
from monitoring.beacon_snapshot import build_red_beacon_snapshot


class Command(BaseCommand):
    help = 'Executa smoke test curto de dashboard, AsyncJob, Beacon e sweeps antes do VPS.'

    def handle(self, *args, **options):
        today = timezone.localdate()
        now = timezone.now()

        dashboard_snapshot = build_dashboard_snapshot(
            today=today,
            month_start=today.replace(day=1),
            role_slug='owner',
        )
        beacon_snapshot = build_red_beacon_snapshot()

        self.stdout.write(
            f"dashboard_red_beacon={dashboard_snapshot['red_beacon_snapshot']['label']}"
        )
        self.stdout.write(
            f"dashboard_alert_siren={dashboard_snapshot['red_beacon_snapshot']['alert_siren']['level']}"
        )
        self.stdout.write(
            f"beacon_signal_mesh_backlog={beacon_snapshot['signal_mesh']['total_due_backlog']}"
        )

        smoke_job = AsyncJob.objects.create(
            job_type='smoke_test',
            created_by_id=None,
            status=JobStatus.PENDING,
            attempts=0,
            max_retries=1,
            result={'smoke': True, 'created_at': now.isoformat()},
        )

        try:
            reloaded_job = AsyncJob.objects.get(pk=smoke_job.pk)
            self.stdout.write(
                f'asyncjob_create_ok id={reloaded_job.id} status={reloaded_job.status} job_type={reloaded_job.job_type}'
            )

            jobs_result = reprocess_due_async_jobs(limit=1)
            webhooks_result = reprocess_due_webhook_events(limit=1)

            self.stdout.write(
                (
                    'smoke_sweeps='
                    f"jobs:{jobs_result['dispatched_count']}/{jobs_result['skipped_count']} "
                    f"webhooks:{webhooks_result['processed_count']}/{webhooks_result['skipped_count']}"
                )
            )
        finally:
            smoke_job.delete()

        self.stdout.write(self.style.SUCCESS('Pre-VPS smoke test operacional concluido.'))
