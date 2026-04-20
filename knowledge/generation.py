"""
ARQUIVO: geracao de resposta para o conhecimento interno — agnóstico de provedor LLM.

POR QUE ELE EXISTE:
- conecta retrieval local com uma camada de resposta explicavel.
- permite trocar OpenAI por Anthropic (Claude) ou operar sem LLM externo, via settings.

O QUE ESTE ARQUIVO FAZ:
1. monta o pacote de contexto recuperado.
2. tenta LLM remoto apenas quando habilitado explicitamente (PROJECT_RAG_REMOTE_LLM_ENABLED).
3. seleciona o provedor via PROJECT_RAG_GENERATION_PROVIDER ('openai' | 'anthropic' | 'extractive').
4. faz fallback para sintese extrativa local quando o remoto estiver desligado ou falhar.

PONTOS CRITICOS:
- envio para provedor externo fica desligado por padrao para evitar exfiltracao acidental.
- o fallback local prioriza citacao e explainability acima de fluidez.
- Anthropic usa /v1/messages (nao /v1/responses); modelo default: claude-haiku-4-5 (rapido e barato).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests
from django.conf import settings

from .retrieval import RetrievalHit


OPENAI_RESPONSES_URL = 'https://api.openai.com/v1/responses'
ANTHROPIC_MESSAGES_URL = 'https://api.anthropic.com/v1/messages'
ANTHROPIC_API_VERSION = '2023-06-01'

RAG_SYSTEM_PROMPT = (
    'Voce e o RAG interno do repositorio OctoBox. '
    'Responda em Portugues do Brasil. '
    'Use apenas o contexto fornecido. '
    'Se algo nao estiver no contexto, diga que nao encontrou evidencias suficientes. '
    'Cite caminhos de arquivo relevantes no corpo da resposta.'
)


@dataclass(slots=True)
class GeneratedAnswer:
    answer: str
    mode: str
    citations: list[dict]


def generate_project_answer(*, question: str, hits: list[RetrievalHit]) -> GeneratedAnswer:
    citations = [serialize_hit(hit) for hit in hits]
    if not hits:
        return GeneratedAnswer(
            answer='Nao encontrei contexto suficiente no indice atual para responder com seguranca.',
            mode='empty-index-or-no-match',
            citations=[],
        )

    if _remote_generation_enabled():
        provider = getattr(settings, 'PROJECT_RAG_GENERATION_PROVIDER', 'openai').strip().lower()
        try:
            if provider == 'anthropic':
                answer = _generate_with_anthropic(question=question, hits=hits)
                if answer:
                    return GeneratedAnswer(answer=answer, mode='anthropic-messages', citations=citations)
            else:
                answer = _generate_with_openai(question=question, hits=hits)
                if answer:
                    return GeneratedAnswer(answer=answer, mode='openai-responses', citations=citations)
        except requests.RequestException:
            pass

    return GeneratedAnswer(
        answer=_extractive_fallback(question=question, hits=hits),
        mode='extractive-fallback',
        citations=citations,
    )


def serialize_hit(hit: RetrievalHit) -> dict:
    return {
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


def _remote_generation_enabled() -> bool:
    if not bool(getattr(settings, 'PROJECT_RAG_REMOTE_LLM_ENABLED', False)):
        return False
    provider = getattr(settings, 'PROJECT_RAG_GENERATION_PROVIDER', 'openai').strip().lower()
    if provider == 'anthropic':
        return bool(os.getenv('ANTHROPIC_API_KEY'))
    return bool(os.getenv('OPENAI_API_KEY'))


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------

def _generate_with_openai(*, question: str, hits: list[RetrievalHit]) -> str:
    api_key = os.getenv('OPENAI_API_KEY', '').strip()
    payload = {
        'model': getattr(settings, 'PROJECT_RAG_REMOTE_MODEL', 'gpt-4o-mini'),
        'instructions': RAG_SYSTEM_PROMPT,
        'input': _build_prompt(question=question, hits=hits),
    }
    response = requests.post(
        OPENAI_RESPONSES_URL,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        json=payload,
        timeout=getattr(settings, 'PROJECT_RAG_REMOTE_TIMEOUT_SECONDS', 30),
    )
    response.raise_for_status()
    return _extract_openai_text(response.json()).strip()


def _extract_openai_text(payload: dict) -> str:
    direct = payload.get('output_text')
    if isinstance(direct, str) and direct.strip():
        return direct
    parts: list[str] = []
    for item in payload.get('output', []):
        for content in item.get('content', []):
            text = content.get('text')
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
            elif isinstance(text, dict):
                value = text.get('value', '')
                if value:
                    parts.append(str(value).strip())
    return '\n'.join(parts).strip()


# ---------------------------------------------------------------------------
# Anthropic provider
# ---------------------------------------------------------------------------

def _generate_with_anthropic(*, question: str, hits: list[RetrievalHit]) -> str:
    """Gera resposta via Anthropic Messages API (Claude).

    Modelo default: claude-haiku-4-5 — rapido, barato, ideal para RAG de consulta.
    Pode ser sobrescrito via PROJECT_RAG_REMOTE_MODEL=claude-sonnet-4-6 para respostas mais ricas.
    """
    api_key = os.getenv('ANTHROPIC_API_KEY', '').strip()
    model = getattr(settings, 'PROJECT_RAG_REMOTE_MODEL', 'claude-haiku-4-5-20251001')
    max_tokens = int(getattr(settings, 'PROJECT_RAG_REMOTE_MAX_TOKENS', 1024) or 1024)
    payload = {
        'model': model,
        'max_tokens': max_tokens,
        'system': RAG_SYSTEM_PROMPT,
        'messages': [
            {'role': 'user', 'content': _build_prompt(question=question, hits=hits)},
        ],
    }
    response = requests.post(
        ANTHROPIC_MESSAGES_URL,
        headers={
            'x-api-key': api_key,
            'anthropic-version': ANTHROPIC_API_VERSION,
            'Content-Type': 'application/json',
        },
        json=payload,
        timeout=getattr(settings, 'PROJECT_RAG_REMOTE_TIMEOUT_SECONDS', 30),
    )
    response.raise_for_status()
    data = response.json()
    parts = [block.get('text', '') for block in data.get('content', []) if block.get('type') == 'text']
    return '\n'.join(parts).strip()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _build_prompt(*, question: str, hits: list[RetrievalHit]) -> str:
    context_parts = []
    max_chars = getattr(settings, 'PROJECT_RAG_MAX_CONTEXT_CHARS', 12000)
    used = 0
    for index, hit in enumerate(hits, start=1):
        block = (
            f'[{index}] PATH: {hit.path}\n'
            f'HEADING: {hit.heading or "-"}\n'
            f'LINES: {hit.start_line}-{hit.end_line}\n'
            f'CONTENT:\n{hit.content}\n'
        )
        if used + len(block) > max_chars:
            break
        context_parts.append(block)
        used += len(block)
    context = '\n---\n'.join(context_parts)
    return (
        f'Pergunta:\n{question}\n\n'
        'Contexto recuperado do repositorio:\n'
        f'{context}\n\n'
        'Tarefa: responda somente com base nesse contexto e cite os caminhos mais relevantes.'
    )


def _extractive_fallback(*, question: str, hits: list[RetrievalHit]) -> str:
    lines = [f'Pergunta: {question}', '', 'Base mais relevante encontrada no indice:']
    for hit in hits[:3]:
        lines.append(
            f'- {hit.path} ({hit.start_line}-{hit.end_line})'
            + (f' :: {hit.heading}' if hit.heading else '')
            + f' -> {hit.preview}'
        )
    lines.append('')
    lines.append(
        'Leitura honesta: o modo local esta em fallback extrativo; '
        'para resposta sintetica por LLM, habilite PROJECT_RAG_REMOTE_LLM_ENABLED '
        'e configure PROJECT_RAG_GENERATION_PROVIDER (openai | anthropic).'
    )
    return '\n'.join(lines)

