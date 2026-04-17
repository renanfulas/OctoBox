"""
ARQUIVO: testes do orquestrador de importacao de leads.

POR QUE ELE EXISTE:
- protege o contrato que une inspecao, policy e criacao do job antes da view HTTP.

O QUE ESTE ARQUIVO FAZ:
1. valida a criacao de job para trilho sync.
2. valida a criacao de job para background imediato.
3. valida a criacao de job para agendamento noturno.
4. valida rejeicao sem persistencia de arquivo temporario.

PONTOS CRITICOS:
- se estes testes quebrarem, a view pode criar jobs com status errado ou deixar lixo no disco.
"""

import os

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from operations.models import (
    LeadImportDeclaredRange,
    LeadImportJobStatus,
    LeadImportProcessingMode,
    LeadImportSourceType,
)
from operations.services.lead_import_orchestrator import orchestrate_lead_import_submission


class LeadImportOrchestratorTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='owner-orchestrator',
            email='owner-orchestrator@example.com',
            password='senha-forte-123',
        )
        self.created_files = []

    def tearDown(self):
        for file_path in self.created_files:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)

    def _build_upload(self, *, lead_count: int) -> SimpleUploadedFile:
        rows = [
            f'Aluno {index},(11) 96000-{index:04d},lead{index}@example.com'
            for index in range(1, lead_count + 1)
        ]
        content = 'Nome,Telefone,Email\n' + '\n'.join(rows) + '\n'
        return SimpleUploadedFile(
            'leads.csv',
            content.encode('utf-8'),
            content_type='text/csv',
        )

    def test_orchestrator_creates_queued_sync_job_for_up_to_200_leads(self):
        result = orchestrate_lead_import_submission(
            file_obj=self._build_upload(lead_count=200),
            source_type=LeadImportSourceType.WHATSAPP_LIST,
            declared_range=LeadImportDeclaredRange.UP_TO_200,
            actor=self.user,
            today=timezone.localdate(),
        )
        self.created_files.append(result.job.file_path)

        self.assertTrue(result.policy_decision.allowed)
        self.assertEqual(result.job.processing_mode, LeadImportProcessingMode.SYNC)
        self.assertEqual(result.job.status, LeadImportJobStatus.QUEUED)
        self.assertEqual(result.job.detected_lead_count, 200)
        self.assertTrue(result.temp_file_created)
        self.assertTrue(os.path.exists(result.job.file_path))

    def test_orchestrator_creates_queued_background_job_for_201_to_500_leads(self):
        result = orchestrate_lead_import_submission(
            file_obj=self._build_upload(lead_count=320),
            source_type=LeadImportSourceType.TECNOFIT_EXPORT,
            declared_range=LeadImportDeclaredRange.FROM_201_TO_500,
            actor=self.user,
            today=timezone.localdate(),
        )
        self.created_files.append(result.job.file_path)

        self.assertTrue(result.policy_decision.allowed)
        self.assertEqual(result.job.processing_mode, LeadImportProcessingMode.ASYNC_NOW)
        self.assertEqual(result.job.status, LeadImportJobStatus.QUEUED)
        self.assertEqual(result.job.detected_lead_count, 320)
        self.assertTrue(result.temp_file_created)

    def test_orchestrator_creates_scheduled_night_job_for_501_to_2000_leads(self):
        result = orchestrate_lead_import_submission(
            file_obj=self._build_upload(lead_count=1200),
            source_type=LeadImportSourceType.NEXTFIT_EXPORT,
            declared_range=LeadImportDeclaredRange.FROM_501_TO_2000,
            actor=self.user,
            today=timezone.localdate(),
        )
        self.created_files.append(result.job.file_path)

        self.assertTrue(result.policy_decision.allowed)
        self.assertEqual(result.job.processing_mode, LeadImportProcessingMode.ASYNC_NIGHT)
        self.assertEqual(result.job.status, LeadImportJobStatus.SCHEDULED)
        self.assertEqual(result.job.detected_lead_count, 1200)
        self.assertTrue(result.temp_file_created)

    def test_orchestrator_rejects_file_above_limit_without_persisting_temp_file(self):
        result = orchestrate_lead_import_submission(
            file_obj=self._build_upload(lead_count=2100),
            source_type=LeadImportSourceType.WHATSAPP_LIST,
            declared_range=LeadImportDeclaredRange.FROM_501_TO_2000,
            actor=self.user,
            today=timezone.localdate(),
        )

        self.assertFalse(result.policy_decision.allowed)
        self.assertEqual(result.job.status, LeadImportJobStatus.REJECTED)
        self.assertEqual(result.job.processing_mode, LeadImportProcessingMode.SYNC)
        self.assertEqual(result.job.file_path, '')
        self.assertFalse(result.temp_file_created)
        self.assertEqual(result.job.error_details[0]['reason_code'], 'lead_limit_exceeded')
