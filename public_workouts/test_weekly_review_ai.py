"""
ARQUIVO: testes de weekly_review_ai.generate_weekly_review_text.

POR QUE ELE EXISTE:
- prova que a chamada de IA da revisao semanal (Entrega 4) nunca quebra a
  tela: sem chave, sem sinal, timeout e erro HTTP devem todos devolver
  `None`, nunca levantar excecao.
"""

from unittest import mock

import requests
from django.test import SimpleTestCase

from public_workouts.weekly_review_ai import generate_weekly_review_text

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
