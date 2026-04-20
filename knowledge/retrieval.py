"""
ARQUIVO: motor de retrieval hibrido do conhecimento interno.

POR QUE ELE EXISTE:
- entrega recuperacao inteligente sem acoplamento prematuro a vector store externa.
- combina autoridade documental, sobreposicao lexical e pistas de caminho.

O QUE ESTE ARQUIVO FAZ:
1. normaliza consultas.
2. calcula score explainable por chunk.
3. retorna citacoes ordenadas com base e motivo.

PONTOS CRITICOS:
- este motor e um MVP lexical+authority; embeddings podem entrar depois se o corpus pedir.
- manter explainability agora evita um "oraculo magico" dificil de debugar depois.
"""

from __future__ import annotations

import heapq
import re
from dataclasses import dataclass

from django.conf import settings

from .embeddings import get_embedding_client
from .models import KnowledgeChunk, KnowledgeChunkEmbedding
from .vector_math import cosine_similarity


TOKEN_RE = re.compile(r"[a-z0-9_]{2,}", re.IGNORECASE)
STOPWORDS = {
    'a', 'o', 'e', 'de', 'da', 'do', 'das', 'dos', 'para', 'por', 'com', 'sem', 'um', 'uma', 'as', 'os',
    'no', 'na', 'nos', 'nas', 'que', 'como', 'qual', 'quais', 'onde', 'when', 'what', 'how', 'the', 'and',
    'for', 'from', 'into', 'this', 'that', 'your', 'you', 'can', 'does', 'did', 'sobre', 'projeto',
}
INTENT_BOOSTS = {
    'architecture': ('docs/architecture/', 'docs/guides/', 'docs/reference/'),
    'arquitetura': ('docs/architecture/', 'docs/guides/', 'docs/reference/'),
    'deploy': ('docs/rollout/', 'config/', 'infra/'),
    'api': ('api/', 'docs/guides/backend-architecture-guide.md'),
    'frontend': ('templates/', 'static/', 'docs/guides/frontend-architecture-guide.md', 'docs/experience/'),
    'css': ('static/css/', 'docs/experience/css-guide.md'),
    'jobs': ('jobs/', 'docs/plans/', 'api/v1/jobs_views.py'),
    'whatsapp': ('communications/', 'integrations/', 'docs/integrations/'),
    'finance': ('finance/', 'catalog/', 'docs/plans/finance'),
    'student': ('students/', 'student_app/', 'student_identity/', 'catalog/'),
}


@dataclass(slots=True)
class RetrievalHit:
    chunk_id: int
    path: str
    title: str
    heading: str
    content: str
    preview: str
    start_line: int
    end_line: int
    score: float
    authority_score: int
    source_kind: str
    reasons: list[str]
    lexical_score: float = 0.0
    semantic_score: float = 0.0


def search_project_knowledge(*, question: str, limit: int = 5) -> list[RetrievalHit]:
    normalized_question = question.strip()
    if not normalized_question:
        return []

    query_tokens = tokenize(normalized_question)
    if not query_tokens:
        return []

    lexical_candidate_limit = max(limit * 6, 24)
    lexical_hits = _search_lexical(question=normalized_question, query_tokens=query_tokens, limit=lexical_candidate_limit)

    combined_hits: dict[int, RetrievalHit] = {hit.chunk_id: hit for hit in lexical_hits}
    semantic_hits = _search_semantic(question=normalized_question, limit=max(limit * 4, 12))
    for hit in semantic_hits:
        existing = combined_hits.get(hit.chunk_id)
        if existing is None:
            combined_hits[hit.chunk_id] = hit
            continue
        existing.semantic_score = hit.semantic_score
        existing.reasons.extend(reason for reason in hit.reasons if reason not in existing.reasons)
        existing.score = round(existing.lexical_score + _semantic_weight(hit.semantic_score), 4)

    return sorted(combined_hits.values(), key=lambda item: (-item.score, item.path, item.start_line))[:limit]


def _search_lexical(*, question: str, query_tokens: list[str], limit: int) -> list[RetrievalHit]:
    candidates = (
        KnowledgeChunk.objects
        .select_related('document')
        .filter(document__is_active=True)
        .only(
            'id',
            'heading',
            'content',
            'content_preview',
            'start_line',
            'end_line',
            'document__path',
            'document__title',
            'document__authority_score',
            'document__source_kind',
        )
    )

    hits: list[RetrievalHit] = []
    for chunk in candidates.iterator():
        score, reasons = score_chunk(question=question, query_tokens=query_tokens, chunk=chunk)
        if score <= 0:
            continue
        hits.append(
            RetrievalHit(
                chunk_id=chunk.id,
                path=chunk.document.path,
                title=chunk.document.title,
                heading=chunk.heading,
                content=chunk.content,
                preview=chunk.content_preview,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                score=round(score, 4),
                authority_score=chunk.document.authority_score,
                source_kind=chunk.document.source_kind,
                reasons=reasons,
                lexical_score=round(score, 4),
            )
        )

    return sorted(hits, key=lambda item: (-item.score, item.path, item.start_line))[:limit]


def _search_semantic(*, question: str, limit: int) -> list[RetrievalHit]:
    client = get_embedding_client()
    if not client.is_enabled():
        return []

    try:
        query_response = client.embed_texts([question])
    except Exception:
        return []

    if not query_response.vectors:
        return []

    query_vector = query_response.vectors[0]
    queryset = (
        KnowledgeChunkEmbedding.objects
        .select_related('chunk__document')
        .filter(
            chunk__document__is_active=True,
            model=query_response.model,
            dimensions=query_response.dimensions,
        )
        .only(
            'chunk_id',
            'vector',
            'norm',
            'chunk__heading',
            'chunk__content',
            'chunk__content_preview',
            'chunk__start_line',
            'chunk__end_line',
            'chunk__document__path',
            'chunk__document__title',
            'chunk__document__authority_score',
            'chunk__document__source_kind',
        )
    )

    top_hits: list[tuple[float, RetrievalHit]] = []
    min_score = float(getattr(settings, 'PROJECT_RAG_EMBEDDING_MIN_SCORE', 0.15) or 0.15)
    for embedding in queryset.iterator(chunk_size=200):
        similarity = cosine_similarity(left=query_vector, right_blob=bytes(embedding.vector), right_norm=embedding.norm)
        if similarity < min_score:
            continue
        final_score = _semantic_weight(similarity)
        hit = RetrievalHit(
            chunk_id=embedding.chunk_id,
            path=embedding.chunk.document.path,
            title=embedding.chunk.document.title,
            heading=embedding.chunk.heading,
            content=embedding.chunk.content,
            preview=embedding.chunk.content_preview,
            start_line=embedding.chunk.start_line,
            end_line=embedding.chunk.end_line,
            score=round(final_score, 4),
            authority_score=embedding.chunk.document.authority_score,
            source_kind=embedding.chunk.document.source_kind,
            reasons=[
                f'autoridade:{embedding.chunk.document.authority_score}',
                f'semantic:{similarity:.4f}',
            ],
            semantic_score=round(similarity, 4),
        )
        if len(top_hits) < limit:
            heapq.heappush(top_hits, (similarity, hit))
            continue
        if similarity > top_hits[0][0]:
            heapq.heapreplace(top_hits, (similarity, hit))

    return [item[1] for item in sorted(top_hits, key=lambda pair: pair[0], reverse=True)]


def _semantic_weight(similarity: float) -> float:
    return max(0.0, similarity) * 12.0


def tokenize(text: str) -> list[str]:
    raw_tokens = [token.lower() for token in TOKEN_RE.findall(text.lower())]
    return [token for token in raw_tokens if token not in STOPWORDS]


def score_chunk(*, question: str, query_tokens: list[str], chunk: KnowledgeChunk) -> tuple[float, list[str]]:
    reasons: list[str] = []
    haystack = f'{chunk.document.path} {chunk.document.title} {chunk.heading} {chunk.content}'.lower()
    content_tokens = set(tokenize(chunk.content))
    title_tokens = set(tokenize(f'{chunk.document.title} {chunk.heading}'))
    path_tokens = set(tokenize(chunk.document.path.replace('/', ' ')))
    query_token_set = set(query_tokens)

    overlap = query_token_set & content_tokens
    title_overlap = query_token_set & title_tokens
    path_overlap = query_token_set & path_tokens

    if not overlap and not title_overlap and not path_overlap and question.lower() not in haystack:
        return 0.0, reasons

    score = chunk.document.authority_score / 20.0
    reasons.append(f'autoridade:{chunk.document.authority_score}')

    if overlap:
        score += len(overlap) * 3.0
        reasons.append(f'overlap:{",".join(sorted(overlap))}')
    if title_overlap:
        score += len(title_overlap) * 2.5
        reasons.append(f'titulo:{",".join(sorted(title_overlap))}')
    if path_overlap:
        score += len(path_overlap) * 2.0
        reasons.append(f'caminho:{",".join(sorted(path_overlap))}')

    lowered_question = question.lower()
    if lowered_question in haystack:
        score += 6.0
        reasons.append('frase-exata')

    for token, boost_paths in INTENT_BOOSTS.items():
        if token in query_token_set and any(chunk.document.path.startswith(candidate) or candidate in chunk.document.path for candidate in boost_paths):
            score += 3.5
            reasons.append(f'intent:{token}')

    if chunk.heading:
        score += 0.5

    density = len(overlap) / max(len(query_token_set), 1)
    score += density * 4.0
    return score, reasons
