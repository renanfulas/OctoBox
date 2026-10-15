"""
ARQUIVO: testes de GET /renan/<slug>/revisao-semanal (Entrega 4,
docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- mesma regra de auth dos demais endpoints de conta (pacote.json, carga):
  sessao de LOGIN ativa, 401 sem sessao, 404 se a sessao nao e' dona deste
  slug. `review_text` precisa vir `null` sem ANTHROPIC_API_KEY configurada
  — o endpoint nunca pode devolver 500 por causa da IA estar fora do ar.
"""

import json
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutSubscription
from student_identity.public_workout_session import (
    PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
    build_public_workout_session_value,
)


def _make_account_with_subscription(*, email, plan_slug) -> PublicWorkoutAccount:
    account = PublicWorkoutAccount.objects.create(email=email)
    PublicWorkoutSubscription.objects.create(account=account, plan_slug=plan_slug)
    return account


def _login(client, account_id):
    client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(account_id=account_id)


class PublicWorkoutWeeklyReviewEndpointTests(TestCase):
    def _url(self, slug='bruno'):
        return reverse('public-workout-weekly-review', kwargs={'plan_slug': slug})

    def test_without_session_returns_401(self):
        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 401)

    def test_session_of_another_slugs_owner_returns_404(self):
        account = _make_account_with_subscription(email='a@example.com', plan_slug='juliana')
        _login(self.client, account.pk)

        response = self.client.get(self._url('bruno'))

        self.assertEqual(response.status_code, 404)

    def test_unknown_slug_returns_404(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.get(self._url('nao-existe'))

        self.assertEqual(response.status_code, 404)

    def test_owner_without_anthropic_key_gets_null_review_text(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': ''}):
            response = self.client.get(self._url('bruno'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'review_text': None})

    def test_owner_with_no_load_yet_also_gets_null_review_text(self):
        # Sem PublicWorkoutLoadLog nenhum, trends_by_movement fica vazio —
        # generate_weekly_review_text nunca chega a chamar a Anthropic.
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            with mock.patch('public_workouts.weekly_review_ai.requests.post') as post:
                response = self.client.get(self._url('bruno'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'review_text': None})
        post.assert_not_called()

    def test_second_request_same_week_reuses_cache_never_calls_anthropic_again(self):
        # achado do Renan (Haiku no resumo da Início): a Início busca este
        # MESMO endpoint automaticamente a cada carregamento -- sem cache
        # semanal, isso chamaria a Anthropic em toda visita.
        from public_workouts.models import PublicWorkoutLoadLog, PublicWorkoutLoadLogSetRole
        from datetime import date, timedelta
        from decimal import Decimal

        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)
        for offset, weight in ((14, 100), (7, 95), (0, 90)):
            PublicWorkoutLoadLog.objects.create(
                account=account, movement_slug='squat', weight_kg=Decimal(str(weight)), reps=5,
                performed_on=date.today() - timedelta(days=offset), set_role=PublicWorkoutLoadLogSetRole.TOP_SET,
                idempotency_key=f'weekly-review-cache-{offset}',
            )

        response_mock = mock.Mock()
        response_mock.raise_for_status = mock.Mock()
        response_mock.json.return_value = {'content': [{'type': 'text', 'text': 'Sua carga caiu essa semana.'}]}

        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            with mock.patch('public_workouts.weekly_review_ai.requests.post', return_value=response_mock) as post:
                first = self.client.get(self._url('bruno'))
                second = self.client.get(self._url('bruno'))

        self.assertEqual(first.json(), {'review_text': 'Sua carga caiu essa semana.'})
        self.assertEqual(second.json(), {'review_text': 'Sua carga caiu essa semana.'})
        post.assert_called_once()

    def test_is_read_only_post_not_allowed(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(self._url('bruno'), data=json.dumps({}), content_type='application/json')

        self.assertEqual(response.status_code, 405)
