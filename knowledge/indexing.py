"""
ARQUIVO: orquestracao de indexacao do RAG interno.

POR QUE ELE EXISTE:
- concentra a sincronizacao lexical e vetorial em um corredor reutilizavel por comando e job.

O QUE ESTE ARQUIVO FAZ:
1. sincroniza documentos e chunks.
2. sincroniza embeddings opcionalmente.
3. retorna estatisticas de ingestao para observabilidade e jobs.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from knowledge.chunking import chunk_file
from knowledge.embeddings import get_embedding_client
from knowledge.models import KnowledgeChunk, KnowledgeChunkEmbedding, KnowledgeDocument
from knowledge.sources import iter_project_sources
from knowledge.vector_math import pack_vector, vector_norm


def sync_project_knowledge(*, force: bool = False, with_embeddings: bool | None = None) -> dict[str, object]:
    base_dir = Path(settings.BASE_DIR)
    now = timezone.now()
    indexed_paths: set[str] = set()
    indexed_documents = 0
    regenerated_chunks = 0
    embedding_stats = {
        'embeddings_enabled': False,
        'embeddings_regenerated': 0,
        'embeddings_skipped': 0,
        'embedding_prompt_tokens': 0,
        'embedding_model': '',
        'embedding_dimensions': 0,
    }

    for source in iter_project_sources(base_dir):
        indexed_paths.add(source.relative_path)
        with transaction.atomic():
            document, created = KnowledgeDocument.objects.get_or_create(
                path=source.relative_path,
                defaults={
                    'title': source.title,
                    'source_kind': source.source_kind,
                    'authority_score': source.authority_score,
                    'checksum': source.checksum,
                    'line_count': source.line_count,
                    'metadata': source.metadata,
                    'is_active': True,
                    'last_indexed_at': now,
                },
            )

            should_rechunk = created or force or document.checksum != source.checksum
            document.title = source.title
            document.source_kind = source.source_kind
            document.authority_score = source.authority_score
            document.checksum = source.checksum
            document.line_count = source.line_count
            document.metadata = source.metadata
            document.is_active = True
            document.last_indexed_at = now
            document.save()

            if should_rechunk:
                KnowledgeChunk.objects.filter(document=document).delete()
                chunk_drafts = chunk_file(
                    path=source.relative_path,
                    content=source.content,
                    extension=source.extension,
                )
                chunk_models = [
                    KnowledgeChunk(
                        document=document,
                        ordinal=index,
                        heading=draft.heading[:255],
                        content=draft.content,
                        content_preview=draft.metadata.get('preview', '')[:280],
                        token_count=draft.token_count,
                        start_line=draft.start_line,
                        end_line=draft.end_line,
                        checksum=hashlib.sha1(draft.content.encode('utf-8')).hexdigest(),
                        metadata=draft.metadata,
                    )
                    for index, draft in enumerate(chunk_drafts, start=1)
                ]
                KnowledgeChunk.objects.bulk_create(chunk_models)
                regenerated_chunks += len(chunk_models)
            indexed_documents += 1

    stale_documents = KnowledgeDocument.objects.exclude(path__in=indexed_paths)
    stale_documents.update(is_active=False, last_indexed_at=now)

    effective_with_embeddings = bool(
        getattr(settings, 'PROJECT_RAG_EMBEDDINGS_ENABLED', False)
        if with_embeddings is None
        else with_embeddings
    )
    if effective_with_embeddings:
        embedding_stats = sync_chunk_embeddings(force=force)

    return {
        'indexed_documents': indexed_documents,
        'regenerated_chunks': regenerated_chunks,
        'stale_documents_deactivated': stale_documents.count(),
        **embedding_stats,
    }


def sync_chunk_embeddings(*, force: bool = False) -> dict[str, object]:
    client = get_embedding_client()
    if not client.is_enabled():
        return {
            'embeddings_enabled': False,
            'embeddings_regenerated': 0,
            'embeddings_skipped': KnowledgeChunk.objects.filter(document__is_active=True).count(),
            'embedding_prompt_tokens': 0,
            'embedding_model': client.model,
            'embedding_dimensions': client.dimensions,
        }

    active_chunks = list(
        KnowledgeChunk.objects
        .select_related('document')
        .filter(document__is_active=True)
        .order_by('document__path', 'ordinal')
    )
    if not active_chunks:
        return {
            'embeddings_enabled': True,
            'embeddings_regenerated': 0,
            'embeddings_skipped': 0,
            'embedding_prompt_tokens': 0,
            'embedding_model': client.model,
            'embedding_dimensions': client.dimensions,
        }

    existing_embeddings = {
        item.chunk_id: item
        for item in KnowledgeChunkEmbedding.objects.filter(chunk_id__in=[chunk.id for chunk in active_chunks])
    }

    pending_chunks: list[KnowledgeChunk] = []
    skipped = 0
    for chunk in active_chunks:
        existing = existing_embeddings.get(chunk.id)
        if (
            not force
            and existing is not None
            and existing.checksum == chunk.checksum
            and existing.model == client.model
            and existing.dimensions == client.dimensions
        ):
            skipped += 1
            continue
        pending_chunks.append(chunk)

    regenerated = 0
    prompt_tokens = 0
    batch_size = int(getattr(settings, 'PROJECT_RAG_EMBEDDING_BATCH_SIZE', 64) or 64)
    now = timezone.now()

    for start in range(0, len(pending_chunks), batch_size):
        batch_chunks = pending_chunks[start:start + batch_size]
        response = client.embed_texts([build_embedding_text(chunk) for chunk in batch_chunks])
        prompt_tokens += response.prompt_tokens
        existing_batch = {
            item.chunk_id: item
            for item in KnowledgeChunkEmbedding.objects.filter(chunk_id__in=[chunk.id for chunk in batch_chunks])
        }
        to_create: list[KnowledgeChunkEmbedding] = []
        to_update: list[KnowledgeChunkEmbedding] = []
        for chunk, vector in zip(batch_chunks, response.vectors):
            packed = pack_vector(vector)
            norm = vector_norm(vector)
            existing = existing_batch.get(chunk.id)
            if existing is None:
                to_create.append(
                    KnowledgeChunkEmbedding(
                        chunk=chunk,
                        model=response.model,
                        dimensions=response.dimensions,
                        checksum=chunk.checksum,
                        vector=packed,
                        norm=norm,
                        generated_at=now,
                    )
                )
            else:
                existing.model = response.model
                existing.dimensions = response.dimensions
                existing.checksum = chunk.checksum
                existing.vector = packed
                existing.norm = norm
                existing.generated_at = now
                to_update.append(existing)
        if to_create:
            KnowledgeChunkEmbedding.objects.bulk_create(to_create)
        if to_update:
            KnowledgeChunkEmbedding.objects.bulk_update(
                to_update,
                ['model', 'dimensions', 'checksum', 'vector', 'norm', 'generated_at', 'updated_at'],
            )
        regenerated += len(batch_chunks)

    return {
        'embeddings_enabled': True,
        'embeddings_regenerated': regenerated,
        'embeddings_skipped': skipped,
        'embedding_prompt_tokens': prompt_tokens,
        'embedding_model': client.model,
        'embedding_dimensions': client.dimensions,
    }


def build_embedding_text(chunk: KnowledgeChunk) -> str:
    title = chunk.document.title or chunk.document.path
    heading = chunk.heading or ''
    return (
        f'PATH: {chunk.document.path}\n'
        f'TITLE: {title}\n'
        f'HEADING: {heading}\n'
        f'CONTENT:\n{chunk.content}'
    )
