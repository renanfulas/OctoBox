"""
ARQUIVO: testes do motor de retrieval do RAG interno.

POR QUE ELE EXISTE:
- protege o ranking hibrido por autoridade e sobreposicao lexical.
"""

import os
from unittest import mock
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from knowledge.models import KnowledgeChunk, KnowledgeChunkEmbedding, KnowledgeDocument, KnowledgeSourceKind
from knowledge.retrieval import search_project_knowledge
from knowledge.schema_access import _normalize_schema, force_utf8_io
from knowledge.vector_math import pack_vector, vector_norm


class KnowledgeRetrievalTests(TestCase):
    def setUp(self):
        architecture_document = KnowledgeDocument.objects.create(
            path='docs/architecture/octobox-architecture-model.md',
            title='OctoBox Architecture Model',
            source_kind=KnowledgeSourceKind.DOC,
            authority_score=90,
            checksum='arch',
            line_count=20,
        )
        guide_document = KnowledgeDocument.objects.create(
            path='docs/experience/css-guide.md',
            title='CSS Guide',
            source_kind=KnowledgeSourceKind.DOC,
            authority_score=70,
            checksum='css',
            line_count=20,
        )
        KnowledgeChunk.objects.create(
            document=architecture_document,
            ordinal=1,
            heading='Center Layer',
            content='The Center Layer is the official hallway for each capability of the OctoBox architecture.',
            content_preview='The Center Layer is the official hallway for each capability of the OctoBox architecture.',
            token_count=12,
            start_line=10,
            end_line=20,
            checksum='arch-1',
        )
        KnowledgeChunk.objects.create(
            document=guide_document,
            ordinal=1,
            heading='CSS ownership',
            content='The CSS guide explains how ownership and tokens should be organized in the frontend.',
            content_preview='The CSS guide explains how ownership and tokens should be organized in the frontend.',
            token_count=12,
            start_line=1,
            end_line=10,
            checksum='css-1',
        )

    def test_architecture_question_prefers_architecture_document(self):
        hits = search_project_knowledge(question='What is the Center Layer in the architecture?', limit=2)

        self.assertEqual(len(hits), 2)
        self.assertEqual(hits[0].path, 'docs/architecture/octobox-architecture-model.md')
        self.assertGreater(hits[0].score, hits[1].score)

    def test_frontend_query_returns_css_guide_hit(self):
        hits = search_project_knowledge(question='How should CSS ownership work in the frontend?', limit=2)

        self.assertEqual(hits[0].path, 'docs/experience/css-guide.md')
        self.assertIn('frontend', hits[0].preview.lower())

    @patch('knowledge.retrieval.get_embedding_client')
    def test_semantic_query_can_surface_non_lexical_match_when_embeddings_are_enabled(self, client_mock):
        semantic_document = KnowledgeDocument.objects.create(
            path='docs/architecture/center-layer.md',
            title='Center Layer',
            source_kind=KnowledgeSourceKind.DOC,
            authority_score=91,
            checksum='center',
            line_count=20,
        )
        semantic_chunk = KnowledgeChunk.objects.create(
            document=semantic_document,
            ordinal=1,
            heading='Tese central',
            content='The official hallway between external access and the internal core is the Center Layer.',
            content_preview='The official hallway between external access and the internal core is the Center Layer.',
            token_count=14,
            start_line=1,
            end_line=6,
            checksum='center-1',
        )
        KnowledgeChunkEmbedding.objects.create(
            chunk=semantic_chunk,
            model='text-embedding-3-small',
            dimensions=3,
            checksum=semantic_chunk.checksum,
            vector=pack_vector([1.0, 0.0, 0.0]),
            norm=vector_norm([1.0, 0.0, 0.0]),
            generated_at=semantic_chunk.created_at,
        )
        client = client_mock.return_value
        client.is_enabled.return_value = True
        client.embed_texts.return_value.vectors = [[1.0, 0.0, 0.0]]
        client.embed_texts.return_value.model = 'text-embedding-3-small'
        client.embed_texts.return_value.dimensions = 3

        hits = search_project_knowledge(question='What is the official hallway between access and core?', limit=3)

        self.assertEqual(hits[0].path, 'docs/architecture/center-layer.md')
        self.assertGreater(hits[0].semantic_score, 0.9)


class KnowledgeSchemaResolutionTests(SimpleTestCase):
    """Contrato de resolucao de schema do RAG tenant (sem banco)."""

    def test_explicit_schema_wins_over_box(self):
        self.assertEqual(_normalize_schema('box_alpha', 'beta'), 'box_alpha')

    def test_box_slug_gets_prefix(self):
        self.assertEqual(_normalize_schema(None, 'ragprobe'), 'box_ragprobe')

    def test_box_already_prefixed_is_kept(self):
        self.assertEqual(_normalize_schema(None, 'box_ragprobe'), 'box_ragprobe')

    def test_env_var_used_when_nothing_explicit(self):
        with mock.patch.dict(os.environ, {'OCTOBOX_KNOWLEDGE_SCHEMA': 'box_envbox'}, clear=False):
            self.assertEqual(_normalize_schema(None, None), 'box_envbox')

    def test_none_when_no_signal(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(_normalize_schema(None, None))

    def test_force_utf8_io_is_safe_to_call(self):
        force_utf8_io()  # nao deve levantar mesmo se o stream nao suportar reconfigure
