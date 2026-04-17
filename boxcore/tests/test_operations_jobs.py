"""
ARQUIVO: testes do ciclo de execucao dos jobs de importacao de leads.

POR QUE ELE EXISTE:
- protege a persistencia de relatorio quando o processamento sai da view e entra no corredor assincrono.

O QUE ESTE ARQUIVO FAZ:
1. valida a execucao de um job `async_now`.
2. valida o despacho e processamento de um job `async_night`.
3. garante que duplicatas e erros estruturados ficam gravados no `LeadImportJob`.

PONTOS CRITICOS:
- se estes testes quebrarem, o owner pode perder visibilidade justamente nos arquivos maiores.
"""

import os

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from onboarding.models import StudentIntake
from operations.models import (
    LeadImportDeclaredRange,
    LeadImportJob,
    LeadImportJobStatus,
    LeadImportProcessingMode,
    LeadImportSourceType,
)
from operations.services.lead_import_orchestrator import orchestrate_lead_import_submission
from operations.tasks import dispatch_nightly_lead_import_jobs as dispatch_nightly_lead_import_jobs_task
from operations.tasks import run_lead_import_job as run_lead_import_job_task


class LeadImportJobExecutionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='owner-job-runner',
            email='owner-job-runner@example.com',
            password='senha-forte-123',
        )
        self.created_files = []

    def tearDown(self):
        for file_path in self.created_files:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)

    def _build_csv_upload(self, *, lead_count: int, duplicate_first_phone=False) -> SimpleUploadedFile:
        rows = []
        for index in range(1, lead_count + 1):
            if index == 1 and duplicate_first_phone:
                phone = '(11) 99888-7766'
            else:
                phone = f'(11) 96{index:03d}-{index:04d}'
            rows.append(f'Aluno {index},{phone},lead{index}@example.com')
        content = 'Nome,Telefone,Email\n' + '\n'.join(rows) + '\n'
        return SimpleUploadedFile(
            'leads_async.csv',
            content.encode('utf-8'),
            content_type='text/csv',
        )

    def test_run_lead_import_job_persists_report_for_async_now(self):
        StudentIntake.objects.create(
            full_name='Lead Existente',
            phone='5511998887766',
            email='existente@example.com',
        )
        orchestration = orchestrate_lead_import_submission(
            file_obj=self._build_csv_upload(lead_count=220, duplicate_first_phone=True),
            source_type=LeadImportSourceType.TECNOFIT_EXPORT,
            declared_range=LeadImportDeclaredRange.FROM_201_TO_500,
            actor=self.user,
            today=timezone.localdate(),
        )
        self.created_files.append(orchestration.job.file_path)

        result = run_lead_import_job_task(orchestration.job.id)
        orchestration.job.refresh_from_db()

        self.assertEqual(result['status'], LeadImportJobStatus.COMPLETED_WITH_WARNINGS)
        self.assertEqual(orchestration.job.processing_mode, LeadImportProcessingMode.ASYNC_NOW)
        self.assertEqual(orchestration.job.status, LeadImportJobStatus.COMPLETED_WITH_WARNINGS)
        self.assertEqual(orchestration.job.duplicate_count, 1)
        self.assertEqual(orchestration.job.duplicate_details[0]['reason'], 'duplicate_in_database_phone')
        self.assertEqual(orchestration.job.success_count, 219)
        self.assertFalse(os.path.exists(orchestration.job.file_path))

    def test_dispatch_due_nightly_lead_import_jobs_processes_scheduled_job(self):
        StudentIntake.objects.create(
            full_name='Lead Existente Noite',
            phone='5511998887766',
            email='existente-noite@example.com',
        )
        orchestration = orchestrate_lead_import_submission(
            file_obj=self._build_csv_upload(lead_count=520, duplicate_first_phone=True),
            source_type=LeadImportSourceType.NEXTFIT_EXPORT,
            declared_range=LeadImportDeclaredRange.FROM_501_TO_2000,
            actor=self.user,
            today=timezone.localdate(),
        )
        self.created_files.append(orchestration.job.file_path)
        orchestration.job.refresh_from_db()
        self.assertEqual(orchestration.job.status, LeadImportJobStatus.SCHEDULED)
        self.assertIsNotNone(orchestration.job.scheduled_for)

        LeadImportJob.objects.filter(pk=orchestration.job.pk).update(
            scheduled_for=timezone.now() - timezone.timedelta(minutes=5)
        )

        dispatch_report = dispatch_nightly_lead_import_jobs_task(limit=10)
        orchestration.job.refresh_from_db()

        self.assertEqual(dispatch_report['dispatched_count'], 1)
        self.assertEqual(dispatch_report['processed_job_ids'], [orchestration.job.id])
        self.assertEqual(orchestration.job.processing_mode, LeadImportProcessingMode.ASYNC_NIGHT)
        self.assertEqual(orchestration.job.status, LeadImportJobStatus.COMPLETED_WITH_WARNINGS)
        self.assertEqual(orchestration.job.duplicate_count, 1)
        self.assertEqual(orchestration.job.duplicate_details[0]['reason'], 'duplicate_in_database_phone')
        self.assertFalse(os.path.exists(orchestration.job.file_path))
