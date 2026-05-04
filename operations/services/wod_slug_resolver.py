"""
ARQUIVO: resolvedor de slugs de movimentos via LLM para o Smart Paste semanal.

POR QUE ELE EXISTE:
- o dicionario de 104 movimentos nao cobre 100% dos textos reais dos coaches.
- quando o parser deterministico nao reconhece um movimento, este servico tenta resolver via LLM.
- resultado: zero chips vermelhos para a maioria dos treinos sem exigir revisao manual.

O QUE ESTE ARQUIVO FAZ:
1. recebe lista de nomes de movimento nao reconhecidos.
2. chama OpenAI (gpt-4o-mini) ou Anthropic (claude-haiku) com o dicionario completo.
3. retorna dict {nome_raw: slug_canonico}.
4. falha silenciosamente (retorna {}) quando LLM nao esta configurado ou falha.

PONTOS CRITICOS:
- nao lanca excecao: qualquer falha retorna {} e o comportamento original e preservado.
- slugs retornados pelo LLM sao validados contra o dicionario antes de serem aplicados.
- timeout curto (8s) para nao bloquear o render da pagina.
- usa OPENAI_API_KEY por padrao, fallback para ANTHROPIC_API_KEY.
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
_TIMEOUT_SECONDS = 8
_OPENAI_MODEL = 'gpt-4o-mini'
_ANTHROPIC_MODEL = 'claude-haiku-4-5-20251001'


def resolve_unknown_slugs(
    *,
    unrecognized_names: list[str],
    slug_dictionary: list[tuple[str, tuple[str, ...]]],
) -> dict[str, str]:
    """Tenta resolver slugs para nomes nao reconhecidos pelo dicionario deterministico.

    Args:
        unrecognized_names: lista de nomes de movimento nao resolvidos (texto livre do coach).
        slug_dictionary: dicionario canonico carregado por load_wod_movement_dictionary().

    Returns:
        Dicionario {nome_raw: slug_canonico}. Pode ser vazio se LLM nao estiver disponivel.
    """
    if not unrecognized_names:
        return {}

    valid_slugs = {slug for slug, _ in slug_dictionary}
    if not valid_slugs:
        return {}

    all_slugs_text = ', '.join(sorted(valid_slugs))
    names_text = '\n'.join(f'- {name}' for name in unrecognized_names)

    prompt = (
        'Voce e um especialista em CrossFit e treinamento funcional. '
        'Abaixo esta uma lista de movimentos extraidos de um treino em portugues ou ingles '
        'que nao foram reconhecidos pelo dicionario interno. '
        'Para cada movimento, identifique o slug canonico mais proximo da lista de slugs validos fornecida. '
        'Se nao houver correspondencia razoavel, use string vazia "".\n\n'
        f'Slugs validos:\n{all_slugs_text}\n\n'
        f'Movimentos para resolver:\n{names_text}\n\n'
        'Responda SOMENTE com um objeto JSON valido no formato:\n'
        '{"nome do movimento": "slug_canonico"}\n'
        'Sem explicacoes, sem markdown, apenas o JSON.'
    )

    openai_key = os.getenv('OPENAI_API_KEY', '').strip()
    anthropic_key = os.getenv('ANTHROPIC_API_KEY', '').strip()

    raw_text = None
    if openai_key:
        raw_text = _call_openai(prompt=prompt, api_key=openai_key)
    elif anthropic_key:
        raw_text = _call_anthropic(prompt=prompt, api_key=anthropic_key)
    else:
        logger.debug('wod_slug_resolver: nenhuma chave LLM configurada, retornando vazio.')
        return {}

    if not raw_text:
        return {}

    return _parse_and_validate(
        raw_text=raw_text,
        valid_slugs=valid_slugs,
        unrecognized_names=unrecognized_names,
    )


def apply_llm_slug_resolution(parsed_payload: dict, slug_dictionary: list[tuple[str, tuple[str, ...]]]) -> None:
    """Aplica resolucao LLM de slugs diretamente no parsed_payload (in-place).

    Coleta todos os movimentos sem slug, chama o LLM e preenche os slugs resolvidos.
    Falha silenciosamente: se o LLM nao estiver disponivel, o payload permanece inalterado.
    """
    days = parsed_payload.get('days', [])

    # Coletar movimentos nao resolvidos com suas posicoes
    unresolved: list[tuple[int, int, int, str]] = []
    for day_idx, day in enumerate(days):
        for block_idx, block in enumerate(day.get('blocks', [])):
            for mov_idx, movement in enumerate(block.get('movements', [])):
                if not movement.get('movement_slug'):
                    raw_name = (movement.get('movement_label_raw') or '').strip()
                    if raw_name:
                        unresolved.append((day_idx, block_idx, mov_idx, raw_name))

    if not unresolved:
        return

    unrecognized_names = list({name for _, _, _, name in unresolved})
    resolved = resolve_unknown_slugs(
        unrecognized_names=unrecognized_names,
        slug_dictionary=slug_dictionary,
    )

    if not resolved:
        return

    for day_idx, block_idx, mov_idx, raw_name in unresolved:
        slug = resolved.get(raw_name)
        if slug:
            days[day_idx]['blocks'][block_idx]['movements'][mov_idx]['movement_slug'] = slug
            logger.info('wod_slug_resolver: "%s" → "%s"', raw_name, slug)


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

def _call_openai(*, prompt: str, api_key: str) -> str | None:
    try:
        response = requests.post(
            _OPENAI_CHAT_URL,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': _OPENAI_MODEL,
                'messages': [{'role': 'user', 'content': prompt}],
                'response_format': {'type': 'json_object'},
                'temperature': 0,
                'max_tokens': 512,
            },
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get('choices', [])
        if choices:
            return choices[0].get('message', {}).get('content', '')
    except Exception as exc:
        logger.warning('wod_slug_resolver: chamada OpenAI falhou: %s', exc)
    return None


def _call_anthropic(*, prompt: str, api_key: str) -> str | None:
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
                'max_tokens': 512,
                'messages': [{'role': 'user', 'content': prompt}],
            },
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        parts = [block.get('text', '') for block in data.get('content', []) if block.get('type') == 'text']
        return '\n'.join(parts).strip()
    except Exception as exc:
        logger.warning('wod_slug_resolver: chamada Anthropic falhou: %s', exc)
    return None


# ---------------------------------------------------------------------------
# Parsing and validation
# ---------------------------------------------------------------------------

def _parse_and_validate(
    *,
    raw_text: str,
    valid_slugs: set[str],
    unrecognized_names: list[str],
) -> dict[str, str]:
    """Extrai e valida o JSON retornado pelo LLM."""
    text = raw_text.strip()

    # Extrair bloco JSON mesmo que o modelo envolva em markdown
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1 or end <= start:
        logger.warning('wod_slug_resolver: resposta do LLM nao contem JSON valido.')
        return {}

    try:
        mapping = json.loads(text[start:end + 1])
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning('wod_slug_resolver: falha ao parsear JSON: %s', exc)
        return {}

    result: dict[str, str] = {}
    unrecognized_lower = {name.lower(): name for name in unrecognized_names}

    for key, value in mapping.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        original_name = unrecognized_lower.get(key.lower(), key)
        slug = value.strip()
        # Aceitar apenas slugs que existem no dicionario canonico
        if slug and slug in valid_slugs:
            result[original_name] = slug
        elif slug:
            logger.debug('wod_slug_resolver: slug "%s" retornado para "%s" nao existe no dicionario.', slug, key)

    return result


__all__ = ['resolve_unknown_slugs', 'apply_llm_slug_resolution']
