"""
ARQUIVO: clientes de embeddings para o RAG interno — agnóstico de provedor.

POR QUE ELE EXISTE:
- habilita semantica vetorial sem acoplar o projeto a um provedor unico.
- permite trocar OpenAI por Voyage AI ou desativar embeddings via settings, sem mudar codigo.

O QUE ESTE ARQUIVO FAZ:
1. define EmbeddingResponse como contrato de dados compartilhado.
2. implementa OpenAIEmbeddingClient (provider: 'openai').
3. implementa VoyageEmbeddingClient (provider: 'voyage') — ecosistema Anthropic, otimo para codigo.
4. implementa NoOpEmbeddingClient (provider: 'disabled') — fallback puro lexical, zero dependencia externa.
5. expoe get_embedding_client() como factory unica — escolhe o provider via PROJECT_RAG_EMBEDDING_PROVIDER.

PONTOS CRITICOS:
- chave da API nunca deve vazar para frontend.
- envio remoto fica desligado por feature flag explicita (PROJECT_RAG_EMBEDDINGS_ENABLED).
- trocar provider nao requer migracao: chunks com embedding de modelo antigo sao ignorados automaticamente
  pelo retrieval (model e dimensions devem casar com o embedding armazenado).
- se o provider for 'disabled' ou a chave nao existir, o sistema cai graciosamente em busca lexical pura.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests
from django.conf import settings


OPENAI_EMBEDDINGS_URL = 'https://api.openai.com/v1/embeddings'
VOYAGE_EMBEDDINGS_URL = 'https://api.voyageai.com/v1/embeddings'


@dataclass(slots=True)
class EmbeddingResponse:
    vectors: list[list[float]]
    model: str
    dimensions: int
    prompt_tokens: int


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

class OpenAIEmbeddingClient:
    """Provider OpenAI — texto, codigo e docs. Requer OPENAI_API_KEY."""

    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY', '').strip()
        self.model = getattr(settings, 'PROJECT_RAG_EMBEDDING_MODEL', 'text-embedding-3-small')
        self.dimensions = int(getattr(settings, 'PROJECT_RAG_EMBEDDING_DIMENSIONS', 256) or 0)
        self.timeout_seconds = int(getattr(settings, 'PROJECT_RAG_EMBEDDING_TIMEOUT_SECONDS', 30) or 30)

    def is_enabled(self) -> bool:
        return bool(getattr(settings, 'PROJECT_RAG_EMBEDDINGS_ENABLED', False) and self.api_key)

    def embed_texts(self, texts: list[str], *, request_id: str = '') -> EmbeddingResponse:
        if not texts:
            return EmbeddingResponse(vectors=[], model=self.model, dimensions=self.dimensions, prompt_tokens=0)
        if not self.is_enabled():
            raise RuntimeError('project-rag-embeddings-disabled')

        payload: dict = {
            'model': self.model,
            'input': texts,
            'encoding_format': 'float',
        }
        if self.dimensions:
            payload['dimensions'] = self.dimensions

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        if request_id:
            headers['X-Client-Request-Id'] = request_id[:512]

        response = requests.post(
            OPENAI_EMBEDDINGS_URL,
            headers=headers,
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        vectors = [item['embedding'] for item in data.get('data', [])]
        resolved_dimensions = len(vectors[0]) if vectors else self.dimensions
        return EmbeddingResponse(
            vectors=vectors,
            model=data.get('model', self.model),
            dimensions=resolved_dimensions,
            prompt_tokens=int(data.get('usage', {}).get('prompt_tokens', 0) or 0),
        )


class VoyageEmbeddingClient:
    """Provider Voyage AI — ecosistema Anthropic, excelente para codigo e docs tecnicas.

    Modelos recomendados:
    - voyage-3-lite: 512 dims, rapido e barato (default).
    - voyage-code-3: 1024 dims, otimizado para codigo-fonte.

    Requer VOYAGE_API_KEY. Sem o PROJECT_RAG_EMBEDDING_DIMENSIONS configurado,
    usa a dimensao nativa do modelo retornada pela API.
    """

    def __init__(self):
        self.api_key = os.getenv('VOYAGE_API_KEY', '').strip()
        self.model = getattr(settings, 'PROJECT_RAG_EMBEDDING_MODEL', 'voyage-3-lite')
        self.dimensions = int(getattr(settings, 'PROJECT_RAG_EMBEDDING_DIMENSIONS', 0) or 0)
        self.timeout_seconds = int(getattr(settings, 'PROJECT_RAG_EMBEDDING_TIMEOUT_SECONDS', 30) or 30)

    def is_enabled(self) -> bool:
        return bool(getattr(settings, 'PROJECT_RAG_EMBEDDINGS_ENABLED', False) and self.api_key)

    def embed_texts(self, texts: list[str], *, request_id: str = '') -> EmbeddingResponse:
        if not texts:
            return EmbeddingResponse(vectors=[], model=self.model, dimensions=self.dimensions, prompt_tokens=0)
        if not self.is_enabled():
            raise RuntimeError('project-rag-embeddings-disabled')

        payload: dict = {
            'model': self.model,
            'input': texts,
            'input_type': 'document',
        }

        response = requests.post(
            VOYAGE_EMBEDDINGS_URL,
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        vectors = [item['embedding'] for item in data.get('data', [])]
        resolved_dimensions = len(vectors[0]) if vectors else self.dimensions
        return EmbeddingResponse(
            vectors=vectors,
            model=data.get('model', self.model),
            dimensions=resolved_dimensions,
            prompt_tokens=int(data.get('usage', {}).get('total_tokens', 0) or 0),
        )


class NoOpEmbeddingClient:
    """Provider desativado — RAG opera em modo lexical puro, zero dependencia externa.

    Use quando PROJECT_RAG_EMBEDDING_PROVIDER='disabled' ou quando nenhuma chave estiver
    disponivel. O sistema continua funcionando normalmente via busca lexical + autoridade.
    """

    def __init__(self):
        self.model = 'noop'
        self.dimensions = 0

    def is_enabled(self) -> bool:
        return False

    def embed_texts(self, texts: list[str], *, request_id: str = '') -> EmbeddingResponse:
        raise RuntimeError('project-rag-noop-embedding-client-always-disabled')


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_embedding_client() -> OpenAIEmbeddingClient | VoyageEmbeddingClient | NoOpEmbeddingClient:
    """Retorna o cliente de embeddings configurado via PROJECT_RAG_EMBEDDING_PROVIDER.

    Valores aceitos:
    - 'openai'   → OpenAIEmbeddingClient (default)
    - 'voyage'   → VoyageEmbeddingClient (ecosistema Anthropic)
    - 'disabled' → NoOpEmbeddingClient (lexical puro, zero dependencia externa)

    Se a variavel nao existir, usa 'openai' para compatibilidade retroativa.
    """
    provider = getattr(settings, 'PROJECT_RAG_EMBEDDING_PROVIDER', 'openai').strip().lower()
    if provider == 'voyage':
        return VoyageEmbeddingClient()
    if provider == 'disabled':
        return NoOpEmbeddingClient()
    return OpenAIEmbeddingClient()
