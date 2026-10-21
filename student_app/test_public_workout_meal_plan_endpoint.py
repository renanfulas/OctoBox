"""
ARQUIVO: testes de GET /renan/<slug>/nutricao.json (Entrega 6, Fase 4 —
docs/plans/public-workouts-escala-e-nutricao-corda.md, D.4/D.6).

POR QUE ELE EXISTE:
- mesma regra de auth dos demais endpoints de conta (pacote.json,
  revisao-semanal): sessao de LOGIN ativa, 401 sem sessao, 404 se a
  sessao nao e' dona deste slug. Alem disso, o gate de tier (D.4): so'
  Completo/Premium tem acesso — Essencial (ou sem assinatura nenhuma)
  recebe 404, nunca 403 (403 confirmaria que existe conteudo de nutricao
  pra aquela conta).
"""

from django.test import TestCase
from django.urls import reverse

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutProfessional, PublicWorkoutProfessionalRole, PublicWorkoutSubscription, PublicWorkoutTier
from public_workouts.services import publish_meal_plan
from public_workouts.nutrition_schema import build_example_payload
from student_identity.public_workout_session import (
    PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
    build_public_workout_session_value,
)


def _make_account_with_subscription(*, email, plan_slug, tier=PublicWorkoutTier.COMPLETO) -> PublicWorkoutAccount:
    account = PublicWorkoutAccount.objects.create(email=email)
    PublicWorkoutSubscription.objects.create(account=account, plan_slug=plan_slug, tier=tier)
    return account


def _login(client, account_id):
    client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(account_id=account_id)


def _make_nutritionist() -> PublicWorkoutProfessional:
    return PublicWorkoutProfessional.objects.create(
        name='Nutricionista de teste',
        role=PublicWorkoutProfessionalRole.NUTRICAO,
        registration_council='CRN',
        registration_number='TESTE-ENDPOINT',
    )


class PublicWorkoutMealPlanEndpointTests(TestCase):
    def _url(self, slug='bruno'):
        return reverse('public-workout-meal-plan', kwargs={'plan_slug': slug})

    def test_without_session_returns_401(self):
        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 401)

    def test_session_of_another_slugs_owner_returns_404(self):
        account = _make_account_with_subscription(email='a@example.com', plan_slug='juliana')
        _login(self.client, account.pk)

        response = self.client.get(self._url('bruno'))

        self.assertEqual(response.status_code, 404)

    def test_essencial_tier_returns_404_never_403(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno', tier=PublicWorkoutTier.ESSENCIAL)
        _login(self.client, account.pk)

        response = self.client.get(self._url('bruno'))

        self.assertEqual(response.status_code, 404)

    def test_account_without_any_subscription_returns_404(self):
        account = PublicWorkoutAccount.objects.create(email='semassinatura@example.com')
        _login(self.client, account.pk)

        response = self.client.get(self._url('bruno'))

        self.assertEqual(response.status_code, 404)

    def test_completo_tier_with_no_plan_published_yet_gets_null(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno', tier=PublicWorkoutTier.COMPLETO)
        _login(self.client, account.pk)

        response = self.client.get(self._url('bruno'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'meal_plan': None})

    def test_completo_tier_gets_the_active_meal_plan_payload(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno', tier=PublicWorkoutTier.COMPLETO)
        nutricionista = _make_nutritionist()
        payload = build_example_payload()
        publish_meal_plan(account_id=account.pk, payload=payload, authored_by=nutricionista)
        _login(self.client, account.pk)

        response = self.client.get(self._url('bruno'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['meal_plan'], payload)

    def test_premium_tier_also_has_access(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno', tier=PublicWorkoutTier.PREMIUM)
        _login(self.client, account.pk)

        response = self.client.get(self._url('bruno'))

        self.assertEqual(response.status_code, 200)

    def test_does_not_leak_meal_plan_between_accounts(self):
        owner = _make_account_with_subscription(email='dono@example.com', plan_slug='bruno')
        other = _make_account_with_subscription(email='outro@example.com', plan_slug='juliana')
        nutricionista = _make_nutritionist()
        publish_meal_plan(account_id=owner.pk, payload=build_example_payload(), authored_by=nutricionista)
        _login(self.client, other.pk)

        response = self.client.get(self._url('juliana'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'meal_plan': None})

    def test_is_read_only_post_not_allowed(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(self._url('bruno'))

        self.assertEqual(response.status_code, 405)
