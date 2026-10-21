from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from public_workouts.billing import get_or_create_subscription, mark_subscription_canceled
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutNutritionProfile,
    PublicWorkoutProfessional,
    PublicWorkoutProfessionalRole,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTier,
    PublicWorkoutTrainingExperience,
    PublicWorkoutTrainingGoal,
    PublicWorkoutTrainingLocation,
    PublicWorkoutTrainingProfile,
    PublicWorkoutWorkItem,
    PublicWorkoutWorkItemStatus,
    PublicWorkoutWorkItemType,
)
from public_workouts.operations import ensure_required_work_items, transition_work_item


@override_settings(PUBLIC_WORKOUT_OPERATIONS_ENABLED=True)
class PublicWorkoutOperationsTests(TestCase):
    def setUp(self):
        # Com --migrations existem os profissionais reais da migration 0010;
        # este caso testa ownership deterministico com fixtures proprias.
        PublicWorkoutProfessional.objects.update(is_active=False)
        self.trainer = PublicWorkoutProfessional.objects.create(
            name='Treinador', role=PublicWorkoutProfessionalRole.TREINO,
            registration_council='CREF', registration_number='1',
        )
        self.nutritionist = PublicWorkoutProfessional.objects.create(
            name='Nutricionista', role=PublicWorkoutProfessionalRole.NUTRICAO,
            registration_council='CRN', registration_number='2',
        )
        self.account = PublicWorkoutAccount.objects.create(email='operacao@example.com')
        self.subscription = get_or_create_subscription(
            account=self.account, tier=PublicWorkoutTier.PREMIUM, plan_slug='operacao',
        )
        self.subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
        self.subscription.save(update_fields=['status'])

    def _training_profile(self):
        return PublicWorkoutTrainingProfile.objects.create(
            account=self.account, goal=PublicWorkoutTrainingGoal.HYPERTROPHY,
            training_experience=PublicWorkoutTrainingExperience.MORE_THAN_2_YEARS,
            days_per_week=4, training_location=PublicWorkoutTrainingLocation.FULL_GYM,
            consent_ai_processing_at=timezone.now(),
        )

    def _nutrition_profile(self):
        return PublicWorkoutNutritionProfile.objects.create(
            account=self.account, objetivo='Saude', rotina_alimentar='Regular',
            consent_health_processing_at=timezone.now(), consent_version='nutrition-v1',
        )

    def test_creates_training_and_nutrition_work_only_after_each_intake(self):
        self.assertEqual(ensure_required_work_items(self.subscription.pk), [])

        self._training_profile()
        ensure_required_work_items(self.subscription.pk)
        self.assertTrue(PublicWorkoutWorkItem.objects.filter(
            item_type=PublicWorkoutWorkItemType.TRAINING_PROGRAM,
            assigned_to=self.trainer,
        ).exists())
        self.assertFalse(PublicWorkoutWorkItem.objects.filter(
            item_type=PublicWorkoutWorkItemType.NUTRITION_PLAN,
        ).exists())

        self._nutrition_profile()
        ensure_required_work_items(self.subscription.pk)
        nutrition = PublicWorkoutWorkItem.objects.get(item_type=PublicWorkoutWorkItemType.NUTRITION_PLAN)
        self.assertEqual(nutrition.assigned_to, self.nutritionist)
        self.assertEqual(nutrition.priority, 30)

    def test_reconciliation_is_idempotent(self):
        self._training_profile()
        ensure_required_work_items(self.subscription.pk)
        ensure_required_work_items(self.subscription.pk)

        self.assertEqual(PublicWorkoutWorkItem.objects.count(), 1)

    def test_transition_records_start_completion_and_actual_effort(self):
        self._training_profile()
        ensure_required_work_items(self.subscription.pk)
        item = PublicWorkoutWorkItem.objects.get()

        transition_work_item(item.pk, to_status=PublicWorkoutWorkItemStatus.IN_PROGRESS)
        transition_work_item(
            item.pk, to_status=PublicWorkoutWorkItemStatus.DONE, actual_effort_minutes=52,
        )

        item.refresh_from_db()
        self.assertIsNotNone(item.started_at)
        self.assertIsNotNone(item.completed_at)
        self.assertEqual(item.actual_effort_minutes, 52)

    def test_invalid_transition_is_rejected(self):
        self._training_profile()
        ensure_required_work_items(self.subscription.pk)
        item = PublicWorkoutWorkItem.objects.get()
        transition_work_item(item.pk, to_status=PublicWorkoutWorkItemStatus.DONE)

        with self.assertRaises(ValueError):
            transition_work_item(item.pk, to_status=PublicWorkoutWorkItemStatus.IN_PROGRESS)

    def test_canceling_subscription_cancels_open_work(self):
        self._training_profile()
        ensure_required_work_items(self.subscription.pk)

        mark_subscription_canceled(self.subscription, reason='cliente cancelou')

        self.assertEqual(
            PublicWorkoutWorkItem.objects.get().status,
            PublicWorkoutWorkItemStatus.CANCELED,
        )

    def test_premium_slo_is_shorter_than_default_three_days(self):
        self._training_profile()
        before = timezone.now()
        ensure_required_work_items(self.subscription.pk)
        item = PublicWorkoutWorkItem.objects.get()

        self.assertLessEqual(item.due_at, before + timedelta(hours=49))

    def test_flag_off_keeps_runtime_unchanged(self):
        self._training_profile()
        with self.settings(PUBLIC_WORKOUT_OPERATIONS_ENABLED=False):
            ensure_required_work_items(self.subscription.pk)

        self.assertFalse(PublicWorkoutWorkItem.objects.exists())
