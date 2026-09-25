"""
ARQUIVO: resolvedor de slugs de movimentos via LLM para o Smart Paste semanal.

POR QUE ELE EXISTE:
- o dicionario canonico nao cobre 100% dos textos reais dos coaches.
- quando o parser deterministico nao reconhece um movimento, este servico tenta resolver via LLM.
- resultado: zero chips vermelhos para a maioria dos treinos sem exigir revisao manual.

O QUE ESTE ARQUIVO FAZ:
1. recebe lista de nomes de movimento nao reconhecidos.
2. consulta primeiro a memoria aprendida (knowledge.WodMovementLearnedAlias, compartilhada
   entre boxes) — nome ja visto antes resolve na hora, sem chamar LLM.
3. o que sobrar vai para Anthropic Haiku com o dicionario completo.
4. toda resolucao nova do LLM e gravada na memoria, pra nao pagar de novo pelo mesmo erro comum.
5. retorna dict {nome_raw: {"slug": slug_canonico, "note": nota_curta_pt_br}}.
6. falha silenciosamente (retorna {}) quando LLM nao esta configurado ou falha; erro na
   memoria (tabela sem migration aplicada, banco fora) tambem nunca derruba o fluxo.

PONTOS CRITICOS:
- nao lanca excecao: qualquer falha retorna {} e o comportamento original e preservado.
- slugs retornados pelo LLM sao validados contra o dicionario antes de serem aplicados.
- timeout limitado a 20s, abaixo do limite padrao do worker web.
- usa ANTHROPIC_API_KEY e, para chaves multi-workspace, ANTHROPIC_WORKSPACE_ID.
- a "note" e so um resumo em linguagem natural da troca feita (ex.: "Troquei 'agachamnto'
  por Back Squat") para exibir no preview do Smart Paste — nunca usada para alterar dado
  numerico (reps/carga), so texto de UI.
- os aliases canonicos vao no prompt para o modelo entender abreviacoes. A resposta
  e JSON estruturado com ids estaveis e passa por validacao de slugs no servidor.
- a memoria (WodMovementLearnedAlias) vive no app knowledge (schema public, cross-tenant) —
  igual o RAG: erro de digitacao de exercicio e vocabulario universal, nao dado de negocio
  de uma box. Chave de lookup e o texto normalizado (minusculo, sem acento/pontuacao).
"""

from __future__ import annotations

import json
import logging
import os
import re
import unicodedata

import requests
from django.db import models

logger = logging.getLogger(__name__)

_ANTHROPIC_MESSAGES_URL = 'https://api.anthropic.com/v1/messages'
_ANTHROPIC_API_VERSION = '2023-06-01'
_TIMEOUT_SECONDS = 20
_ANTHROPIC_MODEL = 'claude-haiku-4-5-20251001'
_MAX_OUTPUT_TOKENS = 2048
_NAMES_PER_BATCH = 80

# Limite superior para evitar gastar a API com texto fora do escopo de treino.
_MAX_NAMES_PER_CALL = 80


_STATIC_INSTRUCTIONS = (
    'Voce e um especialista em CrossFit e treinamento funcional. '
    'Identifique o movimento de cada item pelo contexto do dia e do bloco. '
    'Escolha apenas um slug da lista canonica e seus aliases. '
    'Se a linha contiver mais de um movimento, for apenas uma instrucao, ou nao houver '
    'correspondencia segura, use slug vazio. '
    'Nao altere numeros, repeticoes, cargas ou o texto original. '
    'Responda cada id recebido uma unica vez, no formato JSON solicitado.'
)

_OUTPUT_SCHEMA = {
    'type': 'object',
    'properties': {
        'items': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {'id': {'type': 'integer'}, 'slug': {'type': 'string'}},
                'required': ['id', 'slug'],
                'additionalProperties': False,
            },
        },
    },
    'required': ['items'],
    'additionalProperties': False,
}


def _normalize_lookup_text(text: str) -> str:
    """Normaliza texto pra chave de memoria: minusculo, sem acento, sem pontuacao."""
    decomposed = unicodedata.normalize('NFKD', text or '')
    without_accents = ''.join(ch for ch in decomposed if not unicodedata.combining(ch))
    collapsed = re.sub(r'[^a-z0-9]+', ' ', without_accents.lower()).strip()
    return collapsed[:160]


def _lookup_learned_aliases(names: list[str]) -> dict[str, dict[str, str]]:
    """Consulta a memoria compartilhada por nomes ja aprendidos. Nunca lanca excecao."""
    normalized_to_names: dict[str, list[str]] = {}
    for name in names:
        normalized_to_names.setdefault(_normalize_lookup_text(name), []).append(name)

    result: dict[str, dict[str, str]] = {}
    try:
        from knowledge.models import WodMovementLearnedAlias

        matches = WodMovementLearnedAlias.objects.filter(raw_text_normalized__in=list(normalized_to_names))
        hit_ids = []
        for alias in matches:
            for original_name in normalized_to_names.get(alias.raw_text_normalized, []):
                result[original_name] = {'slug': alias.movement_slug, 'note': alias.note}
            hit_ids.append(alias.id)
        if hit_ids:
            WodMovementLearnedAlias.objects.filter(id__in=hit_ids).update(
                hit_count=models.F('hit_count') + 1
            )
    except Exception as exc:
        logger.debug('wod_slug_resolver: memoria aprendida indisponivel (%s), seguindo sem ela.', exc)
    return result


def _remember_resolved_aliases(resolved: dict[str, dict[str, str]]) -> None:
    """Grava resolucoes novas do LLM na memoria compartilhada. Nunca lanca excecao."""
    if not resolved:
        return
    try:
        from knowledge.models import WodMovementLearnedAlias

        for raw_name, entry in resolved.items():
            slug = entry.get('slug')
            if not slug:
                continue
            normalized = _normalize_lookup_text(raw_name)
            if not normalized:
                continue
            WodMovementLearnedAlias.objects.update_or_create(
                raw_text_normalized=normalized,
                defaults={
                    'raw_text_sample': raw_name[:160],
                    'movement_slug': slug,
                    'note': (entry.get('note') or '')[:200],
                },
            )
    except Exception as exc:
        logger.debug('wod_slug_resolver: falha ao gravar memoria aprendida (%s), ignorando.', exc)


def resolve_unknown_slugs(
    *,
    unrecognized_names: list[str],
    slug_dictionary: list[tuple[str, tuple[str, ...]]],
) -> dict[str, dict[str, str]]:
    """Tenta resolver slugs para nomes nao reconhecidos pelo dicionario deterministico.

    Primeiro consulta a memoria aprendida (nomes ja resolvidos antes, em qualquer box);
    so chama o LLM para o que sobrar, e grava o que ele resolver para a proxima vez.

    Args:
        unrecognized_names: lista de nomes de movimento nao resolvidos (texto livre do coach).
        slug_dictionary: dicionario canonico carregado por load_wod_movement_dictionary().

    Returns:
        Dicionario {nome_raw: {"slug": slug_canonico, "note": nota_curta}}.
        Pode ser vazio se LLM nao estiver disponivel e nada estiver na memoria.
    """
    resolved, _status = _resolve_unknown_slugs_with_status(
        unrecognized_names=unrecognized_names,
        slug_dictionary=slug_dictionary,
    )
    return resolved


def _resolve_unknown_slugs_with_status(
    *,
    unrecognized_names: list[str],
    slug_dictionary: list[tuple[str, tuple[str, ...]]],
    contexts: dict[str, str] | None = None,
) -> tuple[dict[str, dict[str, str]], dict[str, object]]:
    """Resolve with Haiku and return safe, user-displayable outcome metadata."""
    status: dict[str, object] = {
        'provider': 'haiku',
        'state': 'not_needed',
        'candidate_count': len(unrecognized_names),
        'resolved_count': 0,
    }
    if not unrecognized_names:
        return {}, status

    valid_slugs = {slug for slug, _ in slug_dictionary}
    if not valid_slugs:
        status['state'] = 'dictionary_unavailable'
        return {}, status

    learned = {
        name: entry for name, entry in _lookup_learned_aliases(unrecognized_names).items()
        if entry.get('slug') in valid_slugs
    }
    still_unknown = [name for name in unrecognized_names if name not in learned]
    status['memory_resolved_count'] = len(unrecognized_names) - len(still_unknown)
    status['resolved_count'] = len(unrecognized_names) - len(still_unknown)
    if not still_unknown:
        status['state'] = 'memory_resolved'
        return learned, status

    if len(still_unknown) > _MAX_NAMES_PER_CALL:
        status['state'] = 'limit_exceeded'
        status['haiku_candidate_count'] = len(still_unknown)
        logger.warning(
            'wod_slug_resolver: %d nomes nao reconhecidos (limite %d); pulando chamada Haiku.',
            len(still_unknown), _MAX_NAMES_PER_CALL,
        )
        return learned, status

    dictionary_text = '\n'.join(
        f'{slug}: {", ".join(aliases)}' for slug, aliases in slug_dictionary
    )
    static_block = f'{_STATIC_INSTRUCTIONS}\n\nDicionario canonico:\n{dictionary_text}'

    anthropic_key = os.getenv('ANTHROPIC_API_KEY', '').strip()

    if not anthropic_key:
        status['state'] = 'provider_unavailable'
        status['haiku_candidate_count'] = len(still_unknown)
        logger.warning(
            'wod_slug_resolver: Haiku unavailable (ANTHROPIC_API_KEY missing); '
            '%d item(s) require manual review.',
            len(still_unknown),
        )
        return learned, status

    status['haiku_attempted'] = True
    status['haiku_candidate_count'] = len(still_unknown)
    from_llm: dict[str, dict[str, str]] = {}
    failed_batches = 0
    for offset in range(0, len(still_unknown), _NAMES_PER_BATCH):
        batch = still_unknown[offset:offset + _NAMES_PER_BATCH]
        items = [
            {'id': index, 'texto': name, 'contexto': (contexts or {}).get(name, '')[:160]}
            for index, name in enumerate(batch)
        ]
        raw_text = _call_anthropic(
            static_block=static_block,
            dynamic_block='Identifique os itens por id:\n' + json.dumps(items, ensure_ascii=False),
            api_key=anthropic_key,
        )
        if not raw_text or not raw_text.strip():
            failed_batches += 1
            continue
        from_llm.update(_parse_and_validate(
            raw_text=raw_text,
            valid_slugs=valid_slugs,
            unrecognized_names=batch,
        ))

    _remember_resolved_aliases(from_llm)
    status['resolved_count'] = len(learned) + len(from_llm)
    status['haiku_batch_count'] = (len(still_unknown) + _NAMES_PER_BATCH - 1) // _NAMES_PER_BATCH
    status['haiku_failed_batch_count'] = failed_batches
    status['state'] = (
        'haiku_resolved' if len(from_llm) == len(still_unknown)
        else 'haiku_partial' if from_llm
        else 'provider_error' if failed_batches == status['haiku_batch_count']
        else 'haiku_no_match'
    )
    return {**learned, **from_llm}, status


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

    unrecognized_names = list(dict.fromkeys(name for _, _, _, name in unresolved))
    contexts = {}
    for day_idx, block_idx, _mov_idx, raw_name in unresolved:
        day = days[day_idx]
        block = day['blocks'][block_idx]
        contexts.setdefault(
            raw_name,
            f"{day.get('weekday_label', '')} · {block.get('title') or block.get('kind', '')}",
        )
    resolved, resolution_status = _resolve_unknown_slugs_with_status(
        unrecognized_names=unrecognized_names,
        slug_dictionary=slug_dictionary,
        contexts=contexts,
    )

    parsed_payload['movement_resolution'] = resolution_status

    for day_idx, block_idx, mov_idx, raw_name in unresolved:
        entry = resolved.get(raw_name) or {}
        slug = entry.get('slug')
        if slug:
            movement = days[day_idx]['blocks'][block_idx]['movements'][mov_idx]
            movement['movement_slug'] = slug
            movement['llm_resolved'] = True
            movement['llm_fix_note'] = entry.get('note') or f'Ajustado automaticamente para "{slug}".'
    # Keep logs aggregate and privacy-safe: pasted workouts may contain user data.
    logger.info(
        'wod_slug_resolver: state=%s candidates=%s resolved=%s',
        resolution_status.get('state'),
        resolution_status.get('candidate_count'),
        resolution_status.get('resolved_count'),
    )


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

def _call_anthropic(*, static_block: str, dynamic_block: str, api_key: str) -> str | None:
    # The dictionary is static and the indexed candidate list changes per paste.
    try:
        headers = {
            'x-api-key': api_key,
            'anthropic-version': _ANTHROPIC_API_VERSION,
            'Content-Type': 'application/json',
        }
        workspace_id = os.getenv('ANTHROPIC_WORKSPACE_ID', '').strip()
        if workspace_id:
            headers['anthropic-workspace-id'] = workspace_id
        response = requests.post(
            _ANTHROPIC_MESSAGES_URL,
            headers=headers,
            json={
                'model': _ANTHROPIC_MODEL,
                'max_tokens': _MAX_OUTPUT_TOKENS,
                'output_config': {'format': {'type': 'json_schema', 'schema': _OUTPUT_SCHEMA}},
                'system': [
                    {
                        'type': 'text',
                        'text': static_block,
                    },
                ],
                'messages': [{'role': 'user', 'content': dynamic_block}],
            },
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        if data.get('stop_reason') in {'max_tokens', 'model_context_window_exceeded'}:
            logger.warning('wod_slug_resolver: resposta Haiku truncada (%s).', data['stop_reason'])
            return None
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
) -> dict[str, dict[str, str]]:
    """Accept indexed structured output and legacy name-keyed output safely."""
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

    if not isinstance(mapping, dict):
        return {}
    result: dict[str, dict[str, str]] = {}
    indexed_items = mapping.get('items')
    if isinstance(indexed_items, list):
        for item in indexed_items:
            if not isinstance(item, dict):
                continue
            index = item.get('id')
            slug = item.get('slug')
            if type(index) is not int or not 0 <= index < len(unrecognized_names):
                continue
            if not isinstance(slug, str) or slug not in valid_slugs:
                continue
            original_name = unrecognized_names[index]
            result[original_name] = {
                'slug': slug,
                'note': f'Identificado automaticamente como {slug.replace("_", " ")}.',
            }
        return result

    unrecognized_lower = {name.lower(): name for name in unrecognized_names}
    for key, value in mapping.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, dict):
            slug = str(value.get('slug') or '').strip()
            note = str(value.get('note') or '').strip()
        elif isinstance(value, str):
            slug = value.strip()
            note = ''
        else:
            continue
        original_name = unrecognized_lower.get(key.lower())
        if original_name is None:
            continue
        # Aceitar apenas slugs que existem no dicionario canonico
        if slug and slug in valid_slugs:
            result[original_name] = {'slug': slug, 'note': note}
        elif slug:
            logger.debug('wod_slug_resolver: slug "%s" retornado para "%s" nao existe no dicionario.', slug, key)

    return result


__all__ = ['resolve_unknown_slugs', 'apply_llm_slug_resolution']
