"""
ARQUIVO: parser de Smart Paste para texto "cru" de coach (SEM cabecalhos de bloco).

POR QUE ELE EXISTE:
- o parser canonico (wod_paste_parser.parse_weekly_wod_text) exige cabecalhos explicitos
  ("Aquecimento", "WOD", "Mobilidade", "Skill", "Cooldown") e ignora linhas em branco.
- coach real cola texto sem esses cabecalhos: blocos separados por LINHA EM BRANCO + uma
  LINHA DE ESQUEMA ("3x", "5 rounds", "Emom", "Cap 16'", "Tabata", "20-30-40-30-20",
  "Hyrox"), com aquecimento implicito ("Alongar bem").
- este modulo organiza esse texto em dias -> blocos -> movimentos, com o MESMO schema do
  parser canonico, para nao mexer no resto do pipeline (preview, revisao, projecao).

O QUE ESTE ARQUIVO FAZ:
1. parse_weekly_wod_freeform(text): segmenta por dia (linha de dia) e por bloco (linha em
   branco), detecta esquema do bloco, extrai movimentos e PRESERVA notas (parenteses,
   *asteriscos*, "Subindo a carga", "Then"). Nada some em silencio.
2. _freeform_should_take_over(parsed): gate para a view decidir se cai neste parser quando o
   parser com cabecalho nao rendeu estrutura.

PONTOS CRITICOS:
- nao autocorrige: movimento que nao casa no dicionario fica com movement_slug vazio e vai
  para o fluxo de revisao (chips) existente.
- reusa helpers de wod_paste_parser (sem duplicar logica de movimento/dia/metadata).
- funcao pura e idempotente: parsear duas vezes o mesmo texto da o mesmo payload.
"""

from __future__ import annotations

import re

from operations.services.wod_paste_parser import (
    _build_block,
    _build_day,
    _is_block_note_candidate,
    _match_weekday,
    _normalize_token,
    _parse_block_metadata,
    _parse_movement_line,
    resolve_movement_slug,
)

# ---------------------------------------------------------------------------
# Deteccao de marcadores
# ---------------------------------------------------------------------------

_STAR_RE = re.compile(r'\*([^*]+)\*')
_PAREN_RE = re.compile(r'\(([^()]*)\)')
_PERCENT_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s*%')
_LADDER_RE = re.compile(r'\d+(?:-\d+)+')
_LEADING_DIGIT_RE = re.compile(r'^\d')

# Fallback para dias escritos como "Terça-feira": _normalize_token troca '-' por espaco, e os
# aliases do parser canonico tem hifen, entao "terca feira" nao casa la. Aqui removemos o
# sufixo " feira" e casamos pelo token nu do dia.
_WEEKDAY_BY_TOKEN = {
    'segunda': (0, 'Segunda'),
    'terca': (1, 'Terca'),
    'quarta': (2, 'Quarta'),
    'quinta': (3, 'Quinta'),
    'sexta': (4, 'Sexta'),
    'sabado': (5, 'Sabado'),
    'domingo': (6, 'Domingo'),
}


def _match_weekday_line(line: str):
    """Casa uma linha de dia da semana, tolerando o sufixo '-feira'."""
    direct = _match_weekday(line)
    if direct is not None:
        return direct
    norm = re.sub(r'\s*feira$', '', _normalize_token(line.rstrip(':'))).strip()
    return _WEEKDAY_BY_TOKEN.get(norm)


def _warmup_kind(norm: str) -> str | None:
    """Retorna 'mobility'/'warmup' se a linha for um marcador de aquecimento, senao None."""
    if norm.startswith('along') or norm.startswith('mobil'):
        return 'mobility'
    if norm.startswith('aquec') or norm.startswith('warm'):
        return 'warmup'
    return None


def _is_skill_marker(norm: str) -> bool:
    return norm == 'skill' or norm.startswith('skill ')


def _is_note_line(raw: str, norm: str) -> bool:
    """Linha que e nota pura (nao bloco, nao movimento)."""
    stripped = raw.strip()
    if not stripped:
        return False
    if stripped.startswith('(') and stripped.endswith(')'):
        return True
    if stripped.startswith('*') and stripped.endswith('*'):
        return True
    if norm == 'then':
        return True
    if _is_block_note_candidate(stripped):
        return True
    return False


def _detect_scheme(text: str):
    """Detecta uma linha de esquema de bloco.

    Retorna (metadata: dict, kind_hint: str) ou None. kind_hint em
    {'metcon', 'rounds', 'ladder'}; o kind final do bloco e decidido em _finalize_kind.
    """
    norm = _normalize_token(text)
    if not norm:
        return None

    if norm == 'tabata' or norm.startswith('tabata'):
        return {'format_spec': text.strip(), 'score_type': 'tabata', 'interval_seconds': 20}, 'metcon'

    if 'hyrox' in norm:
        return {'format_spec': text.strip()}, 'metcon'

    # "Cap 16'" / "Cap 16" / "Cap 45m"  (a normalizacao remove o apostrofo)
    cap_match = re.fullmatch(r'cap\s*(\d+)\s*m?', norm)
    if cap_match:
        return {'timecap_min': int(cap_match.group(1)), 'format_spec': text.strip(), 'score_type': 'for_time'}, 'metcon'

    # "Emom" / "Emom 12" / "Emom 12m"
    emom_match = re.fullmatch(r'emom\s*(\d+)?\s*m?', norm)
    if emom_match:
        meta = {'score_type': 'emom', 'interval_seconds': 60, 'format_spec': text.strip()}
        if emom_match.group(1):
            meta['timecap_min'] = int(emom_match.group(1))
        return meta, 'metcon'

    # "Amrap" / "Amrap 20" / "Amrap 20m"
    amrap_match = re.fullmatch(r'amrap\s*(\d+)?\s*m?', norm)
    if amrap_match:
        meta = {'score_type': 'amrap', 'format_spec': text.strip()}
        if amrap_match.group(1):
            meta['timecap_min'] = int(amrap_match.group(1))
        return meta, 'metcon'

    # "Cada 1'30" / "cada 1 30" (minutos [segundos])
    cada_match = re.fullmatch(r'cada\s+(\d+)\s*(\d+)?', norm)
    if cada_match:
        minutes = int(cada_match.group(1))
        seconds = int(cada_match.group(2)) if cada_match.group(2) else 0
        return {'interval_seconds': minutes * 60 + seconds, 'format_spec': text.strip()}, 'rounds'

    # Escada de reps: 21-15-9, 20-30-40-30-20, 1-2-3-4, 8-8-6-6-4-4, "20- 30-40-30-20"
    ladder = re.sub(r'\s*-\s*', '-', text.strip())
    if re.fullmatch(r'\d+(?:-\d+)+', ladder):
        return {'format_spec': ladder, 'score_type': 'rounds_reps'}, 'ladder'

    # Fallback para o parser de metadata canonico (Nx, "N rounds", "N rounds N%",
    # "EMOM Nm", "AMRAP Nm", "a cada Ns por Nx", "N/N/N", "Nm").
    meta = _parse_block_metadata(text)
    if meta:
        score = meta.get('score_type')
        if score in ('emom', 'amrap', 'for_time') or 'timecap_min' in meta:
            return meta, 'metcon'
        return meta, 'rounds'

    return None


# ---------------------------------------------------------------------------
# Movimentos
# ---------------------------------------------------------------------------

def _extract_inline_notes(text: str):
    """Separa notas inline (*...* e (...)) e detecta carga em %.

    Retorna (texto_limpo, notas: list[str], load_spec: str | None).
    """
    notes: list[str] = []

    def grab_star(match):
        notes.append(match.group(1).strip())
        return ' '

    def grab_paren(match):
        content = match.group(1).strip()
        if content:
            notes.append(content)
        return ' '

    load_spec = None
    percent = _PERCENT_RE.search(text)
    if percent:
        load_spec = percent.group(1).replace(',', '.') + '%'

    cleaned = _STAR_RE.sub(grab_star, text)
    cleaned = _PAREN_RE.sub(grab_paren, cleaned)
    cleaned = re.sub(r'["“”]+', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    cleaned = cleaned.strip(' -–—')
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned, notes, load_spec


def _raw_movement(label: str, *, block: dict) -> dict:
    """Movimento nao reconhecido: estrutura preservada, slug resolvido se possivel."""
    return {
        'movement_slug': resolve_movement_slug(label),
        'movement_label_raw': label,
        'sets': None,
        'reps_spec': None,
        'load_spec': None,
        'load_rx_male_kg': None,
        'load_rx_female_kg': None,
        'load_percentage_rm': block.get('_inherited_load_percentage_rm'),
        'emom_label': None,
        'notes': None,
        'is_scaled_alternative': False,
        'sort_order': len(block['movements']),
    }


def _append_movement_line(block: dict, raw_line: str) -> None:
    """Parseia uma linha de movimento e anexa ao bloco, preservando notas/carga inline."""
    cleaned, notes, load_spec = _extract_inline_notes(raw_line)
    target_text = cleaned or raw_line.strip()

    payloads = _parse_movement_line(target_text, block)
    if not payloads:
        payloads = [_raw_movement(target_text, block=block)]

    note_text = '; '.join(note for note in notes if note) or None
    for payload in payloads:
        if load_spec and not payload.get('load_spec'):
            payload['load_spec'] = load_spec
            try:
                payload['load_percentage_rm'] = float(load_spec[:-1])
            except (TypeError, ValueError):
                pass
    if note_text:
        last = payloads[-1]
        last['notes'] = f"{last['notes']}; {note_text}" if last.get('notes') else note_text

    block['movements'].extend(payloads)


# ---------------------------------------------------------------------------
# Bloco e dia
# ---------------------------------------------------------------------------

def _apply_scheme(block: dict, meta: dict) -> None:
    for key, value in meta.items():
        if key == 'inherited_load_percentage_rm':
            block['_inherited_load_percentage_rm'] = value
            continue
        if key == 'format_spec':
            existing = block.get('format_spec')
            block['format_spec'] = f'{existing} {value}'.strip() if existing else value
            continue
        if block.get(key) in (None, '', []):
            block[key] = value


def _finalize_kind(block: dict, *, warmup_kind: str | None, skill_seen: bool, scheme_hints: set[str]) -> str:
    if warmup_kind:
        return warmup_kind
    if skill_seen:
        return 'skill'
    if 'metcon' in scheme_hints:
        return 'metcon'
    if {'rounds', 'ladder'} & scheme_hints:
        return 'strength' if len(block['movements']) <= 1 else 'metcon'
    if block['movements']:
        return 'custom'
    return 'custom'


def _parse_segment(segment: list[tuple[int, str]], *, sort_order: int) -> dict:
    """Converte um segmento (linhas nao-vazias entre brancos) em um bloco."""
    block = _build_block('custom', sort_order=sort_order)
    warmup_kind = None
    skill_seen = False
    scheme_hints: set[str] = set()
    title_set = False

    for _line_number, text in segment:
        norm = _normalize_token(text)

        kind = _warmup_kind(norm)
        if kind and not _LEADING_DIGIT_RE.match(text):
            warmup_kind = kind
            if not title_set:
                block['title'] = text
                title_set = True
            continue

        if _is_skill_marker(norm):
            skill_seen = True
            remainder = text.strip()[len('skill'):].strip() if norm != 'skill' else ''
            if not title_set:
                block['title'] = 'Skill'
                title_set = True
            if remainder:
                scheme = _detect_scheme(remainder)
                if scheme:
                    _apply_scheme(block, scheme[0])
                    scheme_hints.add(scheme[1])
            continue

        if _is_note_line(text, norm):
            note = text.strip().strip('*').strip()
            if note:
                existing = block.get('notes') or ''
                if not existing.endswith(note):
                    block['notes'] = f'{existing} {note}'.strip() if existing else note
            continue

        scheme = _detect_scheme(text)
        if scheme is not None:
            _apply_scheme(block, scheme[0])
            scheme_hints.add(scheme[1])
            if not title_set and scheme[0].get('format_spec'):
                block['title'] = scheme[0]['format_spec']
                title_set = True
            continue

        _append_movement_line(block, text)

    block['kind'] = _finalize_kind(
        block, warmup_kind=warmup_kind, skill_seen=skill_seen, scheme_hints=scheme_hints
    )
    if block['kind'] == 'metcon' and block['score_type'] is None and block['movements']:
        block['score_type'] = 'for_time'

    block.pop('_inherited_load_percentage_rm', None)
    for index, movement in enumerate(block['movements']):
        movement['sort_order'] = index
    return block


def _is_scheme_header_only(block: dict) -> bool:
    """Bloco que so tem esquema (rounds/cap/emom...) e nenhum movimento ainda.

    Acontece quando o coach separa o cabecalho do esquema dos movimentos com uma linha em
    branco (ex.: 'Hyrox' / 'Cap 45m' / <branco> / '600 run' ...). NAO conta aquecimento/skill,
    que legitimamente podem nao ter movimentos.
    """
    if block['movements']:
        return False
    if block['kind'] in ('warmup', 'mobility', 'skill'):
        return False
    return any(block.get(key) for key in ('timecap_min', 'rounds', 'interval_seconds', 'score_type'))


def _merge_orphan_scheme_headers(blocks: list[dict]) -> list[dict]:
    """Funde um cabecalho de esquema sem movimentos com o bloco seguinte que os tem."""
    merged: list[dict] = []
    index = 0
    while index < len(blocks):
        block = blocks[index]
        follower = blocks[index + 1] if index + 1 < len(blocks) else None
        can_merge = (
            follower is not None
            and _is_scheme_header_only(block)
            and follower['movements']
            and follower['kind'] not in ('warmup', 'mobility', 'skill')
        )
        if can_merge:
            for key in ('timecap_min', 'rounds', 'interval_seconds', 'score_type'):
                if not block.get(key) and follower.get(key):
                    block[key] = follower[key]
            follower_spec = follower.get('format_spec')
            if follower_spec and follower_spec not in (block.get('format_spec') or ''):
                existing = block.get('format_spec') or ''
                block['format_spec'] = f'{existing} {follower_spec}'.strip()
            if follower.get('notes'):
                block['notes'] = (
                    f"{block['notes']} {follower['notes']}".strip()
                    if block.get('notes') else follower['notes']
                )
            block['movements'] = follower['movements']
            if block['kind'] == 'metcon' and block['score_type'] is None and block['movements']:
                block['score_type'] = 'for_time'
            for sort_index, movement in enumerate(block['movements']):
                movement['sort_order'] = sort_index
            merged.append(block)
            index += 2
            continue
        merged.append(block)
        index += 1
    for sort_index, block in enumerate(merged):
        block['sort_order'] = sort_index
    return merged


def _segment_day_body(body_lines: list[tuple[int, str]]) -> list[list[tuple[int, str]]]:
    """Agrupa linhas nao-vazias em segmentos separados por >=1 linha em branco."""
    segments: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    for line_number, raw in body_lines:
        if raw.strip() == '':
            if current:
                segments.append(current)
                current = []
            continue
        current.append((line_number, raw.strip()))
    if current:
        segments.append(current)
    return segments


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def _split_lines(text: str) -> list[str]:
    return (text or '').replace('\r\n', '\n').replace('\r', '\n').split('\n')


def parse_weekly_wod_freeform(text: str) -> dict:
    """Organiza texto cru de WOD semanal em dias -> blocos -> movimentos."""
    result = {'week_label': None, 'parse_warnings': [], 'days': []}
    lines = _split_lines(text)

    sections: list[dict] = []
    current_section = None
    for line_number, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        weekday_match = _match_weekday_line(stripped) if stripped else None
        if weekday_match is not None:
            weekday, label = weekday_match
            current_section = {'weekday': weekday, 'label': label, 'lines': []}
            sections.append(current_section)
            continue
        if current_section is None:
            if stripped:
                result['parse_warnings'].append(
                    {
                        'line_number': line_number,
                        'line_text': stripped,
                        'message': 'linha fora de um dia da semana',
                    }
                )
            continue
        current_section['lines'].append((line_number, raw))

    days_by_weekday: dict[int, dict] = {}
    for section in sections:
        day = days_by_weekday.get(section['weekday'])
        if day is None:
            day = _build_day(section['weekday'], section['label'])
            days_by_weekday[section['weekday']] = day
        for segment in _segment_day_body(section['lines']):
            block = _parse_segment(segment, sort_order=len(day['blocks']))
            day['blocks'].append(block)

    for day in days_by_weekday.values():
        day['blocks'] = _merge_orphan_scheme_headers(day['blocks'])

    result['days'] = [days_by_weekday[weekday] for weekday in sorted(days_by_weekday)]
    return result


def _freeform_should_take_over(parsed: dict | None) -> bool:
    """True quando o parser com cabecalho nao rendeu estrutura util."""
    if not parsed:
        return True
    days = parsed.get('days') or []
    total_blocks = sum(len(day.get('blocks', [])) for day in days)
    if total_blocks == 0:
        return True
    total_movements = sum(
        len(block.get('movements', []))
        for day in days
        for block in day.get('blocks', [])
    )
    warnings = len(parsed.get('parse_warnings') or [])
    return warnings > max(total_movements, 1)


__all__ = ['parse_weekly_wod_freeform', '_freeform_should_take_over']
