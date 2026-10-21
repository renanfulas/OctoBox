"""
ARQUIVO: testes de weekly_review_ai.generate_weekly_review_text e do cache
semanal (get_or_create_cached_review_text) que o card automatico da
Início e o botao manual da Cargas compartilham.

POR QUE ELE EXISTE:
- prova que a chamada de IA da revisao semanal (Entrega 4) nunca quebra a
  tela: sem chave, sem sinal, timeout e erro HTTP devem todos devolver
  `None`, nunca levantar excecao.
- prova a garantia central do cache (achado do Renan: Haiku no resumo da
  Início): NO MAXIMO 1 chamada a IA por conta por semana ISO, mesmo que a
  Início e o botao da Cargas cheguem na mesma semana.
"""

from unittest import mock

import requests
from django.db import IntegrityError
from django.test import SimpleTestCase, TestCase

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutWeeklyReviewCache
from public_workouts.weekly_review_ai import generate_weekly_review_text, get_or_create_cached_review_text

_REVIEW_WITH_TRENDS = {
    'trends_by_movement': {'agachamento-livre': {'label': 'declining', 'weekly_estimates_kg': [100.0, 95.0]}},
    'declining_movements': ['agachamento-livre'],
    'plateaued_movements': [],
}

_REVIEW_EMPTY = {'trends_by_movement': {}, 'declining_movements': [], 'plateaued_movements': []}


def _mock_response(*, status_code=200, content_blocks=None):
    response = mock.Mock()
    response.status_code = status_code
    response.raise_for_status = mock.Mock()
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(f'HTTP {status_code}')
    response.json.return_value = {'content': content_blocks or []}
    return response


class GenerateWeeklyReviewTextTests(SimpleTestCase):
    def test_returns_none_without_trends(self):
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            self.assertIsNone(generate_weekly_review_text(_REVIEW_EMPTY))

    def test_returns_none_without_api_key(self):
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': ''}):
            self.assertIsNone(generate_weekly_review_text(_REVIEW_WITH_TRENDS))

    def test_returns_text_on_success(self):
        response = _mock_response(content_blocks=[{'type': 'text', 'text': 'Seu agachamento caiu 5% essa semana.'}])
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            with mock.patch('public_workouts.weekly_review_ai.requests.post', return_value=response) as post:
                text = generate_weekly_review_text(_REVIEW_WITH_TRENDS)

        self.assertEqual(text, 'Seu agachamento caiu 5% essa semana.')
        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs['json']['model'], 'claude-haiku-4-5-20251001')

    def test_returns_none_on_timeout(self):
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            with mock.patch('public_workouts.weekly_review_ai.requests.post', side_effect=requests.Timeout):
                self.assertIsNone(generate_weekly_review_text(_REVIEW_WITH_TRENDS))

    def test_returns_none_on_http_error(self):
        response = _mock_response(status_code=500)
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            with mock.patch('public_workouts.weekly_review_ai.requests.post', return_value=response):
                self.assertIsNone(generate_weekly_review_text(_REVIEW_WITH_TRENDS))

    def test_returns_none_on_empty_response_text(self):
        response = _mock_response(content_blocks=[])
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            with mock.patch('public_workouts.weekly_review_ai.requests.post', return_value=response):
                self.assertIsNone(generate_weekly_review_text(_REVIEW_WITH_TRENDS))


class GetOrCreateCachedReviewTextTests(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='cache@example.com')

    def test_first_call_generates_and_persists_a_cache_row(self):
        with mock.patch(
            'public_workouts.weekly_review_ai.generate_weekly_review_text',
            return_value='Você evoluiu bem essa semana.',
        ) as generate:
            text = get_or_create_cached_review_text(account_id=self.account.pk, review=_REVIEW_WITH_TRENDS)

        self.assertEqual(text, 'Você evoluiu bem essa semana.')
        generate.assert_called_once()
        self.assertEqual(PublicWorkoutWeeklyReviewCache.objects.filter(account=self.account).count(), 1)

    def test_second_call_same_week_never_calls_ai_again(self):
        with mock.patch(
            'public_workouts.weekly_review_ai.generate_weekly_review_text',
            return_value='Texto da semana.',
        ) as generate:
            first = get_or_create_cached_review_text(account_id=self.account.pk, review=_REVIEW_WITH_TRENDS)
            second = get_or_create_cached_review_text(account_id=self.account.pk, review=_REVIEW_WITH_TRENDS)

        self.assertEqual(first, second)
        generate.assert_called_once()

    def test_none_result_is_cached_too_and_never_retried_the_same_week(self):
        # sem sinal/sem chave/erro -- generate_weekly_review_text ja devolve
        # None; isso e' um resultado CACHEADO valido, nao "ainda nao tentou".
        with mock.patch(
            'public_workouts.weekly_review_ai.generate_weekly_review_text', return_value=None,
        ) as generate:
            first = get_or_create_cached_review_text(account_id=self.account.pk, review=_REVIEW_EMPTY)
            second = get_or_create_cached_review_text(account_id=self.account.pk, review=_REVIEW_EMPTY)

        self.assertIsNone(first)
        self.assertIsNone(second)
        generate.assert_called_once()
        self.assertTrue(PublicWorkoutWeeklyReviewCache.objects.filter(account=self.account).exists())

    def test_different_accounts_get_independent_cache_entries(self):
        other_account = PublicWorkoutAccount.objects.create(email='cache-outro@example.com')
        with mock.patch(
            'public_workouts.weekly_review_ai.generate_weekly_review_text', return_value='Texto.',
        ) as generate:
            get_or_create_cached_review_text(account_id=self.account.pk, review=_REVIEW_WITH_TRENDS)
            get_or_create_cached_review_text(account_id=other_account.pk, review=_REVIEW_WITH_TRENDS)

        self.assertEqual(generate.call_count, 2)
        self.assertEqual(PublicWorkoutWeeklyReviewCache.objects.count(), 2)

    def test_concurrent_first_call_falls_back_to_the_row_the_other_request_won(self):
        # Corrida rara: dois requests da mesma conta/semana passam pelo
        # filter() (nenhum cache ainda) antes de qualquer um commitar o
        # create() -- esta chamada so' descobre a corrida quando o PROPRIO
        # create() esbarra na unique constraint (a "outra request" e'
        # simulada gravando a linha vencedora DENTRO do side_effect, depois
        # do filter() desta chamada ja ter rodado vazio).
        real_create = PublicWorkoutWeeklyReviewCache.objects.create

        def _other_request_wins_the_race(**kwargs):
            real_create(
                account_id=kwargs['account_id'], iso_week=kwargs['iso_week'],
                review_text='Quem ganhou a corrida escreveu isto.',
            )
            raise IntegrityError

        with mock.patch(
            'public_workouts.weekly_review_ai.generate_weekly_review_text', return_value='Texto perdedor da corrida.',
        ) as generate:
            with mock.patch.object(
                PublicWorkoutWeeklyReviewCache.objects, 'create', side_effect=_other_request_wins_the_race,
            ):
                text = get_or_create_cached_review_text(account_id=self.account.pk, review=_REVIEW_WITH_TRENDS)

        self.assertEqual(text, 'Quem ganhou a corrida escreveu isto.')
        generate.assert_called_once()
        self.assertEqual(PublicWorkoutWeeklyReviewCache.objects.filter(account=self.account).count(), 1)
