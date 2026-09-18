"""
ARQUIVO: testes do admin de PublicWorkoutMealPlan (Entrega 6, Fase 4 —
docs/plans/public-workouts-escala-e-nutricao-corda.md, D.6).

POR QUE ELE EXISTE:
- e' o item de maior incerteza de esforco da Fase 4 (proprio plano):
  formulario aceita o payload como JSON estruturado (nao um formset por
  refeicao/item) mas precisa continuar rejeitando payload malformado —
  e nunca pode permitir UPDATE de uma versao ja publicada (D.6).
"""

import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutMealPlan,
    PublicWorkoutProfessional,
    PublicWorkoutProfessionalRole,
)
from public_workouts.nutrition_schema import build_example_payload
from public_workouts.services import publish_meal_plan


class PublicWorkoutMealPlanAdminTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            username='admin', email='admin@example.com', password='senha-forte-123',
        )
        self.client.force_login(self.superuser)
        self.account = PublicWorkoutAccount.objects.create(email='aluno@example.com')
        self.nutricionista = PublicWorkoutProfessional.objects.get(role=PublicWorkoutProfessionalRole.NUTRICAO)

    def _add_url(self):
        return reverse('admin:public_workouts_publicworkoutmealplan_add')

    def test_changelist_loads_and_lists_published_plans(self):
        publish_meal_plan(account_id=self.account.pk, payload=build_example_payload(), authored_by=self.nutricionista)

        response = self.client.get(reverse('admin:public_workouts_publicworkoutmealplan_changelist'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aluno@example.com')

    def test_valid_payload_publishes_version_1_active(self):
        response = self.client.post(self._add_url(), data={
            'account': self.account.pk,
            'authored_by': self.nutricionista.pk,
            'payload': json.dumps(build_example_payload()),
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        plan = PublicWorkoutMealPlan.objects.get(account=self.account)
        self.assertEqual(plan.version, 1)
        self.assertTrue(plan.is_active)

    def test_second_valid_submission_creates_version_2_not_an_update(self):
        publish_meal_plan(account_id=self.account.pk, payload=build_example_payload(), authored_by=self.nutricionista)

        self.client.post(self._add_url(), data={
            'account': self.account.pk,
            'authored_by': self.nutricionista.pk,
            'payload': json.dumps(build_example_payload()),
        }, follow=True)

        self.assertEqual(PublicWorkoutMealPlan.objects.filter(account=self.account).count(), 2)
        self.assertEqual(PublicWorkoutMealPlan.objects.filter(account=self.account, is_active=True).count(), 1)

    def test_invalid_json_is_rejected_without_creating_a_row(self):
        response = self.client.post(self._add_url(), data={
            'account': self.account.pk,
            'authored_by': self.nutricionista.pk,
            'payload': '{nao e json valido',
        })

        self.assertEqual(response.status_code, 200)  # form re-renderizado com erro, nunca 500
        self.assertContains(response, 'JSON invalido')
        self.assertEqual(PublicWorkoutMealPlan.objects.count(), 0)

    def test_schema_invalid_payload_is_rejected_without_creating_a_row(self):
        payload = build_example_payload()
        del payload['daily_targets']

        response = self.client.post(self._add_url(), data={
            'account': self.account.pk,
            'authored_by': self.nutricionista.pk,
            'payload': json.dumps(payload),
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(PublicWorkoutMealPlan.objects.count(), 0)

    def test_authored_by_choices_are_restricted_to_nutrition_professionals(self):
        treino = PublicWorkoutProfessional.objects.get(role=PublicWorkoutProfessionalRole.TREINO)

        response = self.client.post(self._add_url(), data={
            'account': self.account.pk,
            'authored_by': treino.pk,
            'payload': json.dumps(build_example_payload()),
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(PublicWorkoutMealPlan.objects.count(), 0)

    def test_existing_plan_cannot_be_edited(self):
        plan = publish_meal_plan(account_id=self.account.pk, payload=build_example_payload(), authored_by=self.nutricionista)

        response = self.client.get(reverse('admin:public_workouts_publicworkoutmealplan_change', args=[plan.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<input type="submit" name="_save"')
