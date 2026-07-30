"""
ARQUIVO: testes de shrinkage e correcao local (Onda 9).

POR QUE ELE EXISTE:
- apply_shrinkage() e a formula que resolve o problema ja conhecido do
  churn (min_realized_count vira gambiarra de amostra pequena). Sem teste
  direto de monotonicidade e dos extremos (n=0, n grande), uma regressao
  aqui volta a produzir leitura descontinua ou uma "correcao" que na
  verdade ignora o prior ou ignora o dado local.
"""

from datetime import timedelta

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from catalog.finance_snapshot.ai.scoring import build_recommendation_historical_score_map
from intelligence_network.benchmark import (
    DEFAULT_MIN_BOXES_FOR_BENCHMARK,
    resolve_channel_reading_with_network_prior,
)
from intelligence_network.models import NetworkChannelAggregate
from intelligence_network.shrinkage import DEFAULT_PRIOR_WEIGHT, apply_shrinkage


class ApplyShrinkageTests(SimpleTestCase):
    def test_prior_dominates_with_zero_local_n(self):
        rate = apply_shrinkage(local_rate=0.0, local_n=0, prior_rate=18.0)
        self.assertEqual(rate, 18.0)

    def test_local_dominates_with_large_local_n(self):
        rate = apply_shrinkage(local_rate=50.0, local_n=10_000, prior_rate=18.0, prior_weight=10)
        # com n_local >> prior_weight, o resultado fica bem perto do local.
        self.assertAlmostEqual(rate, 50.0, delta=0.1)

    def test_convergence_is_monotonic_towards_local_rate(self):
        """Conforme local_n cresce (prior e local fixos), a leitura
        ajustada se move continuamente na direcao do local_rate, sem
        saltos nem oscilar de volta para o prior."""
        local_rate, prior_rate = 60.0, 20.0
        previous = apply_shrinkage(local_rate=local_rate, local_n=0, prior_rate=prior_rate)
        for local_n in (1, 5, 10, 20, 50, 200, 1000):
            current = apply_shrinkage(local_rate=local_rate, local_n=local_n, prior_rate=prior_rate)
            self.assertGreaterEqual(current, previous)
            previous = current
        self.assertAlmostEqual(previous, local_rate, delta=1.0)

    def test_default_prior_weight_is_ten(self):
        self.assertEqual(DEFAULT_PRIOR_WEIGHT, 10)
        # n_local igual ao peso do prior -> media simples entre os dois.
        rate = apply_shrinkage(local_rate=30.0, local_n=10, prior_rate=10.0, prior_weight=10)
        self.assertEqual(rate, 20.0)


class ResolveChannelReadingWithNetworkPriorTests(TestCase):
    def _seed_cohort(self, *, box_cohort='pequeno', channel='instagram', window='2026-01-01:2026-03-01', rate=20.0, contributed_at=None):
        for i in range(DEFAULT_MIN_BOXES_FOR_BENCHMARK):
            NetworkChannelAggregate.objects.create(
                box_slug=f'box-{i}',
                box_cohort=box_cohort,
                segment_key='',
                channel=channel,
                window=window,
                captured_total=100,
                converted_total=int(rate),
                retained_90d_total=0,
                k_floor_applied=10,
                contributed_at=contributed_at or timezone.now(),
            )

    def test_reading_marks_is_network_prior_on_cold_start(self):
        self._seed_cohort(rate=18.0)

        reading = resolve_channel_reading_with_network_prior(
            box_cohort='pequeno', channel='instagram', window='2026-01-01:2026-03-01',
            local_captured_total=0, local_converted_total=0,
        )

        self.assertIsNotNone(reading)
        self.assertTrue(reading['is_network_prior'])
        self.assertEqual(reading['adjusted_rate'], reading['network_prior_rate'])

    def test_reading_stops_marking_network_prior_once_local_data_exists(self):
        self._seed_cohort(rate=18.0)

        reading = resolve_channel_reading_with_network_prior(
            box_cohort='pequeno', channel='instagram', window='2026-01-01:2026-03-01',
            local_captured_total=50, local_converted_total=25,
        )

        self.assertFalse(reading['is_network_prior'])
        self.assertEqual(reading['local_rate'], 50.0)

    def test_returns_none_when_no_publishable_prior_exists(self):
        reading = resolve_channel_reading_with_network_prior(
            box_cohort='pequeno', channel='instagram', window='2026-01-01:2026-03-01',
            local_captured_total=0, local_converted_total=0,
        )
        self.assertIsNone(reading)

    def test_stale_contribution_is_not_used_as_prior(self):
        """Regressao: prior contribuido ha muito tempo (canal que pode ter
        decaido) nao pode continuar influenciando a leitura ajustada so
        porque ninguem rodou o job de novo."""
        stale_at = timezone.now() - timedelta(days=100)
        self._seed_cohort(rate=18.0, contributed_at=stale_at)

        reading = resolve_channel_reading_with_network_prior(
            box_cohort='pequeno', channel='instagram', window='2026-01-01:2026-03-01',
            local_captured_total=0, local_converted_total=0,
        )

        self.assertIsNone(reading)


class BuildRecommendationHistoricalScoreMapNetworkPriorTests(SimpleTestCase):
    def test_backward_compatible_without_network_prior_map(self):
        analytics = {
            'recommendation_performance': [
                {'recommended_action': 'send_financial_followup', 'historical_score': 42.0, 'realized_count': 5},
            ]
        }

        score_map = build_recommendation_historical_score_map(analytics)

        self.assertEqual(score_map, {'send_financial_followup': 42.0})

    def test_action_without_local_history_and_with_prior_gets_cold_start_value(self):
        analytics = {'recommendation_performance': []}

        score_map = build_recommendation_historical_score_map(
            analytics, network_prior_score_map={'review_winback': 25.0}
        )

        self.assertEqual(score_map['review_winback'], 25.0)

    def test_action_with_local_history_and_prior_gets_shrinkage_blend(self):
        analytics = {
            'recommendation_performance': [
                {'recommended_action': 'monitor_and_nudge', 'historical_score': 60.0, 'realized_count': 10},
            ]
        }

        score_map = build_recommendation_historical_score_map(
            analytics, network_prior_score_map={'monitor_and_nudge': 20.0}
        )

        expected = apply_shrinkage(local_rate=60.0, local_n=10, prior_rate=20.0)
        self.assertEqual(score_map['monitor_and_nudge'], expected)

    def test_action_without_matching_prior_is_unaffected(self):
        analytics = {
            'recommendation_performance': [
                {'recommended_action': 'escalate_manual_retention', 'historical_score': 33.0, 'realized_count': 5},
            ]
        }

        score_map = build_recommendation_historical_score_map(
            analytics, network_prior_score_map={'review_winback': 25.0}
        )

        self.assertEqual(score_map['escalate_manual_retention'], 33.0)
