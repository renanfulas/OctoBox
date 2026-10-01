"""
ARQUIVO: testes de public_workouts/risk_signals.py -- classificacao
deterministica de risco do aluno (achado do Renan: adesao + progresso +
pagamento numa leitura so, cada motivo explicito).
"""

from django.test import SimpleTestCase

from public_workouts.risk_signals import compute_student_risk


def _risk(**overrides):
    defaults = dict(
        days_since_last_workout=1,
        declining_movements=[],
        plateaued_movements=[],
        tracked_movement_count=2,
        subscription_status='active',
        days_until_renewal=None,
    )
    defaults.update(overrides)
    return compute_student_risk(**defaults)


class ComputeStudentRiskTests(SimpleTestCase):
    def test_healthy_when_nothing_is_wrong(self):
        signal = _risk()

        self.assertEqual(signal.level, 'healthy')
        self.assertEqual(signal.reasons, [])

    def test_never_registered_is_high_risk(self):
        signal = _risk(days_since_last_workout=None, tracked_movement_count=0)

        self.assertEqual(signal.level, 'high')
        self.assertIn('nunca registrou treino', signal.reasons)

    def test_stale_training_is_high_risk(self):
        signal = _risk(days_since_last_workout=10)

        self.assertEqual(signal.level, 'high')
        self.assertIn('10 dias sem treinar', signal.reasons)

    def test_fading_training_is_medium_risk(self):
        signal = _risk(days_since_last_workout=5)

        self.assertEqual(signal.level, 'medium')

    def test_just_below_fading_threshold_is_healthy(self):
        signal = _risk(days_since_last_workout=4)

        self.assertEqual(signal.level, 'healthy')

    def test_majority_declining_movements_is_high_risk(self):
        signal = _risk(declining_movements=['squat', 'bench'], tracked_movement_count=3)

        self.assertEqual(signal.level, 'high')
        self.assertIn('2 movimento(s) em queda', signal.reasons)

    def test_single_plateaued_movement_among_many_is_medium_risk_only(self):
        signal = _risk(plateaued_movements=['squat'], tracked_movement_count=4)

        self.assertEqual(signal.level, 'medium')
        self.assertIn('1 movimento(s) em platô', signal.reasons)

    def test_payment_problem_is_always_high_risk(self):
        signal = _risk(subscription_status='past_due')

        self.assertEqual(signal.level, 'high')
        self.assertIn('pagamento com problema', signal.reasons)

    def test_suspended_subscription_is_high_risk(self):
        signal = _risk(subscription_status='suspended')

        self.assertEqual(signal.level, 'high')

    def test_renewal_within_window_is_medium_risk(self):
        signal = _risk(days_until_renewal=3)

        self.assertEqual(signal.level, 'medium')
        self.assertIn('renovação em 3 dia(s)', signal.reasons)

    def test_renewal_far_away_is_not_a_signal(self):
        signal = _risk(days_until_renewal=45)

        self.assertEqual(signal.level, 'healthy')
        self.assertEqual(signal.reasons, [])

    def test_renewal_soon_never_downgrades_high_risk_from_stale_training(self):
        signal = _risk(days_since_last_workout=15, days_until_renewal=2)

        self.assertEqual(signal.level, 'high')
        self.assertIn('15 dias sem treinar', signal.reasons)
        self.assertIn('renovação em 2 dia(s)', signal.reasons)

    def test_reasons_accumulate_across_independent_signals(self):
        signal = _risk(
            days_since_last_workout=12, declining_movements=['squat'], tracked_movement_count=3,
            subscription_status='past_due', days_until_renewal=1,
        )

        self.assertEqual(signal.level, 'high')
        self.assertEqual(len(signal.reasons), 4)

    def test_no_tracked_movements_never_raises_a_progress_signal(self):
        signal = _risk(declining_movements=[], plateaued_movements=[], tracked_movement_count=0)

        self.assertEqual(signal.level, 'healthy')
