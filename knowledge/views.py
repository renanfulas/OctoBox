"""
ARQUIVO: endpoints do RAG interno do projeto.

POR QUE ELE EXISTE:
- expõe a busca e a resposta aumentada sem misturar essa capacidade com views de dominio.

O QUE ESTE ARQUIVO FAZ:
1. publica health do indice.
2. publica busca hibrida por chunks.
3. publica resposta aumentada com citacoes.
"""

from __future__ import annotations

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.http import JsonResponse
from django.views import View

from access.permissions.mixins import RoleRequiredMixin
from access.roles import ROLE_DEV, ROLE_OWNER
from integrations.mesh import build_correlation_id, build_signal_envelope, resolve_idempotency_key
from jobs.dispatcher import build_dispatch_context, dispatch_async_job
from jobs.models import AsyncJob
from monitoring.alert_siren import get_alert_siren_defense_policy

from .generation import generate_project_answer
from .models import KnowledgeChunk, KnowledgeChunkEmbedding, KnowledgeDocument
from .retrieval import search_project_knowledge


class ProjectKnowledgeHealthView(View):
    def get(self, request, *args, **kwargs):
        active_documents = KnowledgeDocument.objects.filter(is_active=True)
        active_chunks = KnowledgeChunk.objects.filter(document__is_active=True)
        embedded_chunks = KnowledgeChunkEmbedding.objects.filter(chunk__document__is_active=True)
        return JsonResponse(
            {
                'status': 'ok',
                'documents': active_documents.count(),
                'chunks': active_chunks.count(),
                'embedded_chunks': embedded_chunks.count(),
                'embeddings_feature_enabled': bool(getattr(settings, 'PROJECT_RAG_EMBEDDINGS_ENABLED', False)),
            }
        )


class ProjectKnowledgeSearchView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        question = request.GET.get('q', '').strip()
        limit = _safe_limit(request.GET.get('limit'))
        hits = search_project_knowledge(question=question, limit=limit)
        return JsonResponse(
            {
                'question': question,
                'results': [
                    {
                        'path': hit.path,
                        'title': hit.title,
                        'heading': hit.heading,
                        'start_line': hit.start_line,
                        'end_line': hit.end_line,
                        'score': hit.score,
                        'authority_score': hit.authority_score,
                        'source_kind': hit.source_kind,
                        'reasons': hit.reasons,
                        'preview': hit.preview,
                    }
                    for hit in hits
                ],
            }
        )


class ProjectKnowledgeAnswerView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        payload = _read_json(request)
        question = str(payload.get('question', '')).strip()
        limit = _safe_limit(payload.get('limit'))
        hits = search_project_knowledge(question=question, limit=limit)
        answer = generate_project_answer(question=question, hits=hits)
        return JsonResponse(
            {
                'question': question,
                'answer': answer.answer,
                'answer_mode': answer.mode,
                'citations': answer.citations,
            }
        )


class ProjectKnowledgeReindexView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_DEV)

    def post(self, request, *args, **kwargs):
        correlation_id = build_correlation_id(
            request.headers.get('X-Correlation-ID') or request.headers.get('X-Request-ID') or ''
        )
        defense_policy = get_alert_siren_defense_policy()
        if defense_policy.get('pause_non_essential_job_submissions'):
            response = JsonResponse(
                {
                    'error': 'alert_siren_containment',
                    'message': 'Reindexacao do RAG foi temporariamente contida para proteger a operacao.',
                    'correlation_id': correlation_id,
                    'alert_siren_level': defense_policy.get('level', ''),
                },
                status=503,
            )
            response['X-OctoBox-Correlation-Id'] = correlation_id
            return response

        payload = _read_json(request)
        requested_with_embeddings = bool(payload.get('with_embeddings'))
        dispatch_payload = {
            'force': bool(payload.get('force')),
            'with_embeddings': requested_with_embeddings,
        }
        envelope = build_signal_envelope(
            correlation_id=correlation_id,
            idempotency_key=resolve_idempotency_key(
                explicit_key=request.headers.get('X-Idempotency-Key', ''),
            ),
            source_channel='api.v1.project_rag',
            raw_reference='project-knowledge-reindex',
        )
        dispatch_context = build_dispatch_context(
            job_type='project_knowledge_reindex',
            actor_id=request.user.id,
            signal_envelope=envelope.to_metadata(),
            payload=dispatch_payload,
        )
        job = AsyncJob.objects.create(
            job_type='project_knowledge_reindex',
            created_by_id=request.user.id,
            status='pending',
            result={
                'signal_envelope': envelope.to_metadata(),
                'dispatch_context': dispatch_context,
            },
        )
        task = dispatch_async_job(job=job, dispatch_context=dispatch_context)
        response = JsonResponse(
            {
                'status': 'accepted',
                'job_id': job.id,
                'task_id': getattr(task, 'id', ''),
                'correlation_id': correlation_id,
                'with_embeddings': dispatch_payload['with_embeddings'],
                'message': 'Reindexacao do conhecimento enfileirada com sucesso.',
            },
            status=202,
        )
        response['X-OctoBox-Correlation-Id'] = correlation_id
        return response


def _read_json(request) -> dict:
    try:
        return json.loads(request.body.decode('utf-8') or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _safe_limit(raw_limit) -> int:
    try:
        value = int(raw_limit or 5)
    except (TypeError, ValueError):
        value = 5
    return max(1, min(value, 10))
