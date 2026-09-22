from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from public_workouts.experiments import assign_active_experiments, build_experiment_report
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutAcquisitionSession,
    PublicWorkoutExperiment,
    PublicWorkoutExperimentAssignment,
    PublicWorkoutExperimentStatus,
    PublicWorkoutExperimentVariant,
    PublicWorkoutPayment,
    PublicWorkoutPaymentStatus,
    PublicWorkoutSubscription,
)


@override_settings(PUBLIC_WORKOUT_FUNNEL_TRACKING_ENABLED=True)
class PublicWorkoutExperimentTests(TestCase):
    def experiment(self, **overrides):
        values = {
            'key': 'hero-v1',
            'name': 'Hero V1',
            'hypothesis': 'Uma promessa concreta aumenta pagamentos.',
            'status': PublicWorkoutExperimentStatus.RUNNING,
            'starts_at': timezone.now() - timedelta(minutes=1),
            'minimum_sample_size': 20,
        }
        values.update(overrides)
        experiment = PublicWorkoutExperiment.objects.create(**values)
        control = PublicWorkoutExperimentVariant.objects.create(
            experiment=experiment, key='controle', name='Controle', allocation_weight=50,
        )
        challenger = PublicWorkoutExperimentVariant.objects.create(
            experiment=experiment, key='desafiante', name='Desafiante', allocation_weight=50,
            payload={'hero_copy': 'Uma promessa mais concreta'},
        )
        return experiment, control, challenger

    def test_landing_assigns_one_stable_variant_and_exposes_safe_payload(self):
        experiment, _control, _challenger = self.experiment()
        first = self.client.get(reverse('public-workout-landing'))
        assignment = PublicWorkoutExperimentAssignment.objects.get(experiment=experiment)
        second = self.client.get(reverse('public-workout-landing'))

        self.assertEqual(PublicWorkoutExperimentAssignment.objects.count(), 1)
        self.assertEqual(
            PublicWorkoutExperimentAssignment.objects.get().variant_id,
            assignment.variant_id,
        )
        self.assertContains(first, 'curva-experiment-assignments')
        self.assertContains(first, experiment.key)
        self.assertContains(second, assignment.variant.key)

    def test_inactive_or_single_variant_experiment_does_not_assign(self):
        experiment, _control, challenger = self.experiment(status=PublicWorkoutExperimentStatus.PAUSED)
        session = PublicWorkoutAcquisitionSession.objects.create()
        self.assertEqual(assign_active_experiments(session), [])
        experiment.status = PublicWorkoutExperimentStatus.RUNNING
        experiment.save(update_fields=['status', 'updated_at'])
        challenger.is_active = False
        challenger.save(update_fields=['is_active', 'updated_at'])
        self.assertEqual(assign_active_experiments(session), [])

    def test_assignment_is_immutable_when_weights_change(self):
        experiment, control, challenger = self.experiment()
        session = PublicWorkoutAcquisitionSession.objects.create()
        original = assign_active_experiments(session)[0]
        control.allocation_weight = 1
        challenger.allocation_weight = 999
        control.save(update_fields=['allocation_weight', 'updated_at'])
        challenger.save(update_fields=['allocation_weight', 'updated_at'])
        repeated = assign_active_experiments(session)[0]
        self.assertEqual(repeated.pk, original.pk)
        self.assertEqual(repeated.variant_id, original.variant_id)

    def test_report_waits_for_mature_sample_then_identifies_clear_leader(self):
        at = timezone.now()
        experiment, control, challenger = self.experiment(starts_at=at - timedelta(days=12))
        assigned_at = at - timedelta(days=10)
        for variant in (control, challenger):
            for index in range(20):
                session = PublicWorkoutAcquisitionSession.objects.create(
                    first_seen_at=assigned_at, last_seen_at=assigned_at,
                )
                PublicWorkoutExperimentAssignment.objects.create(
                    experiment=experiment, variant=variant,
                    acquisition_session=session, assigned_at=assigned_at,
                )
                if variant == control:
                    account = PublicWorkoutAccount.objects.create(email=f'{variant.key}-{index}@example.com')
                    subscription = PublicWorkoutSubscription.objects.create(account=account)
                    session.account = account
                    session.subscription = subscription
                    session.save(update_fields=['account', 'subscription'])
                    PublicWorkoutPayment.objects.create(
                        subscription=subscription,
                        gross_amount=Decimal('97'),
                        status=PublicWorkoutPaymentStatus.PAID,
                        due_date=at.date(),
                        paid_at=assigned_at + timedelta(days=1),
                    )

        existing_account = PublicWorkoutAccount.objects.create(email='existing@example.com')
        existing_subscription = PublicWorkoutSubscription.objects.create(account=existing_account)
        existing_session = PublicWorkoutAcquisitionSession.objects.create(
            account=existing_account, subscription=existing_subscription,
            first_seen_at=assigned_at, last_seen_at=assigned_at,
        )
        PublicWorkoutPayment.objects.create(
            subscription=existing_subscription, gross_amount=Decimal('97'),
            status=PublicWorkoutPaymentStatus.PAID, due_date=at.date(),
            paid_at=assigned_at - timedelta(days=1),
        )
        PublicWorkoutExperimentAssignment.objects.create(
            experiment=experiment, variant=control,
            acquisition_session=existing_session, assigned_at=assigned_at,
        )

        report = build_experiment_report(at=at)
        result = report['experiments'][0]
        self.assertEqual(result['decision'], 'leader')
        self.assertEqual(result['candidate_variant'], control.key)
        rows = {row['key']: row for row in result['variants']}
        self.assertEqual(rows[control.key]['mature_conversion_percent'], 100)
        self.assertEqual(rows[control.key]['assigned'], 20)
        self.assertEqual(rows[challenger.key]['mature_conversion_percent'], 0)
        self.assertEqual(result['excluded_existing_customers'], 1)

    def test_command_creates_draft_or_starts_experiment(self):
        output = StringIO()
        call_command(
            'configure_public_workout_experiment',
            '--key', 'pricing-v1', '--name', 'Preço V1',
            '--hypothesis', 'Teste de preço',
            '--variant', 'controle:70', '--variant', 'ancora:30',
            '--conversion-days', '7', '--minimum-sample-size', '50', '--start',
            stdout=output,
        )
        experiment = PublicWorkoutExperiment.objects.get(key='pricing-v1')
        self.assertEqual(experiment.status, PublicWorkoutExperimentStatus.RUNNING)
        self.assertEqual(
            list(experiment.variants.order_by('key').values_list('key', 'allocation_weight')),
            [('ancora', 30), ('controle', 70)],
        )
