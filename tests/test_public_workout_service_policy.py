from django.test import SimpleTestCase, override_settings

from public_workouts.models import PublicWorkoutTier
from public_workouts.service_policy import get_tier_service_policy


class PublicWorkoutServicePolicyTests(SimpleTestCase):
    def test_tier_matrix_matches_commercial_contract(self):
        essencial = get_tier_service_policy(PublicWorkoutTier.ESSENCIAL)
        completo = get_tier_service_policy(PublicWorkoutTier.COMPLETO)
        premium = get_tier_service_policy(PublicWorkoutTier.PREMIUM)

        self.assertIsNone(essencial.nutrition_initial_slo_hours)
        self.assertIsNotNone(completo.nutrition_initial_slo_hours)
        self.assertEqual(premium.training_review_cadence_days, 7)
        self.assertEqual(premium.nutrition_review_cadence_days, 7)
        self.assertLess(premium.priority, completo.priority)
        self.assertLess(completo.priority, essencial.priority)

    @override_settings(PUBLIC_WORKOUT_PREMIUM_TRAINING_SLO_HOURS=24)
    def test_operational_override_does_not_change_code_contract(self):
        policy = get_tier_service_policy(PublicWorkoutTier.PREMIUM)

        self.assertEqual(policy.training_initial_slo_hours, 24)
