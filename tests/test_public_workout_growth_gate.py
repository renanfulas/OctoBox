from datetime import date, timedelta
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.utils import ProgrammingError
from django.test import TestCase, override_settings

from public_workouts.growth_gate import evaluate_growth_readiness
from public_workouts.models import PublicWorkoutMetricSnapshot


def _payload(*, status='green', slo=0.96, attribution=0.80):
    return {
        'growth_gate': {'status': status, 'blockers': [], 'warnings': []},
        'operations': {'completed_on_time_rate': slo},
        'commercial': {'attribution': {'known_paid_rate': attribution}},
    }


@override_settings(
    PUBLIC_WORKOUT_GROWTH_MIN_SLO_RATE=0.95,
    PUBLIC_WORKOUT_GROWTH_MIN_ATTRIBUTION_RATE=0.70,
)
class PublicWorkoutGrowthGateTests(TestCase):
    as_of = date(2026, 9, 21)

    def _snapshots(self, *, status='green', slo=0.96, attribution=0.80):
        for offset in range(28):
            PublicWorkoutMetricSnapshot.objects.create(
                metric_date=self.as_of - timedelta(days=27 - offset),
                payload=_payload(status=status, slo=slo, attribution=attribution),
            )

    def test_requires_complete_observation_and_green_window(self):
        result = evaluate_growth_readiness(as_of=self.as_of)

        self.assertFalse(result['ready_to_scale'])
        self.assertIn('missing_daily_snapshots', result['blockers'])
        self.assertIn('growth_gate_not_green_for_required_window', result['blockers'])

    def test_returns_ready_only_after_all_measurable_requirements_pass(self):
        self._snapshots()

        result = evaluate_growth_readiness(as_of=self.as_of)

        self.assertTrue(result['ready_to_scale'])
        self.assertEqual(result['blockers'], [])
        self.assertEqual(result['snapshot_days_found'], 28)

    def test_recent_red_day_blocks_even_with_full_history(self):
        self._snapshots()
        PublicWorkoutMetricSnapshot.objects.filter(metric_date=self.as_of).update(
            payload=_payload(status='red'),
        )

        result = evaluate_growth_readiness(as_of=self.as_of)

        self.assertFalse(result['ready_to_scale'])
        self.assertIn('growth_gate_not_green_for_required_window', result['blockers'])

    def test_missing_slo_or_attribution_never_becomes_green_by_default(self):
        self._snapshots(slo=None, attribution=None)

        result = evaluate_growth_readiness(as_of=self.as_of)

        self.assertFalse(result['ready_to_scale'])
        self.assertIn('slo_sample_unavailable', result['blockers'])
        self.assertIn('attribution_sample_unavailable', result['blockers'])

    def test_strict_command_fails_while_gate_is_not_ready(self):
        with self.assertRaises(CommandError):
            call_command(
                'evaluate_public_workout_growth_gate',
                '--as-of', self.as_of.isoformat(), '--strict', stdout=StringIO(),
            )

    def test_command_explains_missing_snapshot_table(self):
        with self.assertRaisesRegex(CommandError, 'Snapshots Curva não estão disponíveis'):
            with self.settings():
                from unittest.mock import patch
                with patch(
                    'public_workouts.management.commands.evaluate_public_workout_growth_gate.'
                    'evaluate_growth_readiness', side_effect=ProgrammingError('missing table'),
                ):
                    call_command('evaluate_public_workout_growth_gate', stdout=StringIO())
