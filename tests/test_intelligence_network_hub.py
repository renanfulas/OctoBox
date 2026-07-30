"""
ARQUIVO: testes do hub de rede cross-tenant (Onda 8).

POR QUE ELE EXISTE:
- o hub e SHARED (schema public) e agrega dado de VARIOS tenants. Sem
  teste direto de k-anonimato, uma regressao aqui pode expor dado que
  permite inferir uma box individual — o unico risco desta trilha que
  nao e so "numero errado", e vazamento entre clientes.
"""

from datetime import date
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from intelligence.models import LeadChannelDailyFact
from intelligence_network.benchmark import DEFAULT_MIN_BOXES_FOR_BENCHMARK, resolve_channel_benchmark
from intelligence_network.cohort import resolve_box_cohort
from intelligence_network.contribution import DEFAULT_MIN_CAPTURED_TO_CONTRIBUTE, contribute_box_channel_aggregates
from intelligence_network.models import NetworkChannelAggregate
from students.models import Student, StudentStatus

PII_FIELD_NAME_MARKERS = ('name', 'nome', 'phone', 'telefone', 'email', 'cpf', 'payload', 'raw_payload')


def _fake_box(slug):
    return SimpleNamespace(slug=slug)


class ResolveBoxCohortTests(SimpleTestCase):
    def test_bands_are_ordered_and_exclusive(self):
        self.assertEqual(resolve_box_cohort(active_student_count=0), 'micro')
        self.assertEqual(resolve_box_cohort(active_student_count=29), 'micro')
        self.assertEqual(resolve_box_cohort(active_student_count=30), 'pequeno')
        self.assertEqual(resolve_box_cohort(active_student_count=79), 'pequeno')
        self.assertEqual(resolve_box_cohort(active_student_count=80), 'medio')
        self.assertEqual(resolve_box_cohort(active_student_count=199), 'medio')
        self.assertEqual(resolve_box_cohort(active_student_count=200), 'grande')
        self.assertEqual(resolve_box_cohort(active_student_count=5000), 'grande')


class NetworkChannelAggregateHasNoPiiFieldsTests(SimpleTestCase):
    def test_model_fields_do_not_look_like_pii(self):
        """Varredura estatica: nenhum campo do model tem nome que sugira
        dado individual (nome, telefone, email, cpf, payload cru)."""
        field_names = [f.name for f in NetworkChannelAggregate._meta.get_fields()]
        offending = [
            name for name in field_names
            if any(marker in name.lower() for marker in PII_FIELD_NAME_MARKERS)
        ]
        self.assertEqual(offending, [], f'campos suspeitos de PII no hub: {offending}')


class ContributeBoxChannelAggregatesTests(TestCase):
    def _create_fact(self, *, channel, captured_total, converted_total, window_start=date(2026, 1, 1), window_end=date(2026, 3, 1)):
        return LeadChannelDailyFact.objects.create(
            window_start=window_start,
            window_end=window_end,
            channel=channel,
            provenance='declared',
            captured_total=captured_total,
            converted_total=converted_total,
            rejected_total=0,
            open_total=captured_total - converted_total,
            rule_version='lead_channel_facts_v1',
            computed_at=timezone.now(),
            input_window='90d',
        )

    def test_cell_below_floor_does_not_get_contributed(self):
        """Regressao do piso de contribuicao: celula com captured_total
        abaixo do piso nao pode subir para o hub."""
        self._create_fact(channel='instagram', captured_total=DEFAULT_MIN_CAPTURED_TO_CONTRIBUTE - 1, converted_total=1)

        contributed = contribute_box_channel_aggregates(box=_fake_box('box-pequena'))

        self.assertEqual(contributed, 0)
        self.assertEqual(NetworkChannelAggregate.objects.count(), 0)

    def test_cell_at_or_above_floor_is_contributed(self):
        self._create_fact(channel='instagram', captured_total=DEFAULT_MIN_CAPTURED_TO_CONTRIBUTE, converted_total=3)

        contributed = contribute_box_channel_aggregates(box=_fake_box('box-grande'))

        self.assertEqual(contributed, 1)
        row = NetworkChannelAggregate.objects.get()
        self.assertEqual(row.box_slug, 'box-grande')
        self.assertEqual(row.channel, 'instagram')
        self.assertEqual(row.captured_total, DEFAULT_MIN_CAPTURED_TO_CONTRIBUTE)
        self.assertEqual(row.k_floor_applied, DEFAULT_MIN_CAPTURED_TO_CONTRIBUTE)

    def test_missing_channel_cell_is_never_contributed(self):
        self._create_fact(channel='', captured_total=100, converted_total=50)

        contributed = contribute_box_channel_aggregates(box=_fake_box('box-x'))

        self.assertEqual(contributed, 0)

    def test_cohort_reflects_active_student_count(self):
        for i in range(35):
            Student.objects.create(full_name=f'Aluno {i}', phone=f'55119999{i:05d}', status=StudentStatus.ACTIVE)
        self._create_fact(channel='referral', captured_total=15, converted_total=5)

        contribute_box_channel_aggregates(box=_fake_box('box-media'))

        row = NetworkChannelAggregate.objects.get()
        self.assertEqual(row.box_cohort, 'pequeno')

    def test_contribution_is_idempotent(self):
        self._create_fact(channel='instagram', captured_total=20, converted_total=5)

        contribute_box_channel_aggregates(box=_fake_box('box-a'))
        contribute_box_channel_aggregates(box=_fake_box('box-a'))

        self.assertEqual(NetworkChannelAggregate.objects.count(), 1)


class ResolveChannelBenchmarkTests(TestCase):
    def _create_aggregate(self, *, box_slug, box_cohort, channel, captured_total, converted_total, window='2026-01-01:2026-03-01'):
        return NetworkChannelAggregate.objects.create(
            box_slug=box_slug,
            box_cohort=box_cohort,
            segment_key='',
            channel=channel,
            window=window,
            captured_total=captured_total,
            converted_total=converted_total,
            retained_90d_total=0,
            k_floor_applied=DEFAULT_MIN_CAPTURED_TO_CONTRIBUTE,
            contributed_at=timezone.now(),
        )

    def test_benchmark_suppressed_below_min_boxes(self):
        """Regressao de k-anonimato na leitura: com poucas boxes
        contribuindo, o benchmark nao pode publicar (senao da pra inferir
        a taxa de uma box especifica)."""
        for i in range(DEFAULT_MIN_BOXES_FOR_BENCHMARK - 1):
            self._create_aggregate(box_slug=f'box-{i}', box_cohort='pequeno', channel='instagram', captured_total=20, converted_total=4)

        result = resolve_channel_benchmark(box_cohort='pequeno', channel='instagram', window='2026-01-01:2026-03-01')

        self.assertIsNone(result)

    def test_benchmark_publishes_at_or_above_min_boxes(self):
        for i in range(DEFAULT_MIN_BOXES_FOR_BENCHMARK):
            self._create_aggregate(box_slug=f'box-{i}', box_cohort='pequeno', channel='instagram', captured_total=20, converted_total=4)

        result = resolve_channel_benchmark(box_cohort='pequeno', channel='instagram', window='2026-01-01:2026-03-01')

        self.assertIsNotNone(result)
        self.assertEqual(result['box_count'], DEFAULT_MIN_BOXES_FOR_BENCHMARK)
        self.assertEqual(result['median_conversion_rate'], 20.0)

    def test_benchmark_never_returns_a_single_box_identifiable_reading(self):
        """Mesmo com N acima do piso, o resultado exposto e so a mediana +
        contagem de boxes — nunca um box_slug ou linha individual."""
        for i in range(DEFAULT_MIN_BOXES_FOR_BENCHMARK):
            self._create_aggregate(box_slug=f'box-{i}', box_cohort='pequeno', channel='instagram', captured_total=20, converted_total=4)

        result = resolve_channel_benchmark(box_cohort='pequeno', channel='instagram', window='2026-01-01:2026-03-01')

        self.assertNotIn('box_slug', result)
        self.assertNotIn('rows', result)

    def test_cohorts_are_compared_separately(self):
        """Regressao: box grande e box micro nao podem se misturar no
        mesmo benchmark — cada cohort tem sua propria leitura."""
        for i in range(DEFAULT_MIN_BOXES_FOR_BENCHMARK):
            self._create_aggregate(box_slug=f'micro-{i}', box_cohort='micro', channel='instagram', captured_total=10, converted_total=1)
        for i in range(DEFAULT_MIN_BOXES_FOR_BENCHMARK):
            self._create_aggregate(box_slug=f'grande-{i}', box_cohort='grande', channel='instagram', captured_total=100, converted_total=40)

        micro_result = resolve_channel_benchmark(box_cohort='micro', channel='instagram', window='2026-01-01:2026-03-01')
        grande_result = resolve_channel_benchmark(box_cohort='grande', channel='instagram', window='2026-01-01:2026-03-01')

        self.assertEqual(micro_result['median_conversion_rate'], 10.0)
        self.assertEqual(grande_result['median_conversion_rate'], 40.0)
        self.assertNotEqual(micro_result['median_conversion_rate'], grande_result['median_conversion_rate'])
