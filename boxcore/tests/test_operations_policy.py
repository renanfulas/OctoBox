"""
ARQUIVO: testes da policy de importacao de leads.

POR QUE ELE EXISTE:
- protege a regra de negocio de limites e trilhos antes da orquestracao HTTP e dos jobs.

O QUE ESTE ARQUIVO FAZ:
1. valida roteamento por volume real.
2. valida limite diario por tipo.
3. valida limite mensal por tipo.
4. valida que job rejeitado nao conta como upload aceito.

PONTOS CRITICOS:
- se estes testes quebrarem, a importacao pode ir para o trilho errado ou bloquear o owner injustamente.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from operations.models import (
    LeadImportDeclaredRange,
    LeadImportJob,
    LeadImportJobStatus,
    LeadImportProcessingMode,
    LeadImportSourceType,
)
from operations.services.lead_import_policy import (
    count_daily_import_usage,
    count_monthly_import_usage,
    evaluate_lead_import_policy,
)


class LeadImportPolicyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='owner-policy',
            email='owner-policy@example.com',
            password='senha-forte-123',
        )
        self.today = timezone.localdate()

    def _create_job(
        self,
        *,
        source_type=LeadImportSourceType.WHATSAPP_LIST,
        status=LeadImportJobStatus.RECEIVED,
        created_at=None,
    ):
        job = LeadImportJob.objects.create(
            created_by=self.user,
            source_type=source_type,
            declared_range=LeadImportDeclaredRange.UP_TO_200,
            status=status,
        )
        if created_at is not None:
            LeadImportJob.objects.filter(pk=job.pk).update(created_at=created_at, updated_at=created_at)
            job.refresh_from_db()
        return job

    def test_evaluate_policy_routes_sync_for_up_to_200_leads(self):
        decision = evaluate_lead_import_policy(
            source_type=LeadImportSourceType.WHATSAPP_LIST,
            detected_lead_count=200,
            today=self.today,
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.processing_mode, LeadImportProcessingMode.SYNC)
        self.assertEqual(decision.reason_code, 'accepted')

    def test_evaluate_policy_routes_background_for_201_to_500_leads(self):
        decision = evaluate_lead_import_policy(
            source_type=LeadImportSourceType.WHATSAPP_LIST,
            detected_lead_count=347,
            today=self.today,
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.processing_mode, LeadImportProcessingMode.ASYNC_NOW)

    def test_evaluate_policy_routes_night_for_501_to_2000_leads(self):
        decision = evaluate_lead_import_policy(
            source_type=LeadImportSourceType.WHATSAPP_LIST,
            detected_lead_count=1200,
            today=self.today,
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.processing_mode, LeadImportProcessingMode.ASYNC_NIGHT)

    def test_evaluate_policy_rejects_more_than_2000_leads(self):
        decision = evaluate_lead_import_policy(
            source_type=LeadImportSourceType.WHATSAPP_LIST,
            detected_lead_count=2001,
            today=self.today,
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason_code, 'lead_limit_exceeded')
        self.assertEqual(decision.processing_mode, '')

    def test_evaluate_policy_blocks_second_daily_upload_for_same_source(self):
        self._create_job(source_type=LeadImportSourceType.WHATSAPP_LIST)

        decision = evaluate_lead_import_policy(
            source_type=LeadImportSourceType.WHATSAPP_LIST,
            detected_lead_count=100,
            today=self.today,
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason_code, 'daily_limit_reached')
        self.assertEqual(decision.daily_usage, 1)

    def test_evaluate_policy_allows_different_source_type_on_same_day(self):
        self._create_job(source_type=LeadImportSourceType.WHATSAPP_LIST)

        decision = evaluate_lead_import_policy(
            source_type=LeadImportSourceType.TECNOFIT_EXPORT,
            detected_lead_count=100,
            today=self.today,
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.processing_mode, LeadImportProcessingMode.SYNC)

    def test_evaluate_policy_blocks_fourth_monthly_upload_for_same_source(self):
        month_start = self.today.replace(day=1)
        self._create_job(
            source_type=LeadImportSourceType.NEXTFIT_EXPORT,
            created_at=timezone.make_aware(timezone.datetime.combine(month_start, timezone.datetime.min.time())),
        )
        self._create_job(
            source_type=LeadImportSourceType.NEXTFIT_EXPORT,
            created_at=timezone.make_aware(
                timezone.datetime.combine(month_start + timezone.timedelta(days=3), timezone.datetime.min.time())
            ),
        )
        self._create_job(
            source_type=LeadImportSourceType.NEXTFIT_EXPORT,
            created_at=timezone.make_aware(
                timezone.datetime.combine(month_start + timezone.timedelta(days=7), timezone.datetime.min.time())
            ),
        )

        decision = evaluate_lead_import_policy(
            source_type=LeadImportSourceType.NEXTFIT_EXPORT,
            detected_lead_count=100,
            today=self.today,
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason_code, 'monthly_limit_reached')
        self.assertEqual(decision.monthly_usage, 3)

    def test_rejected_job_does_not_count_for_frequency_limits(self):
        self._create_job(
            source_type=LeadImportSourceType.IPHONE_VCF,
            status=LeadImportJobStatus.REJECTED,
        )

        self.assertEqual(
            count_daily_import_usage(source_type=LeadImportSourceType.IPHONE_VCF, today=self.today),
            0,
        )
        self.assertEqual(
            count_monthly_import_usage(source_type=LeadImportSourceType.IPHONE_VCF, today=self.today),
            0,
        )

        decision = evaluate_lead_import_policy(
            source_type=LeadImportSourceType.IPHONE_VCF,
            detected_lead_count=180,
            today=self.today,
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.processing_mode, LeadImportProcessingMode.SYNC)
