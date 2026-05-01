"""
ARQUIVO: parser do output do GPT SmartPlan colado pelo owner.

POR QUE ELE EXISTE:
- valida que o texto colado segue o formato canonico definido em prompts/smartplan_v1.md.
- separa texto humano (`=== WOD NORMALIZADO ===`) e estrutura (`=== JSON ESTRUTURADO ===`).
- bloqueia silenciosamente paste cru sem precisar de chamada externa.

O QUE ESTE ARQUIVO FAZ:
1. expoe `detect_smartplan_format(raw_text)` que retorna dict com flags e payload.
2. extrai secoes entre marcadores fixos.
3. parseia JSON (tolerante a code fence ```json).

PONTOS CRITICOS:
- nao chamar API externa daqui; o trabalho e parsing local de <100ms.
- mudanca de marcadores aqui exige bump de prompt_version e atualizacao do GPT.
- JSON com `blocks` ausente ou vazio e considerado invalido (tier rico precisa de blocos).
"""

from __future__ import annotations

import json
import re

TEXT_MARKER = '=== WOD NORMALIZADO ==='
JSON_MARKER = '=== JSON ESTRUTURADO ==='
END_MARKER = '=== FIM ==='

REASON_MARKERS_MISSING = 'markers_missing'
REASON_TEXT_EMPTY = 'text_empty'
REASON_JSON_NOT_FOUND = 'json_not_found'
REASON_JSON_INVALID = 'json_invalid'
REASON_BLOCKS_MISSING = 'blocks_missing'
REASON_BLOCKS_EMPTY = 'blocks_empty'


def detect_smartplan_format(raw_text: str) -> dict:
    """Detecta se `raw_text` segue o formato canonico do SmartPlan.

    Retorna sempre um dict com a chave `is_normalized` (bool) e, em caso de falha,
    `reason` para diagnostico. Em caso de sucesso, devolve `normalized_text` e
    `structured_payload`.
    """
    if not raw_text or not raw_text.strip():
        return {'is_normalized': False, 'reason': REASON_MARKERS_MISSING}

    if TEXT_MARKER not in raw_text or JSON_MARKER not in raw_text:
        return {'is_normalized': False, 'reason': REASON_MARKERS_MISSING}

    normalized_text = _extract_section(raw_text, TEXT_MARKER, JSON_MARKER)
    if not normalized_text:
        return {'is_normalized': False, 'reason': REASON_TEXT_EMPTY}

    json_block = _extract_section(raw_text, JSON_MARKER, END_MARKER)
    if not json_block:
        return {'is_normalized': False, 'reason': REASON_JSON_NOT_FOUND}

    try:
        structured = json.loads(_strip_code_fence(json_block))
    except (ValueError, json.JSONDecodeError) as exc:
        return {
            'is_normalized': False,
            'reason': REASON_JSON_INVALID,
            'detail': str(exc),
        }

    blocks = structured.get('blocks') if isinstance(structured, dict) else None
    if blocks is None:
        return {'is_normalized': False, 'reason': REASON_BLOCKS_MISSING}
    if not blocks:
        return {'is_normalized': False, 'reason': REASON_BLOCKS_EMPTY}

    return {
        'is_normalized': True,
        'normalized_text': normalized_text.strip(),
        'structured_payload': structured,
    }


def _extract_section(raw_text: str, start_marker: str, end_marker: str) -> str:
    """Extrai conteudo entre `start_marker` e `end_marker`. Se `end_marker` ausente,
    pega ate o fim do texto."""
    start_idx = raw_text.find(start_marker)
    if start_idx < 0:
        return ''
    content_start = start_idx + len(start_marker)
    end_idx = raw_text.find(end_marker, content_start)
    if end_idx < 0:
        return raw_text[content_start:].strip()
    return raw_text[content_start:end_idx].strip()


_CODE_FENCE_RE = re.compile(r'^```(?:json)?\s*\n?(.*?)\n?```$', re.DOTALL)


def _strip_code_fence(text: str) -> str:
    """Remove ``` ou ```json wrap se presente."""
    text = text.strip()
    match = _CODE_FENCE_RE.match(text)
    if match:
        return match.group(1).strip()
    return text


__all__ = [
    'detect_smartplan_format',
    'TEXT_MARKER',
    'JSON_MARKER',
    'END_MARKER',
    'REASON_MARKERS_MISSING',
    'REASON_TEXT_EMPTY',
    'REASON_JSON_NOT_FOUND',
    'REASON_JSON_INVALID',
    'REASON_BLOCKS_MISSING',
    'REASON_BLOCKS_EMPTY',
]
