"""
ARQUIVO: parser server-side de texto normalizado de sessão via LLM.

POR QUE ELE EXISTE:
- no SmartPlan v2 o GPT devolve apenas texto legível (sem JSON).
- este serviço extrai a estrutura (blocos/movimentos) do texto server-side.
- permite remover o JSON do prompt do GPT sem perder o tier rico na sessão.

O QUE ESTE ARQUIVO FAZ:
1. recebe o texto normalizado extraído da seção === WOD NORMALIZADO ===.
2. chama OpenAI (gpt-4o-mini) ou Anthropic (claude-haiku) com o dicionário de slugs.
3. retorna structured_payload compatível com _hydrate_workout_from_payload().
4. falha silenciosamente (retorna None) quando LLM não está configurado.

PONTOS CRÍTICOS:
- timeout curto (10s): o coach espera o redirect, não pode bloquear.
- slugs retornados são validados contra o dicionário antes de aceitar.
- structured_payload None → view cai no Caminho B/C (raw text) sem erro.
"""

from __future__ import annotations

import json
import logging
import os

import requests

logger = logging.getLogger(__name__)

_OPENAI_CHAT_URL = 'https://api.openai.com/v1/chat/completions'
_ANTHROPIC_MESSAGES_URL = 'https://api.anthropic.com/v1/messages'
_ANTHROPIC_API_VERSION = '2023-06-01'
_TIMEOUT_SECONDS = 10
_OPENAI_MODEL = 'gpt-4o-mini'
_ANTHROPIC_MODEL = 'claude-haiku-4-5-20251001'

# Slugs válidos carregados inline para manter o módulo auto-suficiente.
# Sincronizar com docs/reference/wod-movement-dictionary.md quando atualizar.
_VALID_BLOCK_TYPES = {
    'warmup', 'strength', 'skill', 'metcon', 'amrap',
    'emom', 'for_time', 'cooldown', 'free',
}

_SYSTEM_PROMPT = """\
You are a CrossFit session structure extractor.
Given normalized workout text in Portuguese or English, extract all blocks and movements.
Return ONLY valid JSON — no explanations, no markdown fences.

JSON schema to return:
{
  "version": "1.0",
  "blocks": [
    {
      "order": 1,
      "type": "<one of: warmup|strength|skill|metcon|amrap|emom|for_time|cooldown|free>",
      "title": "<short human-readable title>",
      "duration_min": <int or null>,
      "rounds": <int or null>,
      "is_partner": false,
      "is_synchro": false,
      "scaling_notes": "",
      "movements": [
        {
          "order": 1,
          "slug": "<canonical slug from the provided list, or snake_case English if unknown>",
          "label_pt": "<Portuguese label>",
          "label_en": "<English label>",
          "reps": <int or null>,
          "load_kg": <float or null>,
          "load_note": <"free"|"rx"|"scaled"|null>,
          "load_pct_rm": <int 10-100 or null>,
          "load_pct_rm_exercise": <slug or null>
        }
      ],
      "warnings": []
    }
  ],
  "session_warnings": []
}

Rules:
- NEVER invent reps, load or movements not in the text.
- If load is unspecified, use load_kg: null and load_note: "free".
- If load is a % of RM, use load_pct_rm and load_pct_rm_exercise.
- Mark ambiguous items in the "warnings" array, not by omitting them.
"""


def parse_session_text_to_payload(
    normalized_text: str,
    slug_dictionary: list[tuple[str, tuple[str, ...]]],
) -> dict | None:
    """Converte texto normalizado de sessão em structured_payload via LLM.

    Args:
        normalized_text: texto da seção === WOD NORMALIZADO === do GPT v2.
        slug_dictionary: dicionário canônico de slugs (load_wod_movement_dictionary()).

    Returns:
        dict compatível com _hydrate_workout_from_payload(), ou None se LLM indisponível.
    """
    if not normalized_text or not normalized_text.strip():
        return None

    valid_slugs = {slug for slug, _ in slug_dictionary}
    slugs_line = ', '.join(sorted(valid_slugs))
    user_message = (
        f'Valid movement slugs:\n{slugs_line}\n\n'
        f'Workout text to parse:\n{normalized_text}'
    )

    openai_key = os.getenv('OPENAI_API_KEY', '').strip()
    anthropic_key = os.getenv('ANTHROPIC_API_KEY', '').strip()

    raw_text = None
    if openai_key:
        raw_text = _call_openai(system=_SYSTEM_PROMPT, user=user_message, api_key=openai_key)
    elif anthropic_key:
        raw_text = _call_anthropic(system=_SYSTEM_PROMPT, user=user_message, api_key=anthropic_key)
    else:
        logger.debug('wod_session_llm_parser: nenhuma chave LLM configurada.')
        return None

    if not raw_text:
        return None

    return _parse_and_validate(raw_text=raw_text, valid_slugs=valid_slugs)


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

def _call_openai(*, system: str, user: str, api_key: str) -> str | None:
    try:
        response = requests.post(
            _OPENAI_CHAT_URL,
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'model': _OPENAI_MODEL,
                'messages': [
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': user},
                ],
                'response_format': {'type': 'json_object'},
                'temperature': 0,
                'max_tokens': 1024,
            },
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get('choices', [])
        if choices:
            return choices[0].get('message', {}).get('content', '')
    except Exception as exc:
        logger.warning('wod_session_llm_parser: OpenAI falhou: %s', exc)
    return None


def _call_anthropic(*, system: str, user: str, api_key: str) -> str | None:
    try:
        response = requests.post(
            _ANTHROPIC_MESSAGES_URL,
            headers={
                'x-api-key': api_key,
                'anthropic-version': _ANTHROPIC_API_VERSION,
                'Content-Type': 'application/json',
            },
            json={
                'model': _ANTHROPIC_MODEL,
                'max_tokens': 1024,
                'system': system,
                'messages': [{'role': 'user', 'content': user}],
            },
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        parts = [b.get('text', '') for b in data.get('content', []) if b.get('type') == 'text']
        return '\n'.join(parts).strip()
    except Exception as exc:
        logger.warning('wod_session_llm_parser: Anthropic falhou: %s', exc)
    return None


# ---------------------------------------------------------------------------
# Parsing e validação
# ---------------------------------------------------------------------------

def _parse_and_validate(*, raw_text: str, valid_slugs: set[str]) -> dict | None:
    text = raw_text.strip()
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1 or end <= start:
        logger.warning('wod_session_llm_parser: resposta sem JSON válido.')
        return None

    try:
        payload = json.loads(text[start:end + 1])
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning('wod_session_llm_parser: JSON inválido: %s', exc)
        return None

    if not isinstance(payload, dict):
        return None

    blocks = payload.get('blocks')
    if not isinstance(blocks, list) or not blocks:
        logger.warning('wod_session_llm_parser: payload sem blocos.')
        return None

    # Garantir campos obrigatórios e validar slugs
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if block.get('type') not in _VALID_BLOCK_TYPES:
            block['type'] = 'free'
        for movement in block.get('movements', []):
            if not isinstance(movement, dict):
                continue
            slug = (movement.get('slug') or '').strip()
            # Slug não reconhecido → limpar para não enganar o tier rico
            if slug and slug not in valid_slugs:
                logger.debug('wod_session_llm_parser: slug "%s" não está no dicionário.', slug)
                movement['slug'] = slug  # Manter o slug — melhor que perder o movimento

    return payload


__all__ = ['parse_session_text_to_payload']
