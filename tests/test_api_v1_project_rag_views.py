"""
ARQUIVO: testes dos endpoints da API v1 do RAG interno.

POR QUE ELE EXISTE:
- garante que a busca e a resposta aumentada fiquem acessiveis pela fronteira da API.
"""

import json
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from knowledge.models import KnowledgeChunk, KnowledgeDocument, KnowledgeSourceKind


class ApiV1ProjectRagViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='rag-owner', password='secret123')
        document = KnowledgeDocument.objects.create(
            path='README.md',
            title='OctoBox Control',
            source_kind=KnowledgeSourceKind.README,
            authority_score=95,
            checksum='readme',
            line_count=30,
        )
        KnowledgeChunk.objects.create(
            document=document,
            ordinal=1,
            heading='Current scope',
            content='OctoBox is an operational hub for boxes and gyms.',
            content_preview='OctoBox is an operational hub for boxes and gyms.',
            token_count=10,
            start_line=1,
            end_line=5,
            checksum='readme-1',
        )

    def test_project_rag_search_requires_authentication(self):
        response = self.client.get(reverse('api-v1-project-rag-search'), {'q': 'OctoBox'})

        self.assertEqual(response.status_code, 302)

    def test_project_rag_search_returns_ranked_results(self):
        self.client.login(username='rag-owner', password='secret123')

        response = self.client.get(reverse('api-v1-project-rag-search'), {'q': 'What is OctoBox?'})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['results'][0]['path'], 'README.md')

    def test_project_rag_answer_returns_citations(self):
        self.client.login(username='rag-owner', password='secret123')

        response = self.client.post(
            reverse('api-v1-project-rag-answer'),
            data=json.dumps({'question': 'What is OctoBox?'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['citations'][0]['path'], 'README.md')
        self.assertIn(payload['answer_mode'], {'extractive-fallback', 'openai-responses'})

    @patch('access.permissions.mixins.get_user_role')
    @patch('knowledge.views.get_alert_siren_defense_policy')
    @patch('knowledge.views.dispatch_async_job')
    @patch('knowledge.views.AsyncJob.objects.create')
    def test_project_rag_reindex_enqueues_async_job(
        self,
        async_job_create_mock,
        dispatch_async_job_mock,
        defense_policy_mock,
        get_user_role_mock,
    ):
        get_user_role_mock.return_value = SimpleNamespace(slug='DEV')
        defense_policy_mock.return_value = {
            'level': 'silent',
            'pause_non_essential_job_submissions': False,
        }
        async_job_create_mock.return_value = SimpleNamespace(id=77)
        dispatch_async_job_mock.return_value = SimpleNamespace(id='task-rag-77')
        self.client.login(username='rag-owner', password='secret123')

        response = self.client.post(
            reverse('api-v1-project-rag-reindex'),
            data=json.dumps({'force': True, 'with_embeddings': True}),
            content_type='application/json',
            HTTP_X_CORRELATION_ID='req-rag-1',
            HTTP_X_IDEMPOTENCY_KEY='idem-rag-1',
        )

        self.assertEqual(response.status_code, 202)
        payload = response.json()
        self.assertEqual(payload['job_id'], 77)
        self.assertTrue(payload['with_embeddings'])
        create_kwargs = async_job_create_mock.call_args.kwargs
        self.assertEqual(create_kwargs['job_type'], 'project_knowledge_reindex')
        self.assertEqual(
            create_kwargs['result']['dispatch_context']['payload'],
            {'force': True, 'with_embeddings': True},
        )
