"""
ARQUIVO: testes de publish_meal_plan/get_active_meal_plan/require_nutrition_tier
(Entrega 6, Fase 4 — docs/plans/public-workouts-escala-e-nutricao-corda.md, D.4/D.6).

POR QUE ELE EXISTE:
- mesma garantia de integridade que publish_program/get_active_program ja
  tem (test_program.py): nunca duas versoes ativas pra mesma conta,
  publicar e' so' criar linha nova, payload malformado nunca publica.
"""

import copy

from django.db import IntegrityError, transaction
from django.test import TestCase

from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutMealPlan,
    PublicWorkoutProfessional,
    PublicWorkoutProfessionalRole,
    PublicWorkoutSubscription,
    PublicWorkoutTier,
)
from public_workouts.nutrition_schema import NutritionPayloadValidationError, build_example_payload
from public_workouts.services import get_active_meal_plan, publish_meal_plan, require_nutrition_tier


def _payload(**overrides) -> dict:
    payload = copy.deepcopy(build_example_payload())
    payload.update(overrides)
    return payload


class RequireNutritionTierTests(TestCase):
    def _subscription(self, tier):
        account = PublicWorkoutAccount.objects.create(email=f'{tier}@example.com')
        return PublicWorkoutSubscription.objects.create(account=account, tier=tier)

    def test_essencial_does_not_have_access(self):
        self.assertFalse(require_nutrition_tier(self._subscription(PublicWorkoutTier.ESSENCIAL)))

    def test_completo_has_access(self):
        self.assertTrue(require_nutrition_tier(self._subscription(PublicWorkoutTier.COMPLETO)))

    def test_premium_has_access(self):
        self.assertTrue(require_nutrition_tier(self._subscription(PublicWorkoutTier.PREMIUM)))


class GetActiveMealPlanTests(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='aluno@example.com')
        self.nutricionista = PublicWorkoutProfessional.objects.get(role=PublicWorkoutProfessionalRole.NUTRICAO)

    def test_returns_none_when_no_plan_exists(self):
        self.assertIsNone(get_active_meal_plan(account_id=self.account.pk))

    def test_returns_payload_of_active_plan(self):
        payload = _payload()
        publish_meal_plan(account_id=self.account.pk, payload=payload, authored_by=self.nutricionista)

        self.assertEqual(get_active_meal_plan(account_id=self.account.pk), payload)

    def test_ignores_inactive_versions(self):
        publish_meal_plan(account_id=self.account.pk, payload=_payload(), authored_by=self.nutricionista)
        publish_meal_plan(
            account_id=self.account.pk,
            payload=_payload(daily_targets={'kcal': 2600, 'protein_g': 190, 'carbs_g': 280, 'fat_g': 75}),
            authored_by=self.nutricionista,
        )

        result = get_active_meal_plan(account_id=self.account.pk)

        self.assertEqual(result['daily_targets']['kcal'], 2600)

    def test_does_not_leak_between_accounts(self):
        other_account = PublicWorkoutAccount.objects.create(email='outro@example.com')
        publish_meal_plan(account_id=self.account.pk, payload=_payload(), authored_by=self.nutricionista)

        self.assertIsNone(get_active_meal_plan(account_id=other_account.pk))


class PublishMealPlanTests(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='aluno@example.com')
        self.nutricionista = PublicWorkoutProfessional.objects.get(role=PublicWorkoutProfessionalRole.NUTRICAO)

    def test_first_publish_creates_version_1_active(self):
        plan = publish_meal_plan(account_id=self.account.pk, payload=_payload(), authored_by=self.nutricionista)

        self.assertEqual(plan.version, 1)
        self.assertTrue(plan.is_active)
        self.assertEqual(PublicWorkoutMealPlan.objects.count(), 1)

    def test_republish_creates_version_2_and_deactivates_version_1(self):
        v1 = publish_meal_plan(account_id=self.account.pk, payload=_payload(), authored_by=self.nutricionista)
        v2 = publish_meal_plan(account_id=self.account.pk, payload=_payload(), authored_by=self.nutricionista)

        v1.refresh_from_db()
        self.assertEqual(v2.version, 2)
        self.assertTrue(v2.is_active)
        self.assertFalse(v1.is_active)

    def test_rejects_malformed_payload_without_creating_a_row(self):
        payload = _payload()
        del payload['daily_targets']

        with self.assertRaises(NutritionPayloadValidationError):
            publish_meal_plan(account_id=self.account.pk, payload=payload, authored_by=self.nutricionista)

        self.assertEqual(PublicWorkoutMealPlan.objects.count(), 0)

    def test_never_ends_up_with_two_active_plans_for_the_same_account(self):
        # Prova a UniqueConstraint (nao so' o comportamento feliz do
        # publish_meal_plan) — mesma garantia que test_program.py tem pra
        # PublicWorkoutProgram.
        publish_meal_plan(account_id=self.account.pk, payload=_payload(), authored_by=self.nutricionista)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PublicWorkoutMealPlan.objects.create(
                    account=self.account, version=99, is_active=True,
                    authored_by=self.nutricionista, payload=_payload(),
                )
