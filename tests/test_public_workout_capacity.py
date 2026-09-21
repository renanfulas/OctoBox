from django.test import TestCase, override_settings

from public_workouts.capacity import get_tier_capacity
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutProfessional,
    PublicWorkoutProfessionalRole,
    PublicWorkoutSubscription,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTier,
    PublicWorkoutWorkItem,
    PublicWorkoutWorkItemType,
)
from django.utils import timezone


class PublicWorkoutCapacityTests(TestCase):
    def setUp(self):
        self.trainer = PublicWorkoutProfessional.objects.create(
            name='Treino', role=PublicWorkoutProfessionalRole.TREINO,
            registration_council='CREF', registration_number='1',
            weekly_capacity_minutes=100,
        )
        self.nutritionist = PublicWorkoutProfessional.objects.create(
            name='Nutri', role=PublicWorkoutProfessionalRole.NUTRICAO,
            registration_council='CRN', registration_number='2',
            weekly_capacity_minutes=100,
        )

    def _committed_work(self, *, item_type, minutes):
        account = PublicWorkoutAccount.objects.create(email=f'{item_type}@example.com')
        subscription = PublicWorkoutSubscription.objects.create(
            account=account, tier=PublicWorkoutTier.PREMIUM,
            status=PublicWorkoutSubscriptionStatus.ACTIVE,
        )
        return PublicWorkoutWorkItem.objects.create(
            account=account, subscription=subscription, item_type=item_type,
            cycle_key='capacity-test', estimated_effort_minutes=minutes,
            due_at=timezone.now(),
        )

    @override_settings(PUBLIC_WORKOUT_CAPACITY_MODE='enforce', PUBLIC_WORKOUT_CAPACITY_MAX_UTILIZATION=0.85)
    def test_enforce_blocks_when_incremental_effort_exceeds_role_limit(self):
        self._committed_work(item_type=PublicWorkoutWorkItemType.TRAINING_PROGRAM, minutes=50)

        snapshot = get_tier_capacity(PublicWorkoutTier.ESSENCIAL)

        self.assertTrue(snapshot['configured'])
        self.assertFalse(snapshot['raw_available'])
        self.assertFalse(snapshot['checkout_allowed'])

    @override_settings(PUBLIC_WORKOUT_CAPACITY_MODE='observe', PUBLIC_WORKOUT_CAPACITY_MAX_UTILIZATION=0.85)
    def test_observe_never_blocks_checkout(self):
        self._committed_work(item_type=PublicWorkoutWorkItemType.TRAINING_PROGRAM, minutes=90)

        snapshot = get_tier_capacity(PublicWorkoutTier.ESSENCIAL)

        self.assertFalse(snapshot['raw_available'])
        self.assertTrue(snapshot['checkout_allowed'])

    @override_settings(PUBLIC_WORKOUT_CAPACITY_MODE='enforce')
    def test_complete_requires_both_professional_pools_configured(self):
        self.nutritionist.weekly_capacity_minutes = 0
        self.nutritionist.save(update_fields=['weekly_capacity_minutes'])

        snapshot = get_tier_capacity(PublicWorkoutTier.COMPLETO)

        self.assertFalse(snapshot['configured'])
        self.assertFalse(snapshot['checkout_allowed'])
