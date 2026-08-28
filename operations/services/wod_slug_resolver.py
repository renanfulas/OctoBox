"""
ARQUIVO: resolvedor de slugs de movimentos via LLM para o Smart Paste semanal.

POR QUE ELE EXISTE:
- o dicionario de 104 movimentos nao cobre 100% dos textos reais dos coaches.
- quando o parser deterministico nao reconhece um movimento, este servico tenta resolver via LLM.
- resultado: zero chips vermelhos para a maioria dos treinos sem exigir revisao manual.

O QUE ESTE ARQUIVO FAZ:
1. recebe lista de nomes de movimento nao reconhecidos.
2. consulta primeiro a memoria aprendida (knowledge.WodMovementLearnedAlias, compartilhada
   entre boxes) — nome ja visto antes resolve na hora, sem chamar LLM.
3. o que sobrar vai pro Anthropic (claude-haiku) ou OpenAI (gpt-4o-mini) com o dicionario completo.
4. toda resolucao nova do LLM e gravada na memoria, pra nao pagar de novo pelo mesmo erro comum.
5. retorna dict {nome_raw: {"slug": slug_canonico, "note": nota_curta_pt_br}}.
6. falha silenciosamente (retorna {}) quando LLM nao esta configurado ou falha; erro na
   memoria (tabela sem migration aplicada, banco fora) tambem nunca derruba o fluxo.

PONTOS CRITICOS:
- nao lanca excecao: qualquer falha retorna {} e o comportamento original e preservado.
- slugs retornados pelo LLM sao validados contra o dicionario antes de serem aplicados.
- timeout curto (8s) para nao bloquear o render da pagina.
- usa ANTHROPIC_API_KEY por padrao (provedor escolhido no design), fallback para OPENAI_API_KEY
  quando so essa estiver configurada. Nao inverter: OPENAI_API_KEY costuma estar setada em
  producao so por causa do RAG (knowledge/embeddings.py), o que faria o Haiku nunca rodar.
- a "note" e so um resumo em linguagem natural da troca feita (ex.: "Troquei 'agachamnto'
  por Back Squat") para exibir no preview do Smart Paste — nunca usada para alterar dado
  numerico (reps/carga), so texto de UI.
- o dicionario de slugs + instrucoes (parte estatica) vai em bloco cacheado
  (cache_control: ephemeral) na chamada Anthropic — so a lista de nomes nao reconhecidos
  muda a cada chamada, entao o cache reduz custo/latencia quando a memoria nao cobre tudo.
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

_OPENAI_CHAT_URL = 'https://api.openai.com/v1/chat/completions'
_ANTHROPIC_MESSAGES_URL = 'https://api.anthropic.com/v1/messages'
_ANTHROPIC_API_VERSION = '2023-06-01'
_TIMEOUT_SECONDS = 8
_OPENAI_MODEL = 'gpt-4o-mini'
_ANTHROPIC_MODEL = 'claude-haiku-4-5-20251001'

# Um treino real de uma semana tem no maximo ~60-80 movimentos ao todo; mais que
# isso sobrando sem slug depois do parser deterministico + memoria aprendida e
# sinal de spam/lixo colado, nao de treino. Corta antes de gastar chamada de LLM.
_MAX_NAMES_PER_CALL = 40


_STATIC_INSTRUCTIONS = (
    'Voce e um especialista em CrossFit e treinamento funcional. '
    'Voce recebe uma lista de movimentos extraidos de um treino em portugues ou ingles '
    'que nao foram reconhecidos pelo dicionario interno (geralmente por erro de digitacao, '
    'sinonimo ou abreviacao). '
    'Para cada movimento, identifique o slug canonico mais proximo da lista de slugs validos fornecida. '
    'Se nao houver correspondencia razoavel, use string vazia "" no slug.\n\n'
    'Alem do slug, escreva uma nota curta em portugues (menos de 12 palavras) explicando a troca '
    'de forma natural para o coach ler, ex.: "Troquei \'agachamnto\' por Back Squat". '
    'Se o slug ficar vazio, a nota deve dizer que nao encontrou correspondencia. '
    'NUNCA invente ou corrija numero (reps, carga, series) — isso nao e sua tarefa aqui, '
    'so identificacao de movimento.\n\n'
    'Responda SOMENTE com um objeto JSON valido no formato:\n'
    '{"nome do movimento": {"slug": "slug_canonico", "note": "nota curta em pt-br"}}\n'
    'Sem explicacoes, sem markdown, apenas o JSON.'
)


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
    if not unrecognized_names:
        return {}

    valid_slugs = {slug for slug, _ in slug_dictionary}
    if not valid_slugs:
        return {}

    learned = _lookup_learned_aliases(unrecognized_names)
    still_unknown = [name for name in unrecognized_names if name not in learned]
    if not still_unknown:
        return learned

    if len(still_unknown) > _MAX_NAMES_PER_CALL:
        logger.warning(
            'wod_slug_resolver: %d nomes nao reconhecidos (limite %d) — '
            'provavel texto fora do escopo de treino, pulando chamada LLM.',
            len(still_unknown), _MAX_NAMES_PER_CALL,
        )
        return learned

    all_slugs_text = ', '.join(sorted(valid_slugs))
    names_text = '\n'.join(f'- {name}' for name in still_unknown)
    static_block = f'{_STATIC_INSTRUCTIONS}\n\nSlugs validos:\n{all_slugs_text}'
    dynamic_block = f'Movimentos para resolver:\n{names_text}'

    openai_key = os.getenv('OPENAI_API_KEY', '').strip()
    anthropic_key = os.getenv('ANTHROPIC_API_KEY', '').strip()

    # Anthropic (Haiku) tem prioridade: e o provedor escolhido no design (docs/plans/wod-smart-paste-corda.md).
    # OPENAI_API_KEY costuma estar setada em producao por causa do RAG (knowledge/embeddings.py exige),
    # entao nao pode ser o desempate — senao o Haiku nunca roda mesmo quando configurado.
    raw_text = None
    if anthropic_key:
        raw_text = _call_anthropic(static_block=static_block, dynamic_block=dynamic_block, api_key=anthropic_key)
    elif openai_key:
        raw_text = _call_openai(prompt=f'{static_block}\n\n{dynamic_block}', api_key=openai_key)
    else:
        logger.debug('wod_slug_resolver: nenhuma chave LLM configurada, usando so a memoria.')
        return learned

    if not raw_text:
        return learned

    from_llm = _parse_and_validate(
        raw_text=raw_text,
        valid_slugs=valid_slugs,
        unrecognized_names=still_unknown,
    )
    _remember_resolved_aliases(from_llm)
    return {**learned, **from_llm}


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
        entry = resolved.get(raw_name) or {}
        slug = entry.get('slug')
        if slug:
            movement = days[day_idx]['blocks'][block_idx]['movements'][mov_idx]
            movement['movement_slug'] = slug
            movement['llm_resolved'] = True
            movement['llm_fix_note'] = entry.get('note') or f'Ajustado automaticamente para "{slug}".'
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


def _call_anthropic(*, static_block: str, dynamic_block: str, api_key: str) -> str | None:
    # static_block (instrucoes + dicionario de slugs) e identico entre chamadas na mesma
    # sessao de paste — cache_control:ephemeral evita reprocessar/repagar esses tokens
    # a cada linha nao reconhecida. So dynamic_block (nomes a resolver) muda.
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
                'system': [
                    {
                        'type': 'text',
                        'text': static_block,
                        'cache_control': {'type': 'ephemeral'},
                    },
                ],
                'messages': [{'role': 'user', 'content': dynamic_block}],
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
) -> dict[str, dict[str, str]]:
    """Extrai e valida o JSON retornado pelo LLM.

    Aceita tanto o formato novo ({"nome": {"slug": ..., "note": ...}}) quanto o
    formato antigo ({"nome": "slug"}) — mantem compatibilidade com respostas de
    modelos que ignorem a instrucao de incluir "note".
    """
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

    result: dict[str, dict[str, str]] = {}
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
        original_name = unrecognized_lower.get(key.lower(), key)
        # Aceitar apenas slugs que existem no dicionario canonico
        if slug and slug in valid_slugs:
            result[original_name] = {'slug': slug, 'note': note}
        elif slug:
            logger.debug('wod_slug_resolver: slug "%s" retornado para "%s" nao existe no dicionario.', slug, key)

    return result


__all__ = ['resolve_unknown_slugs', 'apply_llm_slug_resolution']
