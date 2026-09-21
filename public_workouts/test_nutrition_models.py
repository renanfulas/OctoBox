"""
ARQUIVO: testes dos modelos de nutricao (Entrega 6, Fase 4 —
docs/plans/public-workouts-escala-e-nutricao-corda.md, D.5/D.6).

POR QUE ELE EXISTE:
- prova as garantias de unicidade de PublicWorkoutMealPlan (mesmo padrao
  de PublicWorkoutProgram — no maximo uma versao por conta, no maximo uma
  ativa por conta) e confirma que a migracao de dado (0010) populou os
  dois PublicWorkoutProfessional reais (ADR-3), nao um seed generico.
"""

from django.db import IntegrityError, transaction
from django.apps import apps as django_apps
from django.test import TestCase
import importlib

from .models import (
    PublicWorkoutAccount,
    PublicWorkoutMealPlan,
    PublicWorkoutNutritionProfile,
    PublicWorkoutProfessional,
    PublicWorkoutProfessionalRole,
)
from .nutrition_schema import build_example_payload


class PublicWorkoutProfessionalSeedMigrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        migration = importlib.import_module(
            'public_workouts.migrations.0010_seed_public_workout_professionals'
        )
        migration.seed_professionals(django_apps, None)

    def test_treino_professional_is_renan_with_real_cref(self):
        professional = PublicWorkoutProfessional.objects.get(role=PublicWorkoutProfessionalRole.TREINO)

        self.assertEqual(professional.name, 'Renan Fulas')
        self.assertEqual(professional.registration_council, 'CREF')
        self.assertEqual(professional.registration_number, '155070-G/SP')

    def test_nutricao_professional_is_giovanna_with_real_crn(self):
        professional = PublicWorkoutProfessional.objects.get(role=PublicWorkoutProfessionalRole.NUTRICAO)

        self.assertEqual(professional.name, 'Giovanna Fontes')
        self.assertEqual(professional.registration_council, 'CRN-3')
        self.assertEqual(professional.registration_number, '67286')

    def test_exactly_one_professional_per_role(self):
        self.assertEqual(PublicWorkoutProfessional.objects.filter(role=PublicWorkoutProfessionalRole.TREINO).count(), 1)
        self.assertEqual(PublicWorkoutProfessional.objects.filter(role=PublicWorkoutProfessionalRole.NUTRICAO).count(), 1)


class PublicWorkoutNutritionProfileTests(TestCase):
    def test_one_profile_per_account(self):
        account = PublicWorkoutAccount.objects.create(email='aluno@example.com')
        PublicWorkoutNutritionProfile.objects.create(account=account, comorbidades='hipertensao')

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PublicWorkoutNutritionProfile.objects.create(account=account, comorbidades='outra')


class PublicWorkoutMealPlanTests(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='aluno@example.com')
        self.nutricionista = PublicWorkoutProfessional.objects.create(
            name='Nutricionista de teste', role=PublicWorkoutProfessionalRole.NUTRICAO,
            registration_council='CRN', registration_number='TESTE',
        )

    def _make_plan(self, *, version, is_active):
        return PublicWorkoutMealPlan.objects.create(
            account=self.account,
            version=version,
            is_active=is_active,
            authored_by=self.nutricionista,
            payload=build_example_payload(),
        )

    def test_same_account_cannot_have_two_plans_with_the_same_version(self):
        self._make_plan(version=1, is_active=False)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._make_plan(version=1, is_active=False)

    def test_same_account_cannot_have_two_active_plans(self):
        self._make_plan(version=1, is_active=True)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._make_plan(version=2, is_active=True)

    def test_different_accounts_can_each_have_an_active_plan(self):
        other_account = PublicWorkoutAccount.objects.create(email='outro@example.com')
        self._make_plan(version=1, is_active=True)

        plan = PublicWorkoutMealPlan.objects.create(
            account=other_account, version=1, is_active=True, authored_by=self.nutricionista,
            payload=build_example_payload(),
        )

        self.assertTrue(plan.is_active)

    def test_authored_by_professional_cannot_be_deleted_while_referenced(self):
        self._make_plan(version=1, is_active=True)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.nutricionista.delete()
