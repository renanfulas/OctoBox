"""
ARQUIVO: testes de assessment_hero_ai.

POR QUE ELE EXISTE:
- prova que a geracao do comentario tecnico (hero da aba Avaliacoes) nunca
  quebra: sem chave, sem indicador, timeout e erro HTTP devem todos
  devolver `None`, nunca levantar excecao (mesmo espirito de
  test_weekly_review_ai.py).
- prova que `generate_and_store_hero_commentary` grava o texto no campo
  `hero_commentary` da avaliacao mais recente, e nunca na mais antiga.
"""

from datetime import date
from unittest import mock

import requests
from django.test import SimpleTestCase, TestCase

from public_workouts.assessment_hero_ai import generate_and_store_hero_commentary, generate_assessment_hero_text
from public_workouts.models import PublicWorkoutAssessment

_INDICATORS_WITH_DATA = {
    'bmi': {'value': 21.0, 'classification': {'label': 'Normal', 'level': 'good'}, 'delta': -1.1},
    'whr': {'value': 0.8, 'classification': {'label': 'Risco moderado', 'level': 'warning'}, 'delta': -0.05},
    'body_fat_percent': {'value': 21.6, 'source': 'skinfold_jp7', 'classification': {'label': 'Fitness', 'level': 'good'}, 'delta': -2.1},
}

_INDICATORS_EMPTY = {'bmi': None, 'whr': None, 'body_fat_percent': None}


def _mock_response(*, status_code=200, content_blocks=None):
    response = mock.Mock()
    response.status_code = status_code
    response.raise_for_status = mock.Mock()
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(f'HTTP {status_code}')
    response.json.return_value = {'content': content_blocks or []}
    return response


class GenerateAssessmentHeroTextTests(SimpleTestCase):
    def test_returns_none_without_indicators(self):
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            self.assertIsNone(generate_assessment_hero_text(_INDICATORS_EMPTY))

    def test_returns_none_without_api_key(self):
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': ''}):
            self.assertIsNone(generate_assessment_hero_text(_INDICATORS_WITH_DATA))

    def test_returns_text_on_success(self):
        response = _mock_response(content_blocks=[{'type': 'text', 'text': 'Sua avaliacao esta boa.'}])
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            with mock.patch('public_workouts.assessment_hero_ai.requests.post', return_value=response) as post:
                text = generate_assessment_hero_text(_INDICATORS_WITH_DATA)

        self.assertEqual(text, 'Sua avaliacao esta boa.')
        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs['json']['model'], 'claude-haiku-4-5-20251001')

    def test_returns_none_on_timeout(self):
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            with mock.patch('public_workouts.assessment_hero_ai.requests.post', side_effect=requests.Timeout):
                self.assertIsNone(generate_assessment_hero_text(_INDICATORS_WITH_DATA))

    def test_returns_none_on_http_error(self):
        response = _mock_response(status_code=500)
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            with mock.patch('public_workouts.assessment_hero_ai.requests.post', return_value=response):
                self.assertIsNone(generate_assessment_hero_text(_INDICATORS_WITH_DATA))

    def test_returns_none_on_empty_response_text(self):
        response = _mock_response(content_blocks=[])
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            with mock.patch('public_workouts.assessment_hero_ai.requests.post', return_value=response):
                self.assertIsNone(generate_assessment_hero_text(_INDICATORS_WITH_DATA))

    def test_includes_workspace_header_when_configured(self):
        response = _mock_response(content_blocks=[{'type': 'text', 'text': 'ok'}])
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test', 'ANTHROPIC_WORKSPACE_ID': 'wrkspc_test'}):
            with mock.patch('public_workouts.assessment_hero_ai.requests.post', return_value=response) as post:
                generate_assessment_hero_text(_INDICATORS_WITH_DATA)
        self.assertEqual(post.call_args.kwargs['headers']['anthropic-workspace-id'], 'wrkspc_test')

    def test_omits_workspace_header_when_not_configured(self):
        response = _mock_response(content_blocks=[{'type': 'text', 'text': 'ok'}])
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test', 'ANTHROPIC_WORKSPACE_ID': ''}):
            with mock.patch('public_workouts.assessment_hero_ai.requests.post', return_value=response) as post:
                generate_assessment_hero_text(_INDICATORS_WITH_DATA)
        self.assertNotIn('anthropic-workspace-id', post.call_args.kwargs['headers'])


class GenerateAndStoreHeroCommentaryTests(TestCase):
    def test_stores_generated_text_on_latest_assessment_only(self):
        first = PublicWorkoutAssessment.objects.create(
            plan_slug='herotest', measured_at=date(2026, 9, 1), weight_kg=66, measurements={'cintura': 83, 'quadril': 98}
        )
        latest = PublicWorkoutAssessment.objects.create(
            plan_slug='herotest', measured_at=date(2026, 9, 28), weight_kg=63, measurements={'cintura': 79, 'quadril': 99}
        )

        response = _mock_response(content_blocks=[{'type': 'text', 'text': 'Comentario tecnico.'}])
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            with mock.patch('public_workouts.assessment_hero_ai.requests.post', return_value=response):
                result = generate_and_store_hero_commentary(plan_slug='herotest', sex='female', height_cm=170)

        self.assertEqual(result, 'Comentario tecnico.')
        first.refresh_from_db()
        latest.refresh_from_db()
        self.assertIsNone(first.hero_commentary)
        self.assertEqual(latest.hero_commentary, 'Comentario tecnico.')

    def test_returns_none_when_no_assessments(self):
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            result = generate_and_store_hero_commentary(plan_slug='ghost-plan', sex='female', height_cm=170)
        self.assertIsNone(result)
