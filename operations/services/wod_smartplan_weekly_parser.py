"""
ARQUIVO: conversor de saída SmartPlan semanal para o formato interno do Smart Paste.

POR QUE ELE EXISTE:
- o GPT SmartPlan devolve um JSON com todos os blocos da semana em uma lista plana.
- o Smart Paste espera dias agrupados com lista de blocos cada um.
- este arquivo conecta os dois formatos sem exigir dois fluxos distintos para o coach.

O QUE ESTE ARQUIVO FAZ:
1. detect_and_convert_smartplan_weekly(text): ponto de entrada — chama detect_smartplan_format()
   e, se detectado, converte para parsed_payload compatível com Smart Paste.
2. Agrupa blocos pelo dia extraído do título ("SEGUNDA-FEIRA — Força" → dia 0).
3. Mapeia campos SmartPlan (slug, reps, load_pct_rm) para campos Smart Paste
   (movement_slug, reps_spec, load_spec).

PONTOS CRÍTICOS:
- retorna None se o texto não for formato SmartPlan (fallback transparente para o parser de texto).
- movimentos com `slug` preenchido chegam com `movement_slug` não vazio → chips verdes direto.
- falha silenciosa: qualquer erro de parsing retorna None.
"""

from __future__ import annotations

import logging

from .wod_normalization.response_parser import (
    END_MARKER,
    JSON_MARKER,
    TEXT_MARKER,
    detect_smartplan_format,
    detect_smartplan_text_format,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapeamento de dias
# ---------------------------------------------------------------------------

_DAY_TOKENS: list[tuple[str, int, str]] = [
    ('SEGUNDA-FEIRA', 0, 'Segunda'),
    ('SEGUNDA', 0, 'Segunda'),
    ('TERÇA-FEIRA', 1, 'Terca'),
    ('TERCA-FEIRA', 1, 'Terca'),
    ('TERÇA', 1, 'Terca'),
    ('TERCA', 1, 'Terca'),
    ('QUARTA-FEIRA', 2, 'Quarta'),
    ('QUARTA', 2, 'Quarta'),
    ('QUINTA-FEIRA', 3, 'Quinta'),
    ('QUINTA', 3, 'Quinta'),
    ('SEXTA-FEIRA', 4, 'Sexta'),
    ('SEXTA', 4, 'Sexta'),
    ('SÁBADO', 5, 'Sabado'),
    ('SABADO', 5, 'Sabado'),
    ('DOMINGO', 6, 'Domingo'),
]

# Mapeamento de tipo SmartPlan → kind Smart Paste
_TYPE_MAP: dict[str, str] = {
    'strength': 'metcon',
    'amrap': 'metcon',
    'emom': 'metcon',
    'for_time': 'metcon',
    'skill': 'skill',
    'mobility': 'mobility',
    'warmup': 'warmup',
    'cooldown': 'cooldown',
    'metcon': 'metcon',
}


# ---------------------------------------------------------------------------
# Ponto de entrada público
# ---------------------------------------------------------------------------

def detect_and_convert_smartplan_weekly(text: str) -> dict | None:
    """Tenta detectar e converter uma saída SmartPlan semanal para parsed_payload Smart Paste.

    Returns:
        dict compatível com Smart Paste (chaves: days, week_label, parse_warnings, source_format)
        ou None se o texto não for formato SmartPlan.
    """
    if not text:
        return None

    if JSON_MARKER not in text:
        # SmartPlan v2 intentionally returns readable normalized text only.
        # Return it as a typed input for the weekly Haiku normalizer; do not
        # send a marked SmartPlan response through the legacy freeform parser.
        if TEXT_MARKER not in text and END_MARKER not in text:
            return None
        result = detect_smartplan_text_format(text)
        if not result.get('is_normalized'):
            reason = result.get('reason')
            message = (
                'A resposta do SmartPlan precisa conter os marcadores '
                '“=== WOD NORMALIZADO ===” e “=== FIM ===”, com o treino entre eles.'
                if reason == 'markers_missing'
                else 'A seção WOD NORMALIZADO está vazia.'
            )
            return {
                'week_label': None,
                'parse_warnings': [],
                'parse_errors': [message],
                'days': [],
                'source_format': 'smartplan_text_v2',
            }
        return {
            'week_label': None,
            'parse_warnings': [],
            'parse_errors': [],
            'days': [],
            'normalized_text': result['normalized_text'],
            'source_format': 'smartplan_text_v2',
        }

    result = detect_smartplan_format(text)
    if not result.get('is_normalized'):
        logger.debug(
            'wod_smartplan_weekly_parser: formato SmartPlan detectado mas inválido (%s)',
            result.get('reason'),
        )
        reason_messages = {
            'markers_missing': 'A resposta do SmartPlan está sem as seções obrigatórias.',
            'text_empty': 'A seção WOD NORMALIZADO está vazia.',
            'json_not_found': 'Não encontrei o JSON estruturado da semana.',
            'json_invalid': 'O JSON estruturado está malformado.',
            'blocks_missing': 'A resposta não contém a lista de treinos por dia.',
            'blocks_empty': 'A resposta não contém blocos de treino.',
        }
        return {
            'week_label': None,
            'parse_warnings': [],
            'parse_errors': [reason_messages.get(result.get('reason'), 'A estrutura do SmartPlan é inválida.')],
            'days': [],
            'source_format': 'smartplan_json',
        }

    structured = result['structured_payload']
    try:
        return _build_smart_paste_payload(structured)
    except Exception as exc:
        logger.warning('wod_smartplan_weekly_parser: erro ao converter payload: %s', exc)
        return {
            'week_label': None,
            'parse_warnings': [],
            'parse_errors': ['Não foi possível interpretar a estrutura dos blocos do SmartPlan.'],
            'days': [],
            'source_format': 'smartplan_json',
        }


# ---------------------------------------------------------------------------
# Conversão interna
# ---------------------------------------------------------------------------

def _detect_day_from_title(title: str) -> tuple[int, str] | None:
    """Retorna o dia somente quando o título identifica exatamente um dia."""
    title_norm = title.upper()
    # Deduplica variantes com/sem acento e forma curta/longa do mesmo dia.
    # Dois dias distintos no mesmo título são ambíguos e não escolhemos o
    # primeiro da lista silenciosamente.
    matches = {
        (weekday, label)
        for token, weekday, label in _DAY_TOKENS
        if token in title_norm
    }
    return next(iter(matches)) if len(matches) == 1 else None


def _block_title_without_day(title: str) -> str:
    """Remove o prefixo de dia do título — 'SEGUNDA-FEIRA — Força' → 'Força'."""
    if ' — ' in title:
        parts = title.split(' — ', 1)
        if len(parts) == 2:
            return parts[1].strip()
    if ' - ' in title:
        parts = title.split(' - ', 1)
        if len(parts) == 2:
            return parts[1].strip()
    return title.strip()


def _build_format_spec(block: dict) -> str:
    """Monta uma descrição legível do formato do bloco."""
    btype = block.get('type', '')
    duration = block.get('duration_min')
    rounds = block.get('rounds')

    if btype == 'amrap' and duration:
        return f'AMRAP {duration} min'
    if btype == 'emom' and duration:
        return f'EMOM {duration} min'
    if btype == 'for_time':
        return 'For Time'
    if btype == 'strength' and rounds:
        return f'{rounds} séries'
    if btype == 'skill' and rounds:
        return f'{rounds} séries (técnica)'
    return ''


def _build_load_spec(movement: dict) -> str | None:
    """Constrói load_spec a partir dos campos SmartPlan."""
    load_pct_rm = movement.get('load_pct_rm')
    load_kg = movement.get('load_kg')
    load_note = (movement.get('load_note') or '').strip()

    if load_pct_rm:
        base = f'{load_pct_rm}% RM'
        rm_exercise = (movement.get('load_pct_rm_exercise') or '').strip()
        if rm_exercise and rm_exercise != movement.get('slug', ''):
            base += f' {rm_exercise}'
        return base
    if load_kg:
        return f'{load_kg}kg'
    # "free" e variantes indicam carga livre — não é uma spec de carga real
    if load_note and load_note.lower() not in ('free', 'livre', 'carga livre'):
        return load_note
    return None


def _convert_movement(m: dict) -> dict:
    """Converte um movimento SmartPlan para o formato Smart Paste."""
    reps = m.get('reps')
    return {
        'movement_slug': (m.get('slug') or '').strip(),
        'movement_label_raw': (m.get('label_pt') or m.get('label_en') or '').strip(),
        'sets': m.get('sets'),
        'reps_spec': str(reps) if reps is not None else None,
        'load_spec': _build_load_spec(m),
        'is_scaled_alternative': bool(m.get('is_scaled_alternative', False)),
        'notes': (m.get('notes') or '').strip() or None,
        'sort_order': m.get('order', 0),
    }


def _build_smart_paste_payload(structured: dict) -> dict:
    """Converte structured_payload (SmartPlan) para parsed_payload (Smart Paste)."""
    blocks_raw: list[dict] = structured.get('blocks') or []
    session_warnings: list[str] = structured.get('session_warnings') or []

    # Agrupar blocos por dia — dict weekday → day_dict
    days_map: dict[int, dict] = {}
    unrooted_blocks: list[str] = []  # blocos sem um único dia identificável
    parse_errors: list[str] = []

    for block in blocks_raw:
        title = block.get('title', '')
        day_info = _detect_day_from_title(title)

        kind = _TYPE_MAP.get(block.get('type', ''), 'metcon')
        block_title = _block_title_without_day(title)
        movements = [_convert_movement(m) for m in (block.get('movements') or [])]
        warnings = block.get('warnings') or []

        converted_block = {
            'kind': kind,
            'title': block_title,
            'format_spec': _build_format_spec(block),
            'rounds': block.get('rounds'),
            'timecap_min': block.get('duration_min'),
            'notes': '; '.join(warnings) if warnings else None,
            'movements': movements,
        }

        if day_info is None:
            unrooted_blocks.append(title.strip() or 'bloco sem título')
            continue

        weekday, label = day_info
        if weekday not in days_map:
            days_map[weekday] = {
                'weekday': weekday,
                'weekday_label': label,
                'blocks': [],
            }
        days_map[weekday]['blocks'].append(converted_block)

    # Sem dia, ou com mais de um dia, não há base segura para distribuir.
    # Os demais dias continuam revisáveis, mas a confirmação será bloqueada.
    if unrooted_blocks:
        parse_errors.extend(
            f'Não foi possível identificar um único dia no bloco “{title}”.'
            for title in unrooted_blocks
        )

    days = [days_map[k] for k in sorted(days_map.keys())]

    return {
        'week_label': None,
        'parse_warnings': session_warnings,
        'parse_errors': parse_errors,
        'days': days,
        'source_format': 'smartplan_json',
    }


__all__ = ['detect_and_convert_smartplan_weekly']
