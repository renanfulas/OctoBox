"""
ARQUIVO: testes de program_generation_ai.generate_program_draft_payload.

POR QUE ELE EXISTE:
- mesmo espirito de test_weekly_review_ai.py: prova que TODA falha (sem
  chave, timeout, erro HTTP, JSON invalido, payload que nao passa no
  schema) devolve `(None, model)`, nunca levanta excecao — o fallback e'
  literalmente o status quo (Renan monta o programa a mao).
- prova especificamente os overrides deterministicos (schema_version,
  started_on): o modulo NUNCA confia no LLM pra esses campos, mesmo que o
  prompt peca pra ele preencher algo.
"""

import json
from datetime import date
from unittest import mock

import requests
from django.test import SimpleTestCase

from public_workouts.program_generation_ai import generate_program_draft_payload
from public_workouts.schema import build_example_payload

_TRAINING_PROFILE = {
    'goal': 'hypertrophy',
    'physical_restrictions': ['joelho'],
    'physical_restrictions_detail': 'dor leve',
    'training_experience': 'less_than_6_months',
    'days_per_week': 3,
    'training_location': 'full_gym',
    'motivation': 'quero mudar',
    'biggest_difficulty': 'consistencia',
}


def _mock_response(*, status_code=200, content_blocks=None):
    response = mock.Mock()
    response.status_code = status_code
    response.raise_for_status = mock.Mock()
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(f'HTTP {status_code}')
    response.json.return_value = {'content': content_blocks or []}
    return response


def _valid_payload_text() -> str:
    payload = build_example_payload()
    # program_id/started_on/schema_version propositalmente "errados" — o
    # modulo deve sobrescrever, nunca confiar no que o LLM mandou aqui.
    payload['schema_version'] = 999
    payload['started_on'] = '2000-01-01'
    return json.dumps(payload)


class GenerateProgramDraftPayloadTests(SimpleTestCase):
    def test_returns_none_without_api_key(self):
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': ''}):
            payload, model = generate_program_draft_payload(
                training_profile=_TRAINING_PROFILE, tier='completo', plan_slug='bruno'
            )
        self.assertIsNone(payload)
        self.assertEqual(model, 'claude-haiku-4-5-20251001')

    def test_returns_none_on_timeout(self):
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            with mock.patch('public_workouts.program_generation_ai.requests.post', side_effect=requests.Timeout):
                payload, _model = generate_program_draft_payload(
                    training_profile=_TRAINING_PROFILE, tier='completo', plan_slug='bruno'
                )
        self.assertIsNone(payload)

    def test_returns_none_on_http_error(self):
        response = _mock_response(status_code=500)
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            with mock.patch('public_workouts.program_generation_ai.requests.post', return_value=response):
                payload, _model = generate_program_draft_payload(
                    training_profile=_TRAINING_PROFILE, tier='completo', plan_slug='bruno'
                )
        self.assertIsNone(payload)

    def test_returns_none_on_empty_response_text(self):
        response = _mock_response(content_blocks=[])
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            with mock.patch('public_workouts.program_generation_ai.requests.post', return_value=response):
                payload, _model = generate_program_draft_payload(
                    training_profile=_TRAINING_PROFILE, tier='completo', plan_slug='bruno'
                )
        self.assertIsNone(payload)

    def test_returns_none_on_malformed_json(self):
        response = _mock_response(content_blocks=[{'type': 'text', 'text': 'isso nao e json { de jeito nenhum'}])
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            with mock.patch('public_workouts.program_generation_ai.requests.post', return_value=response):
                payload, _model = generate_program_draft_payload(
                    training_profile=_TRAINING_PROFILE, tier='completo', plan_slug='bruno'
                )
        self.assertIsNone(payload)

    def test_returns_none_on_schema_invalid_payload(self):
        broken = build_example_payload()
        del broken['days']
        response = _mock_response(content_blocks=[{'type': 'text', 'text': json.dumps(broken)}])
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            with mock.patch('public_workouts.program_generation_ai.requests.post', return_value=response):
                payload, _model = generate_program_draft_payload(
                    training_profile=_TRAINING_PROFILE, tier='completo', plan_slug='bruno'
                )
        self.assertIsNone(payload)

    def test_success_overrides_schema_version_and_started_on_deterministically(self):
        response = _mock_response(content_blocks=[{'type': 'text', 'text': _valid_payload_text()}])
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            with mock.patch(
                'public_workouts.program_generation_ai.requests.post', return_value=response
            ) as post:
                payload, model = generate_program_draft_payload(
                    training_profile=_TRAINING_PROFILE, tier='completo', plan_slug='bruno'
                )

        self.assertIsNotNone(payload)
        self.assertEqual(payload['schema_version'], 1)
        self.assertEqual(payload['started_on'], date.today().isoformat())
        self.assertEqual(model, 'claude-haiku-4-5-20251001')
        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs['json']['model'], 'claude-haiku-4-5-20251001')

    def test_success_tolerates_markdown_fences_around_json(self):
        fenced = f'```json\n{_valid_payload_text()}\n```'
        response = _mock_response(content_blocks=[{'type': 'text', 'text': fenced}])
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            with mock.patch('public_workouts.program_generation_ai.requests.post', return_value=response):
                payload, _model = generate_program_draft_payload(
                    training_profile=_TRAINING_PROFILE, tier='completo', plan_slug='bruno'
                )
        self.assertIsNotNone(payload)

    def test_movement_catalog_block_carries_cache_control(self):
        response = _mock_response(content_blocks=[{'type': 'text', 'text': _valid_payload_text()}])
        with mock.patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            with mock.patch(
                'public_workouts.program_generation_ai.requests.post', return_value=response
            ) as post:
                generate_program_draft_payload(
                    training_profile=_TRAINING_PROFILE,
                    tier='completo',
                    plan_slug='bruno',
                    known_movement_slugs=['agachamento-livre'],
                )

        system_blocks = post.call_args.kwargs['json']['system']
        self.assertEqual(len(system_blocks), 2)
        self.assertIn('cache_control', system_blocks[1])
