"""
ARQUIVO: testes do feature layer de leads (Onda 6).

POR QUE ELE EXISTE:
- compute_lead_channel_facts() e deduplicate_by_phone() sao calculo puro
  (features.py) — sem cobertura direta, um erro de agregacao ou de
  deduplicacao vaza silenciosamente para as celulas persistidas.
- resolve_publishable_conversion_rate() e o piso de publicacao: sem teste,
  uma celula com 2 conversoes pode voltar a virar "leitura estatistica"
  como ja aconteceu no churn (ver catalog/finance_snapshot/ai/learning.py).
"""

from datetime import datetime

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from intelligence.leads.features import (
    DEFAULT_MIN_CONVERSIONS_TO_PUBLISH,
    compute_lead_channel_facts,
    deduplicate_by_phone,
    resolve_publishable_conversion_rate,
)
from intelligence.models import LeadChannelDailyFact
from onboarding.attribution import build_intake_attribution_payload
from onboarding.models import IntakeStatus, StudentIntake


def _row(
    *,
    phone_lookup_index,
    created_at,
    status=IntakeStatus.NEW,
    converted_at=None,
    source='manual',
    acquisition_channel='instagram',
):
    return {
        'phone_lookup_index': phone_lookup_index,
        'created_at': created_at,
        'status': status,
        'converted_at': converted_at,
        'source': source,
        'raw_payload': build_intake_attribution_payload(source=source, acquisition_channel=acquisition_channel),
    }


class DeduplicateByPhoneTests(SimpleTestCase):
    def test_keeps_earliest_row_per_phone(self):
        early = _row(phone_lookup_index='abc', created_at=datetime(2026, 1, 1))
        late = _row(phone_lookup_index='abc', created_at=datetime(2026, 1, 5))

        result = deduplicate_by_phone([late, early])

        self.assertEqual(result, [early])

    def test_passes_through_rows_without_phone_lookup_index(self):
        no_phone_a = _row(phone_lookup_index='', created_at=datetime(2026, 1, 1))
        no_phone_b = _row(phone_lookup_index='', created_at=datetime(2026, 1, 2))

        result = deduplicate_by_phone([no_phone_a, no_phone_b])

        self.assertEqual(len(result), 2)


class ComputeLeadChannelFactsTests(SimpleTestCase):
    def test_aggregates_by_channel_and_provenance(self):
        rows = [
            _row(phone_lookup_index='p1', created_at=datetime(2026, 1, 1), acquisition_channel='instagram'),
            _row(phone_lookup_index='p2', created_at=datetime(2026, 1, 2), acquisition_channel='instagram'),
            _row(phone_lookup_index='p3', created_at=datetime(2026, 1, 3), acquisition_channel='referral'),
        ]

        facts = compute_lead_channel_facts(
            rows=rows,
            rule_version='v1',
            input_window='90d',
            window_start=datetime(2026, 1, 1).date(),
            window_end=datetime(2026, 3, 1).date(),
            computed_at=datetime(2026, 3, 2, 12, 0, 0),
        )

        by_channel = {(f['channel'], f['provenance']): f for f in facts}
        self.assertEqual(by_channel[('instagram', 'declared')]['captured_total'], 2)
        self.assertEqual(by_channel[('referral', 'declared')]['captured_total'], 1)

    def test_converted_and_rejected_and_open_are_mutually_exclusive(self):
        rows = [
            _row(
                phone_lookup_index='p1',
                created_at=datetime(2026, 1, 1),
                status=IntakeStatus.APPROVED,
                converted_at=datetime(2026, 1, 11),
            ),
            _row(phone_lookup_index='p2', created_at=datetime(2026, 1, 2), status=IntakeStatus.REJECTED),
            _row(phone_lookup_index='p3', created_at=datetime(2026, 1, 3), status=IntakeStatus.REVIEWING),
        ]

        facts = compute_lead_channel_facts(
            rows=rows,
            rule_version='v1',
            input_window='90d',
            window_start=datetime(2026, 1, 1).date(),
            window_end=datetime(2026, 3, 1).date(),
            computed_at=datetime(2026, 3, 2, 12, 0, 0),
        )

        cell = next(f for f in facts if f['channel'] == 'instagram')
        self.assertEqual(cell['captured_total'], 3)
        self.assertEqual(cell['converted_total'], 1)
        self.assertEqual(cell['rejected_total'], 1)
        self.assertEqual(cell['open_total'], 1)

    def test_median_days_to_conversion_only_counts_converted_rows(self):
        rows = [
            _row(
                phone_lookup_index='p1',
                created_at=datetime(2026, 1, 1),
                status=IntakeStatus.APPROVED,
                converted_at=datetime(2026, 1, 11),
            ),
            _row(
                phone_lookup_index='p2',
                created_at=datetime(2026, 1, 1),
                status=IntakeStatus.APPROVED,
                converted_at=datetime(2026, 1, 21),
            ),
            _row(phone_lookup_index='p3', created_at=datetime(2026, 1, 1), status=IntakeStatus.NEW),
        ]

        facts = compute_lead_channel_facts(
            rows=rows,
            rule_version='v1',
            input_window='90d',
            window_start=datetime(2026, 1, 1).date(),
            window_end=datetime(2026, 3, 1).date(),
            computed_at=datetime(2026, 3, 2, 12, 0, 0),
        )

        cell = next(f for f in facts if f['channel'] == 'instagram')
        # medianas de 10 e 20 dias -> 15.0
        self.assertEqual(float(cell['median_days_to_conversion']), 15.0)

    def test_missing_channel_gets_its_own_sparse_cell(self):
        rows = [_row(phone_lookup_index='p1', created_at=datetime(2026, 1, 1), acquisition_channel='')]
        # forca fallback_source sem mapeamento legado, garantindo provenance=missing
        rows[0]['source'] = 'manual'

        facts = compute_lead_channel_facts(
            rows=rows,
            rule_version='v1',
            input_window='90d',
            window_start=datetime(2026, 1, 1).date(),
            window_end=datetime(2026, 3, 1).date(),
            computed_at=datetime(2026, 3, 2, 12, 0, 0),
        )

        missing_cells = [f for f in facts if f['provenance'] == 'missing']
        self.assertEqual(len(missing_cells), 1)
        self.assertEqual(missing_cells[0]['channel'], '')
        self.assertEqual(missing_cells[0]['captured_total'], 1)

    def test_output_carries_ml_contract_fields(self):
        """rule_version, computed_at e input_window precisam estar em toda
        celula emitida — contrato obrigatorio do documento pai."""
        rows = [_row(phone_lookup_index='p1', created_at=datetime(2026, 1, 1))]

        facts = compute_lead_channel_facts(
            rows=rows,
            rule_version='lead_channel_facts_v1',
            input_window='90d',
            window_start=datetime(2026, 1, 1).date(),
            window_end=datetime(2026, 3, 1).date(),
            computed_at=datetime(2026, 3, 2, 12, 0, 0),
        )

        self.assertTrue(facts)
        for fact in facts:
            self.assertEqual(fact['rule_version'], 'lead_channel_facts_v1')
            self.assertEqual(fact['computed_at'], datetime(2026, 3, 2, 12, 0, 0))
            self.assertEqual(fact['input_window'], '90d')


class ResolvePublishableConversionRateTests(SimpleTestCase):
    def test_suppresses_rate_below_floor(self):
        rate = resolve_publishable_conversion_rate(captured_total=10, converted_total=2)
        self.assertIsNone(rate)

    def test_publishes_rate_at_or_above_floor(self):
        rate = resolve_publishable_conversion_rate(
            captured_total=100,
            converted_total=DEFAULT_MIN_CONVERSIONS_TO_PUBLISH,
        )
        self.assertEqual(rate, 20.0)

    def test_suppresses_when_captured_total_is_zero(self):
        rate = resolve_publishable_conversion_rate(captured_total=0, converted_total=0)
        self.assertIsNone(rate)


class ComputeAndPersistLeadChannelFactsTests(TestCase):
    """Testes de integracao (precisam de banco) do job de orquestracao."""

    def _create_intake(self, *, full_name, phone, created_at, status=IntakeStatus.NEW, converted_at=None, acquisition_channel='instagram'):
        intake = StudentIntake.objects.create(
            full_name=full_name,
            phone=phone,
            source='manual',
            status=status,
            converted_at=converted_at,
            raw_payload=build_intake_attribution_payload(source='manual', acquisition_channel=acquisition_channel),
        )
        StudentIntake.objects.filter(pk=intake.pk).update(created_at=created_at)
        intake.refresh_from_db()
        return intake

    def test_job_is_idempotent(self):
        from intelligence.leads.jobs import compute_and_persist_lead_channel_facts

        today = timezone.localdate()
        matured_date = timezone.now() - timezone.timedelta(days=40)
        self._create_intake(full_name='Lead A', phone='5511910001111', created_at=matured_date)

        first_result = compute_and_persist_lead_channel_facts(today=today)
        first_snapshot = list(
            LeadChannelDailyFact.objects.values('channel', 'provenance', 'captured_total', 'converted_total')
        )

        second_result = compute_and_persist_lead_channel_facts(today=today)
        second_snapshot = list(
            LeadChannelDailyFact.objects.values('channel', 'provenance', 'captured_total', 'converted_total')
        )

        self.assertEqual(first_result['cells_persisted'], second_result['cells_persisted'])
        self.assertEqual(first_snapshot, second_snapshot)
        self.assertEqual(LeadChannelDailyFact.objects.count(), first_result['cells_persisted'])

    def test_recent_lead_does_not_enter_the_cohort(self):
        """Regressao de censura a direita: lead criado ONTEM nao pode
        contar como capturado — ele so nao teve tempo de converter ainda."""
        from intelligence.leads.jobs import compute_and_persist_lead_channel_facts

        today = timezone.localdate()
        self._create_intake(
            full_name='Lead Recente',
            phone='5511910002222',
            created_at=timezone.now() - timezone.timedelta(days=2),
        )

        compute_and_persist_lead_channel_facts(today=today, maturation_days=30)

        self.assertEqual(LeadChannelDailyFact.objects.filter(channel='instagram').count(), 0)

    def test_job_does_not_write_to_student_intake(self):
        """ML nunca escreve verdade primaria: o job so pode gravar em
        LeadChannelDailyFact, nunca em StudentIntake."""
        from intelligence.leads.jobs import compute_and_persist_lead_channel_facts

        today = timezone.localdate()
        intake = self._create_intake(
            full_name='Lead Intocado',
            phone='5511910003333',
            created_at=timezone.now() - timezone.timedelta(days=40),
        )
        before = StudentIntake.objects.get(pk=intake.pk)

        compute_and_persist_lead_channel_facts(today=today)

        after = StudentIntake.objects.get(pk=intake.pk)
        self.assertEqual(before.status, after.status)
        self.assertEqual(before.updated_at, after.updated_at)
