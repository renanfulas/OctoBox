from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from public_workouts.billing import get_or_create_subscription, mark_subscription_canceled
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutNutritionProfile,
    PublicWorkoutOutboxMessage,
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
from public_workouts.outbox import TOPIC_STAFF_WORK_ITEM_OPENED, drain_public_workout_outbox


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


@override_settings(
    PUBLIC_WORKOUT_OPERATIONS_ENABLED=True,
    PUBLIC_WORKOUT_STAFF_ALERT_EMAILS=['equipe@example.com'],
    PUBLIC_WORKOUT_PUBLIC_BASE_URL='https://curva.example.test',
    STUDENT_EMAIL_PROVIDER='smtp',
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class PublicWorkoutWorkItemStaffAlertTests(TestCase):
    """Anamnese respondida depois do pagamento abria trabalho em silencio."""

    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='alerta@example.com')
        self.subscription = get_or_create_subscription(
            account=self.account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='alerta',
        )
        self.subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
        self.subscription.save(update_fields=['status'])

    def _training_profile(self, **fields):
        return PublicWorkoutTrainingProfile.objects.create(
            account=self.account, goal=PublicWorkoutTrainingGoal.HYPERTROPHY,
            training_experience=PublicWorkoutTrainingExperience.MORE_THAN_2_YEARS,
            days_per_week=4, training_location=PublicWorkoutTrainingLocation.FULL_GYM,
            consent_ai_processing_at=timezone.now(), **fields,
        )

    def _alerts(self):
        return PublicWorkoutOutboxMessage.objects.filter(topic=TOPIC_STAFF_WORK_ITEM_OPENED)

    def test_new_work_item_queues_exactly_one_staff_alert(self):
        self._training_profile()

        ensure_required_work_items(self.subscription.pk)
        ensure_required_work_items(self.subscription.pk)

        item = PublicWorkoutWorkItem.objects.get()
        self.assertEqual(list(self._alerts().values_list('aggregate_id', flat=True)), [str(item.pk)])

    def test_no_alert_while_nothing_new_opens(self):
        ensure_required_work_items(self.subscription.pk)

        self.assertFalse(self._alerts().exists())

    def test_alert_email_points_to_the_student_without_intake_answers(self):
        from django.core import mail

        self._training_profile(motivation='resposta-sensivel-da-anamnese', physical_restrictions_detail='hernia L4')
        ensure_required_work_items(self.subscription.pk)

        counters = drain_public_workout_outbox()

        self.assertEqual(counters['sent'], 1)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['equipe@example.com'])
        self.assertIn('Montar treino', message.subject)
        self.assertIn('alerta@example.com', message.subject)
        self.assertIn(f'https://curva.example.test/public-workouts/alunos/{self.account.pk}/', message.body)
        html = message.alternatives[0][0]
        for content in (message.body, html):
            self.assertNotIn('resposta-sensivel-da-anamnese', content)
            self.assertNotIn('hernia', content)

    def test_item_finished_before_the_drain_sends_nothing(self):
        from django.core import mail

        self._training_profile()
        ensure_required_work_items(self.subscription.pk)
        transition_work_item(PublicWorkoutWorkItem.objects.get().pk, to_status=PublicWorkoutWorkItemStatus.DONE)

        drain_public_workout_outbox()

        self.assertEqual(mail.outbox, [])
        self.assertEqual(self._alerts().get().status, 'sent')

    def test_program_published_without_explicit_start_still_counts_for_slo(self):
        from public_workouts.metrics import build_metrics_snapshot
        from public_workouts.schema import build_example_payload
        from public_workouts.services import publish_program

        self._training_profile()
        ensure_required_work_items(self.subscription.pk)
        publish_program(slug='alerta', payload=build_example_payload())

        item = PublicWorkoutWorkItem.objects.get()
        self.assertEqual(item.status, PublicWorkoutWorkItemStatus.DONE)
        self.assertIsNone(item.started_at)
        self.assertEqual(build_metrics_snapshot()['operations']['completed_on_time_rate'], 1.0)


@override_settings(PUBLIC_WORKOUT_OPERATIONS_ENABLED=True)
class PublicWorkoutPlanSlugAssignmentTests(TestCase):
    """Sem plan_slug o rascunho por IA recusa e a assinatura paga espera o admin."""

    def _active_subscription(self, email, plan_slug=None):
        account = PublicWorkoutAccount.objects.create(email=email)
        subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug=plan_slug)
        subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
        subscription.save(update_fields=['status'])
        return subscription

    def test_active_subscription_without_slug_gets_one_from_the_email(self):
        subscription = self._active_subscription('Joao.Conceição+curva@example.com')

        ensure_required_work_items(subscription.pk)

        subscription.refresh_from_db()
        self.assertEqual(subscription.plan_slug, 'joaoconceicaocurva')

    def test_slug_with_someone_elses_history_is_never_reused(self):
        from public_workouts.models import PublicWorkoutAssessment

        # Avaliacao antiga de outra pessoa ainda chaveada por 'carla'.
        PublicWorkoutAssessment.objects.create(plan_slug='carla', measured_at='2026-01-01', weight_kg=60)
        self._active_subscription('carla.antiga@example.com', plan_slug='carla2')
        subscription = self._active_subscription('carla@example.com')

        ensure_required_work_items(subscription.pk)

        subscription.refresh_from_db()
        self.assertEqual(subscription.plan_slug, 'carla3')

    def test_catalog_slug_is_never_reused(self):
        subscription = self._active_subscription('bruno@example.com')

        ensure_required_work_items(subscription.pk)

        subscription.refresh_from_db()
        self.assertEqual(subscription.plan_slug, 'bruno2')

    def test_reserved_route_segment_is_skipped(self):
        subscription = self._active_subscription('offline@example.com')

        ensure_required_work_items(subscription.pk)

        subscription.refresh_from_db()
        self.assertEqual(subscription.plan_slug, 'offline2')

    def test_existing_slug_and_pending_payment_are_left_alone(self):
        chosen = self._active_subscription('escolhido@example.com', plan_slug='slug-do-admin')
        pending_account = PublicWorkoutAccount.objects.create(email='pendente@example.com')
        pending = get_or_create_subscription(account=pending_account, tier=PublicWorkoutTier.ESSENCIAL)

        ensure_required_work_items(chosen.pk)
        ensure_required_work_items(pending.pk)

        chosen.refresh_from_db()
        pending.refresh_from_db()
        self.assertEqual(chosen.plan_slug, 'slug-do-admin')
        self.assertIsNone(pending.plan_slug)
